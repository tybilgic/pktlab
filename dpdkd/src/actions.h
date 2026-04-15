#ifndef PKTLAB_DPDKD_ACTIONS_H
#define PKTLAB_DPDKD_ACTIONS_H

#include <stdint.h>

struct rte_mbuf;

uint16_t pktlab_actions_forward_burst(
    uint16_t port_id,
    struct rte_mbuf **packets,
    uint16_t packet_count
);
void pktlab_actions_drop_burst(struct rte_mbuf **packets, uint16_t packet_count);

#endif /* PKTLAB_DPDKD_ACTIONS_H */
