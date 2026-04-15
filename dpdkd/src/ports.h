#ifndef PKTLAB_DPDKD_PORTS_H
#define PKTLAB_DPDKD_PORTS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "pktlab_dpdkd/errors.h"
#include "pktlab_dpdkd/types.h"

#define PKTLAB_DPDKD_PORT_COUNT 2U

struct pktlab_datapath_config;
struct pktlab_eal_config;
struct rte_mempool;

struct pktlab_ports_config {
    uint16_t burst_size;
    uint16_t rx_queue_size;
    uint16_t tx_queue_size;
    uint32_t mempool_size;
    struct pktlab_port_info infos[PKTLAB_DPDKD_PORT_COUNT];
    bool attached[PKTLAB_DPDKD_PORT_COUNT];
    bool ready;
    struct rte_mempool *mempool;
};

int pktlab_ports_prepare(
    struct pktlab_ports_config *ports,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
);
int pktlab_ports_start(
    struct pktlab_ports_config *ports,
    const struct pktlab_eal_config *eal,
    struct pktlab_dpdkd_error *error
);
void pktlab_ports_cleanup(struct pktlab_ports_config *ports);
void pktlab_ports_snapshot(
    const struct pktlab_ports_config *ports,
    struct pktlab_port_info *infos,
    size_t infos_cap,
    size_t *info_count
);
bool pktlab_ports_ready(const struct pktlab_ports_config *ports);
void pktlab_ports_set_state(struct pktlab_ports_config *ports, enum pktlab_port_state state);

#endif /* PKTLAB_DPDKD_PORTS_H */
