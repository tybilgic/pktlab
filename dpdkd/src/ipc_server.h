#ifndef PKTLAB_DPDKD_IPC_SERVER_H
#define PKTLAB_DPDKD_IPC_SERVER_H

#include <limits.h>
#include <signal.h>
#include <stddef.h>

#include "json_proto.h"
#include "pktlab_dpdkd/errors.h"

#define PKTLAB_IPC_SERVER_DEFAULT_BACKLOG 16

struct pktlab_ipc_server_config {
    const char *socket_path;
    int backlog;
};

struct pktlab_ipc_server {
    int listen_fd;
    char socket_path[PATH_MAX];
    int backlog;
};

typedef int (*pktlab_ipc_request_handler_fn)(
    void *handler_ctx,
    const struct pktlab_ipc_request *request,
    char *response_buffer,
    size_t response_buffer_cap,
    size_t *response_len,
    struct pktlab_dpdkd_error *error
);

int pktlab_ipc_server_init(
    struct pktlab_ipc_server *server,
    const struct pktlab_ipc_server_config *config,
    struct pktlab_dpdkd_error *error
);
int pktlab_ipc_server_run(
    struct pktlab_ipc_server *server,
    pktlab_ipc_request_handler_fn handler,
    void *handler_ctx,
    volatile sig_atomic_t *stop_requested
);
void pktlab_ipc_server_close(struct pktlab_ipc_server *server);

#endif /* PKTLAB_DPDKD_IPC_SERVER_H */
