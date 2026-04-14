#ifndef PKTLAB_DPDKD_DAEMON_H
#define PKTLAB_DPDKD_DAEMON_H

#include <limits.h>
#include <signal.h>
#include <stddef.h>

#include "datapath.h"
#include "health.h"
#include "ipc_server.h"
#include "log.h"
#include "stats.h"

#define PKTLAB_DPDKD_DEFAULT_SOCKET_PATH "/run/pktlab/dpdkd.sock"

struct pktlab_daemon_config {
    const char *socket_path;
    enum pktlab_log_level log_level;
    struct pktlab_datapath_config datapath;
};

struct pktlab_daemon {
    char socket_path[PATH_MAX];
    struct pktlab_health_tracker health;
    struct pktlab_stats_tracker stats;
    struct pktlab_datapath datapath;
    struct pktlab_ipc_server ipc_server;
};

int pktlab_daemon_init(
    struct pktlab_daemon *daemon,
    const struct pktlab_daemon_config *config,
    struct pktlab_dpdkd_error *error
);
int pktlab_daemon_run(struct pktlab_daemon *daemon, volatile sig_atomic_t *stop_requested);
void pktlab_daemon_cleanup(struct pktlab_daemon *daemon);

#endif /* PKTLAB_DPDKD_DAEMON_H */
