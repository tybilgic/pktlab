#ifndef PKTLAB_DPDKD_HEALTH_H
#define PKTLAB_DPDKD_HEALTH_H

#include <stdbool.h>
#include <stdint.h>

#include "pktlab_dpdkd/types.h"

struct pktlab_health_tracker {
    struct pktlab_health_snapshot snapshot;
};

void pktlab_health_init(struct pktlab_health_tracker *tracker);
void pktlab_health_set_state(
    struct pktlab_health_tracker *tracker,
    enum pktlab_dp_state state,
    const char *message
);
void pktlab_health_set_ports_ready(struct pktlab_health_tracker *tracker, bool ports_ready);
void pktlab_health_set_paused(struct pktlab_health_tracker *tracker, bool paused);
void pktlab_health_set_applied_rule_version(
    struct pktlab_health_tracker *tracker,
    uint32_t applied_rule_version
);
void pktlab_health_snapshot(
    const struct pktlab_health_tracker *tracker,
    struct pktlab_health_snapshot *snapshot
);
const char *pktlab_dp_state_name(enum pktlab_dp_state state);

#endif /* PKTLAB_DPDKD_HEALTH_H */
