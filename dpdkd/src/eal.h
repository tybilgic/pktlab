#ifndef PKTLAB_DPDKD_EAL_H
#define PKTLAB_DPDKD_EAL_H

#include <stdbool.h>
#include <stdint.h>

#include "pktlab_dpdkd/errors.h"

#define PKTLAB_DPDKD_EAL_LCORES_LEN 64
#define PKTLAB_DPDKD_EAL_VDEV_NAME_LEN 32
#define PKTLAB_DPDKD_EAL_VDEV_ARG_LEN 128
#define PKTLAB_DPDKD_EAL_ARGC 11
#define PKTLAB_DPDKD_EAL_SOCKET_MEM_LEN 32
#define PKTLAB_DPDKD_EAL_FILE_PREFIX_LEN 64

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

struct pktlab_eal_argv {
    int argc;
    char socket_mem_arg[PKTLAB_DPDKD_EAL_SOCKET_MEM_LEN];
    char file_prefix_arg[PKTLAB_DPDKD_EAL_FILE_PREFIX_LEN];
    char *argv[PKTLAB_DPDKD_EAL_ARGC];
};

int pktlab_eal_prepare(
    struct pktlab_eal_config *eal,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
);
int pktlab_eal_build_argv(
    const struct pktlab_eal_config *eal,
    struct pktlab_eal_argv *argv,
    struct pktlab_dpdkd_error *error
);
int pktlab_eal_start(
    struct pktlab_eal_config *eal,
    struct pktlab_dpdkd_error *error
);
void pktlab_eal_cleanup(struct pktlab_eal_config *eal);

#endif /* PKTLAB_DPDKD_EAL_H */
