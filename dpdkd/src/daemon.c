#include "daemon.h"

#include <string.h>

#include "json_proto.h"
#include "log.h"

static void pktlab_daemon_set_error(
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

static int pktlab_daemon_dispatch_request(
    void *handler_ctx,
    const struct pktlab_ipc_request *request,
    char *response_buffer,
    size_t response_buffer_cap,
    size_t *response_len,
    struct pktlab_dpdkd_error *error
)
{
    char payload[1024];
    size_t payload_len;
    struct pktlab_daemon *daemon;
    struct pktlab_health_snapshot health_snapshot;

    daemon = handler_ctx;

    if (strcmp(request->cmd, "ping") == 0) {
        if (pktlab_json_proto_make_pong_payload(payload, sizeof(payload), &payload_len) != 0) {
            pktlab_daemon_set_error(error, PKTLAB_DPDKD_ERR_INTERNAL, "failed to render pong payload");
            return -1;
        }
    } else if (strcmp(request->cmd, "get_version") == 0) {
        if (pktlab_json_proto_make_version_payload(payload, sizeof(payload), &payload_len) != 0) {
            pktlab_daemon_set_error(
                error,
                PKTLAB_DPDKD_ERR_INTERNAL,
                "failed to render version payload"
            );
            return -1;
        }
    } else if (strcmp(request->cmd, "get_health") == 0) {
        pktlab_health_snapshot(&daemon->health, &health_snapshot);
        if (pktlab_json_proto_make_health_payload(
                &health_snapshot, payload, sizeof(payload), &payload_len) != 0) {
            pktlab_daemon_set_error(
                error,
                PKTLAB_DPDKD_ERR_INTERNAL,
                "failed to render health payload"
            );
            return -1;
        }
    } else {
        pktlab_daemon_set_error(error, PKTLAB_DPDKD_ERR_UNKNOWN_COMMAND, "unknown IPC command");
        return -1;
    }

    if (pktlab_json_proto_make_success(
            request->id,
            payload,
            response_buffer,
            response_buffer_cap,
            response_len,
            error) != 0) {
        return -1;
    }

    return 0;
}

int pktlab_daemon_init(
    struct pktlab_daemon *daemon,
    const struct pktlab_daemon_config *config,
    struct pktlab_dpdkd_error *error
)
{
    const char *socket_path;
    struct pktlab_ipc_server_config ipc_config;

    memset(daemon, 0, sizeof(*daemon));
    daemon->ipc_server.listen_fd = -1;

    socket_path = config->socket_path;
    if (socket_path == NULL) {
        socket_path = PKTLAB_DPDKD_DEFAULT_SOCKET_PATH;
    }

    if (strlen(socket_path) >= sizeof(daemon->socket_path)) {
        pktlab_daemon_set_error(error, PKTLAB_DPDKD_ERR_INVALID_REQUEST, "socket path exceeds PATH_MAX");
        return -1;
    }

    strcpy(daemon->socket_path, socket_path);

    pktlab_health_init(&daemon->health);
    pktlab_health_set_ports_ready(&daemon->health, false);
    pktlab_health_set_paused(&daemon->health, false);
    pktlab_health_set_applied_rule_version(&daemon->health, 0U);
    pktlab_stats_init(&daemon->stats);

    ipc_config.socket_path = daemon->socket_path;
    ipc_config.backlog = PKTLAB_IPC_SERVER_DEFAULT_BACKLOG;
    if (pktlab_ipc_server_init(&daemon->ipc_server, &ipc_config, error) != 0) {
        pktlab_health_set_state(
            &daemon->health,
            PKTLAB_DP_STATE_FAILED,
            "failed to initialize IPC socket"
        );
        return -1;
    }

    pktlab_health_set_state(&daemon->health, PKTLAB_DP_STATE_STARTING, "ipc socket initialized");
    return 0;
}

int pktlab_daemon_run(struct pktlab_daemon *daemon, volatile sig_atomic_t *stop_requested)
{
    int status;

    PKTLAB_LOG_INFO("starting datapath daemon on socket %s", daemon->socket_path);
    pktlab_health_set_state(
        &daemon->health,
        PKTLAB_DP_STATE_RUNNING,
        "ipc server listening; datapath fast path not initialized"
    );

    status = pktlab_ipc_server_run(
        &daemon->ipc_server,
        pktlab_daemon_dispatch_request,
        daemon,
        stop_requested
    );
    if (status != 0) {
        pktlab_health_set_state(&daemon->health, PKTLAB_DP_STATE_FAILED, "ipc server exited with an error");
        return -1;
    }

    pktlab_health_set_state(&daemon->health, PKTLAB_DP_STATE_STOPPING, "shutting down datapath daemon");
    return 0;
}

void pktlab_daemon_cleanup(struct pktlab_daemon *daemon)
{
    pktlab_ipc_server_close(&daemon->ipc_server);
}
