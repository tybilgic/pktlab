#include "actions.h"

#if PKTLAB_DPDKD_HAS_DPDK
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#endif

void pktlab_actions_drop_burst(struct rte_mbuf **packets, uint16_t packet_count)
{
#if PKTLAB_DPDKD_HAS_DPDK
    uint16_t index;

    for (index = 0U; index < packet_count; index++) {
        rte_pktmbuf_free(packets[index]);
    }
#else
    (void) packets;
    (void) packet_count;
#endif
}

uint16_t pktlab_actions_forward_burst(
    uint16_t port_id,
    struct rte_mbuf **packets,
    uint16_t packet_count
)
{
#if PKTLAB_DPDKD_HAS_DPDK
    uint16_t sent_count;

    if (packet_count == 0U) {
        return 0U;
    }

    sent_count = rte_eth_tx_burst(port_id, 0U, packets, packet_count);
    if (sent_count < packet_count) {
        pktlab_actions_drop_burst(&packets[sent_count], (uint16_t) (packet_count - sent_count));
    }
    return sent_count;
#else
    (void) port_id;
    pktlab_actions_drop_burst(packets, packet_count);
    return 0U;
#endif
}
