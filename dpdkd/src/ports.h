#ifndef PKTLAB_DPDKD_PORTS_H
#define PKTLAB_DPDKD_PORTS_H

#include <stdint.h>

#include "pktlab_dpdkd/errors.h"
#include "pktlab_dpdkd/types.h"

#define PKTLAB_DPDKD_PORT_COUNT 2U

struct pktlab_datapath_config;

struct pktlab_ports_config {
    uint16_t burst_size;
    uint16_t rx_queue_size;
    uint16_t tx_queue_size;
    uint32_t mempool_size;
    struct pktlab_port_info infos[PKTLAB_DPDKD_PORT_COUNT];
};

int pktlab_ports_prepare(
    struct pktlab_ports_config *ports,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
);
void pktlab_ports_set_state(struct pktlab_ports_config *ports, enum pktlab_port_state state);

#endif /* PKTLAB_DPDKD_PORTS_H */
