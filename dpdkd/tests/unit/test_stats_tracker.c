#include <stdint.h>

#include "stats.h"

int main(void)
{
    struct pktlab_stats_tracker tracker;
    struct dp_stats_snapshot delta = {
        .rx_packets = 5U,
        .tx_packets = 4U,
        .drop_packets = 1U,
        .drop_parse_errors = 1U,
        .drop_no_match = 0U,
        .rx_bursts = 2U,
        .tx_bursts = 1U,
        .unsent_packets = 1U,
    };
    struct dp_stats_snapshot snapshot;
    int status;

    status = pktlab_stats_init(&tracker);
    if (status != 0) {
        return 1;
    }

    pktlab_stats_add(&tracker, &delta);
    pktlab_stats_snapshot(&tracker, &snapshot);
    if (snapshot.rx_packets != 5U || snapshot.tx_packets != 4U || snapshot.drop_packets != 1U) {
        pktlab_stats_destroy(&tracker);
        return 1;
    }

    pktlab_stats_reset(&tracker);
    pktlab_stats_snapshot(&tracker, &snapshot);
    pktlab_stats_destroy(&tracker);

    if (snapshot.rx_packets != 0U
        || snapshot.tx_packets != 0U
        || snapshot.drop_packets != 0U
        || snapshot.drop_parse_errors != 0U
        || snapshot.drop_no_match != 0U
        || snapshot.rx_bursts != 0U
        || snapshot.tx_bursts != 0U
        || snapshot.unsent_packets != 0U) {
        return 1;
    }

    return 0;
}
