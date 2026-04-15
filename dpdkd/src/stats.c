#include "stats.h"

#include <pthread.h>
#include <string.h>

int pktlab_stats_init(struct pktlab_stats_tracker *tracker)
{
    memset(tracker, 0, sizeof(*tracker));
    if (pthread_mutex_init(&tracker->lock, NULL) != 0) {
        return -1;
    }
    tracker->initialized = true;
    return 0;
}

void pktlab_stats_destroy(struct pktlab_stats_tracker *tracker)
{
    if (!tracker->initialized) {
        return;
    }

    (void) pthread_mutex_destroy(&tracker->lock);
    tracker->initialized = false;
}

void pktlab_stats_reset(struct pktlab_stats_tracker *tracker)
{
    if (!tracker->initialized) {
        return;
    }

    (void) pthread_mutex_lock(&tracker->lock);
    memset(&tracker->snapshot, 0, sizeof(tracker->snapshot));
    (void) pthread_mutex_unlock(&tracker->lock);
}

void pktlab_stats_add(
    struct pktlab_stats_tracker *tracker,
    const struct dp_stats_snapshot *delta
)
{
    if (!tracker->initialized) {
        return;
    }

    (void) pthread_mutex_lock(&tracker->lock);
    tracker->snapshot.rx_packets += delta->rx_packets;
    tracker->snapshot.tx_packets += delta->tx_packets;
    tracker->snapshot.drop_packets += delta->drop_packets;
    tracker->snapshot.drop_parse_errors += delta->drop_parse_errors;
    tracker->snapshot.drop_no_match += delta->drop_no_match;
    tracker->snapshot.rx_bursts += delta->rx_bursts;
    tracker->snapshot.tx_bursts += delta->tx_bursts;
    tracker->snapshot.unsent_packets += delta->unsent_packets;
    (void) pthread_mutex_unlock(&tracker->lock);
}

void pktlab_stats_snapshot(
    const struct pktlab_stats_tracker *tracker,
    struct dp_stats_snapshot *snapshot
)
{
    if (!tracker->initialized) {
        memset(snapshot, 0, sizeof(*snapshot));
        return;
    }

    (void) pthread_mutex_lock((pthread_mutex_t *) &tracker->lock);
    *snapshot = tracker->snapshot;
    (void) pthread_mutex_unlock((pthread_mutex_t *) &tracker->lock);
}
