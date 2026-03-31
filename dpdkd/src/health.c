#include "health.h"

#include <string.h>

static void pktlab_health_copy_message(char *dst, size_t dst_len, const char *message)
{
    if (dst_len == 0U) {
        return;
    }

    if (message == NULL) {
        dst[0] = '\0';
        return;
    }

    strncpy(dst, message, dst_len - 1U);
    dst[dst_len - 1U] = '\0';
}

void pktlab_health_init(struct pktlab_health_tracker *tracker)
{
    memset(tracker, 0, sizeof(*tracker));
    tracker->snapshot.state = PKTLAB_DP_STATE_STARTING;
    pktlab_health_copy_message(
        tracker->snapshot.message,
        sizeof(tracker->snapshot.message),
        "initializing datapath daemon"
    );
}

void pktlab_health_set_state(
    struct pktlab_health_tracker *tracker,
    enum pktlab_dp_state state,
    const char *message
)
{
    tracker->snapshot.state = state;
    pktlab_health_copy_message(
        tracker->snapshot.message,
        sizeof(tracker->snapshot.message),
        message
    );
}

void pktlab_health_set_ports_ready(struct pktlab_health_tracker *tracker, bool ports_ready)
{
    tracker->snapshot.ports_ready = ports_ready;
}

void pktlab_health_set_paused(struct pktlab_health_tracker *tracker, bool paused)
{
    tracker->snapshot.paused = paused;
}

void pktlab_health_set_applied_rule_version(
    struct pktlab_health_tracker *tracker,
    uint32_t applied_rule_version
)
{
    tracker->snapshot.applied_rule_version = applied_rule_version;
}

void pktlab_health_snapshot(
    const struct pktlab_health_tracker *tracker,
    struct pktlab_health_snapshot *snapshot
)
{
    *snapshot = tracker->snapshot;
}

const char *pktlab_dp_state_name(enum pktlab_dp_state state)
{
    switch (state) {
    case PKTLAB_DP_STATE_STARTING:
        return "starting";
    case PKTLAB_DP_STATE_RUNNING:
        return "running";
    case PKTLAB_DP_STATE_PAUSED:
        return "paused";
    case PKTLAB_DP_STATE_DEGRADED:
        return "degraded";
    case PKTLAB_DP_STATE_STOPPING:
        return "stopping";
    case PKTLAB_DP_STATE_FAILED:
        return "failed";
    default:
        return "failed";
    }
}
