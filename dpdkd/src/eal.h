#ifndef PKTLAB_DPDKD_EAL_H
#define PKTLAB_DPDKD_EAL_H

#include <stdbool.h>
#include <stdint.h>

#include "pktlab_dpdkd/errors.h"

#define PKTLAB_DPDKD_EAL_LCORES_LEN 64
#define PKTLAB_DPDKD_EAL_VDEV_NAME_LEN 32
#define PKTLAB_DPDKD_EAL_VDEV_ARG_LEN 128

struct pktlab_datapath_config;

struct pktlab_eal_config {
    char lcores[PKTLAB_DPDKD_EAL_LCORES_LEN];
    uint32_t hugepages_mb;
    char ingress_vdev_name[PKTLAB_DPDKD_EAL_VDEV_NAME_LEN];
    char ingress_vdev_arg[PKTLAB_DPDKD_EAL_VDEV_ARG_LEN];
    char egress_vdev_name[PKTLAB_DPDKD_EAL_VDEV_NAME_LEN];
    char egress_vdev_arg[PKTLAB_DPDKD_EAL_VDEV_ARG_LEN];
    bool initialized;
};

int pktlab_eal_prepare(
    struct pktlab_eal_config *eal,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
);
int pktlab_eal_start(
    struct pktlab_eal_config *eal,
    struct pktlab_dpdkd_error *error
);
void pktlab_eal_cleanup(struct pktlab_eal_config *eal);

#endif /* PKTLAB_DPDKD_EAL_H */
