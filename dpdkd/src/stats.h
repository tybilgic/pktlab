#ifndef PKTLAB_DPDKD_STATS_H
#define PKTLAB_DPDKD_STATS_H

#include <pthread.h>
#include <stdbool.h>

#include "pktlab_dpdkd/types.h"

struct pktlab_stats_tracker {
    struct dp_stats_snapshot snapshot;
    pthread_mutex_t lock;
    bool initialized;
};

int pktlab_stats_init(struct pktlab_stats_tracker *tracker);
void pktlab_stats_destroy(struct pktlab_stats_tracker *tracker);
void pktlab_stats_reset(struct pktlab_stats_tracker *tracker);
void pktlab_stats_add(
    struct pktlab_stats_tracker *tracker,
    const struct dp_stats_snapshot *delta
);
void pktlab_stats_snapshot(
    const struct pktlab_stats_tracker *tracker,
    struct dp_stats_snapshot *snapshot
);

#endif /* PKTLAB_DPDKD_STATS_H */
