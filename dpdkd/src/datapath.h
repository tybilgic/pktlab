#ifndef PKTLAB_DPDKD_DATAPATH_H
#define PKTLAB_DPDKD_DATAPATH_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "eal.h"
#include "pktlab_dpdkd/errors.h"
#include "ports.h"

#define PKTLAB_DPDKD_DEFAULT_LCORES "1"
#define PKTLAB_DPDKD_DEFAULT_HUGEPAGE_SIZE_MB 2U
#define PKTLAB_DPDKD_DEFAULT_HUGEPAGES_MB 256U
#define PKTLAB_DPDKD_DEFAULT_BURST_SIZE 32U
#define PKTLAB_DPDKD_DEFAULT_RX_QUEUE_SIZE 256U
#define PKTLAB_DPDKD_DEFAULT_TX_QUEUE_SIZE 256U
#define PKTLAB_DPDKD_DEFAULT_MEMPOOL_SIZE 4096U
#define PKTLAB_DPDKD_DEFAULT_INGRESS_PORT_NAME "dtap0"
#define PKTLAB_DPDKD_DEFAULT_EGRESS_PORT_NAME "dtap1"

struct pktlab_datapath_config {
    const char *lcores;
    uint32_t hugepages_mb;
    uint32_t burst_size;
    uint32_t rx_queue_size;
    uint32_t tx_queue_size;
    uint32_t mempool_size;
    const char *ingress_port_name;
    const char *egress_port_name;
};

struct pktlab_datapath {
    struct pktlab_eal_config eal;
    struct pktlab_ports_config ports;
    bool configured;
    bool started;
    bool ports_ready;
    char running_message[PKTLAB_DPDKD_MESSAGE_LEN];
};

int pktlab_datapath_init(
    struct pktlab_datapath *datapath,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
);
int pktlab_datapath_start(
    struct pktlab_datapath *datapath,
    struct pktlab_dpdkd_error *error
);
void pktlab_datapath_cleanup(struct pktlab_datapath *datapath);
void pktlab_datapath_running_message(
    const struct pktlab_datapath *datapath,
    char *buffer,
    size_t buffer_cap
);
bool pktlab_datapath_ports_ready(const struct pktlab_datapath *datapath);

#endif /* PKTLAB_DPDKD_DATAPATH_H */
