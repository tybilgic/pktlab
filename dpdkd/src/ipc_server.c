#include "ipc_server.h"

#include <errno.h>
#include <poll.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <unistd.h>

#include "log.h"

#define PKTLAB_IPC_SERVER_POLL_TIMEOUT_MS 250

static void pktlab_ipc_server_set_error(
    struct pktlab_dpdkd_error *error,
    enum pktlab_dpdkd_error_code code,
    const char *message
)
{
    if (error == NULL) {
        return;
    }

    error->code = code;
    error->message = message;
}

static int pktlab_ipc_server_ensure_parent_dir(
    const char *socket_path,
    struct pktlab_dpdkd_error *error
)
{
    char parent_dir[PATH_MAX];
    char *slash;

    if (strlen(socket_path) >= sizeof(parent_dir)) {
        pktlab_ipc_server_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "socket path exceeds PATH_MAX"
        );
        return -1;
    }

    strcpy(parent_dir, socket_path);
    slash = strrchr(parent_dir, '/');
    if (slash == NULL) {
        return 0;
    }

    if (slash == parent_dir) {
        return 0;
    }

    *slash = '\0';
    if (mkdir(parent_dir, 0755) == 0 || errno == EEXIST) {
        return 0;
    }

    pktlab_ipc_server_set_error(
        error,
        PKTLAB_DPDKD_ERR_INTERNAL,
        "failed to create socket directory"
    );
    return -1;
}

int pktlab_ipc_server_init(
    struct pktlab_ipc_server *server,
    const struct pktlab_ipc_server_config *config,
    struct pktlab_dpdkd_error *error
)
{
    struct sockaddr_un address;
    size_t socket_path_len;
    int listen_fd;

    memset(server, 0, sizeof(*server));
    server->listen_fd = -1;
    server->backlog = (config->backlog > 0) ? config->backlog : PKTLAB_IPC_SERVER_DEFAULT_BACKLOG;

    socket_path_len = strlen(config->socket_path);
    if (socket_path_len >= sizeof(server->socket_path) || socket_path_len >= sizeof(address.sun_path)) {
        pktlab_ipc_server_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "socket path is too long for AF_UNIX"
        );
        return -1;
    }

    if (pktlab_ipc_server_ensure_parent_dir(config->socket_path, error) != 0) {
        return -1;
    }

    listen_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (listen_fd < 0) {
        pktlab_ipc_server_set_error(error, PKTLAB_DPDKD_ERR_INTERNAL, "failed to create IPC socket");
        return -1;
    }

    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, config->socket_path, socket_path_len + 1U);

    unlink(config->socket_path);
    if (bind(listen_fd, (const struct sockaddr *) &address, sizeof(address)) != 0) {
        pktlab_ipc_server_set_error(error, PKTLAB_DPDKD_ERR_INTERNAL, "failed to bind IPC socket");
        close(listen_fd);
        return -1;
    }

    if (listen(listen_fd, server->backlog) != 0) {
        pktlab_ipc_server_set_error(error, PKTLAB_DPDKD_ERR_INTERNAL, "failed to listen on IPC socket");
        close(listen_fd);
        unlink(config->socket_path);
        return -1;
    }

    strcpy(server->socket_path, config->socket_path);
    server->listen_fd = listen_fd;
    return 0;
}

static int pktlab_ipc_server_send_error(
    int client_fd,
    const char *request_id,
    const struct pktlab_dpdkd_error *error
)
{
    char response[PKTLAB_JSON_PROTO_MAX_FRAME_SIZE];
    size_t response_len;
    struct pktlab_dpdkd_error transport_error;

    if (pktlab_json_proto_make_error(request_id, error, response, sizeof(response), &response_len) != 0) {
        return -1;
    }

    if (pktlab_json_proto_write_frame(client_fd, response, response_len, &transport_error) != 0) {
        return -1;
    }

    return 0;
}

static int pktlab_ipc_server_handle_client(
    int client_fd,
    pktlab_ipc_request_handler_fn handler,
    void *handler_ctx
)
{
    char frame[PKTLAB_JSON_PROTO_MAX_FRAME_SIZE];
    char response[PKTLAB_JSON_PROTO_MAX_FRAME_SIZE];
    struct pktlab_ipc_request request;
    size_t frame_len;
    size_t response_len;
    int read_status;

    for (;;) {
        struct pktlab_dpdkd_error error;

        memset(&error, 0, sizeof(error));
        read_status = pktlab_json_proto_read_frame(
            client_fd,
            frame,
            sizeof(frame),
            &frame_len,
            &error
        );
        if (read_status == PKTLAB_JSON_PROTO_STATUS_EOF) {
            return 0;
        }
        if (read_status != PKTLAB_JSON_PROTO_STATUS_OK) {
            PKTLAB_LOG_WARN("closing client connection after frame read error: %s", error.message);
            return -1;
        }

        memset(&request, 0, sizeof(request));
        if (pktlab_json_proto_parse_request(frame, frame_len, &request, &error) != 0) {
            PKTLAB_LOG_WARN("invalid IPC request: %s", error.message);
            if (pktlab_ipc_server_send_error(client_fd, request.id, &error) != 0) {
                return -1;
            }
            continue;
        }

        if (handler(handler_ctx, &request, response, sizeof(response), &response_len, &error) != 0) {
            PKTLAB_LOG_WARN("request handler returned error for cmd=%s: %s", request.cmd, error.message);
            if (pktlab_ipc_server_send_error(client_fd, request.id, &error) != 0) {
                return -1;
            }
            continue;
        }

        if (pktlab_json_proto_write_frame(client_fd, response, response_len, &error) != 0) {
            PKTLAB_LOG_WARN("failed to write IPC response: %s", error.message);
            return -1;
        }
    }
}

int pktlab_ipc_server_run(
    struct pktlab_ipc_server *server,
    pktlab_ipc_request_handler_fn handler,
    void *handler_ctx,
    volatile sig_atomic_t *stop_requested
)
{
    struct pollfd pfd;

    pfd.fd = server->listen_fd;
    pfd.events = POLLIN;
    pfd.revents = 0;

    while (stop_requested == NULL || *stop_requested == 0) {
        int poll_result;

        poll_result = poll(&pfd, 1, PKTLAB_IPC_SERVER_POLL_TIMEOUT_MS);
        if (poll_result < 0) {
            if (errno == EINTR) {
                continue;
            }
            PKTLAB_LOG_ERROR("poll() failed while waiting for IPC clients: %s", strerror(errno));
            return -1;
        }
        if (poll_result == 0) {
            continue;
        }
        if ((pfd.revents & POLLIN) == 0) {
            continue;
        }

        for (;;) {
            int client_fd;

            client_fd = accept(server->listen_fd, NULL, NULL);
            if (client_fd < 0) {
                if (errno == EINTR) {
                    continue;
                }
                PKTLAB_LOG_WARN("accept() failed on IPC socket: %s", strerror(errno));
                break;
            }

            PKTLAB_LOG_DEBUG("accepted IPC client connection");
            (void) pktlab_ipc_server_handle_client(client_fd, handler, handler_ctx);
            close(client_fd);
            break;
        }
    }

    return 0;
}

void pktlab_ipc_server_close(struct pktlab_ipc_server *server)
{
    if (server->listen_fd >= 0) {
        close(server->listen_fd);
        server->listen_fd = -1;
    }

    if (server->socket_path[0] != '\0') {
        unlink(server->socket_path);
    }
}
