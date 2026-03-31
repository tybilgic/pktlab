#include "stats.h"

#include <string.h>

void pktlab_stats_init(struct pktlab_stats_tracker *tracker)
{
    memset(tracker, 0, sizeof(*tracker));
}

void pktlab_stats_reset(struct pktlab_stats_tracker *tracker)
{
    memset(&tracker->snapshot, 0, sizeof(tracker->snapshot));
}

void pktlab_stats_snapshot(
    const struct pktlab_stats_tracker *tracker,
    struct dp_stats_snapshot *snapshot
)
{
    *snapshot = tracker->snapshot;
}
