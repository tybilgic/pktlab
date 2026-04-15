#include "eal.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "datapath.h"

#if PKTLAB_DPDKD_HAS_DPDK
#include <rte_eal.h>
#endif

#define PKTLAB_DPDKD_EAL_ARGC 12
#define PKTLAB_DPDKD_EAL_SOCKET_MEM_LEN 32
#define PKTLAB_DPDKD_EAL_FILE_PREFIX_LEN 64

static void pktlab_eal_set_error(
    struct pktlab_dpdkd_error *error,
    enum pktlab_dpdkd_error_code code,
    const char *message
)
{
    if (error == NULL) {
        return;
    }

    error->code = code;
    error->message = message;
}

int pktlab_eal_prepare(
    struct pktlab_eal_config *eal,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
)
{
    int written;

    memset(eal, 0, sizeof(*eal));

    if (config->lcores == NULL || config->lcores[0] == '\0') {
        pktlab_eal_set_error(error, PKTLAB_DPDKD_ERR_INVALID_REQUEST, "lcores must be a non-empty string");
        return -1;
    }

    written = snprintf(eal->lcores, sizeof(eal->lcores), "%s", config->lcores);
    if (written < 0 || (size_t) written >= sizeof(eal->lcores)) {
        pktlab_eal_set_error(error, PKTLAB_DPDKD_ERR_INVALID_REQUEST, "lcores exceeds the supported length");
        return -1;
    }

    if (
        config->hugepages_mb == 0U
        || (config->hugepages_mb % PKTLAB_DPDKD_DEFAULT_HUGEPAGE_SIZE_MB) != 0U
    ) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "hugepages_mb must be a positive multiple of 2 MB"
        );
        return -1;
    }
    eal->hugepages_mb = config->hugepages_mb;

    written = snprintf(
        eal->ingress_vdev_name,
        sizeof(eal->ingress_vdev_name),
        "%s",
        "net_tap0"
    );
    if (written < 0 || (size_t) written >= sizeof(eal->ingress_vdev_name)) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "ingress TAP vdev name exceeds the supported length"
        );
        return -1;
    }

    written = snprintf(
        eal->ingress_vdev_arg,
        sizeof(eal->ingress_vdev_arg),
        "--vdev=%s,iface=%s",
        eal->ingress_vdev_name,
        config->ingress_port_name
    );
    if (written < 0 || (size_t) written >= sizeof(eal->ingress_vdev_arg)) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "ingress TAP vdev configuration exceeds the supported length"
        );
        return -1;
    }

    written = snprintf(
        eal->egress_vdev_name,
        sizeof(eal->egress_vdev_name),
        "%s",
        "net_tap1"
    );
    if (written < 0 || (size_t) written >= sizeof(eal->egress_vdev_name)) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "egress TAP vdev name exceeds the supported length"
        );
        return -1;
    }

    written = snprintf(
        eal->egress_vdev_arg,
        sizeof(eal->egress_vdev_arg),
        "--vdev=%s,iface=%s",
        eal->egress_vdev_name,
        config->egress_port_name
    );
    if (written < 0 || (size_t) written >= sizeof(eal->egress_vdev_arg)) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "egress TAP vdev configuration exceeds the supported length"
        );
        return -1;
    }

    return 0;
}

int pktlab_eal_start(
    struct pktlab_eal_config *eal,
    struct pktlab_dpdkd_error *error
)
{
#if PKTLAB_DPDKD_HAS_DPDK
    char program_name[] = "pktlab-dpdkd";
    char lcores_flag[] = "-l";
    char no_pci_flag[] = "--no-pci";
    char in_memory_flag[] = "--in-memory";
    char iova_mode_flag[] = "--iova-mode=va";
    char huge_unlink_flag[] = "--huge-unlink=always";
    char no_telemetry_flag[] = "--no-telemetry";
    char socket_mem_arg[PKTLAB_DPDKD_EAL_SOCKET_MEM_LEN];
    char file_prefix_arg[PKTLAB_DPDKD_EAL_FILE_PREFIX_LEN];
    char *argv[PKTLAB_DPDKD_EAL_ARGC];
    int argc;
    int written;

    if (eal->initialized) {
        return 0;
    }

    written = snprintf(
        socket_mem_arg,
        sizeof(socket_mem_arg),
        "--socket-mem=%u",
        eal->hugepages_mb
    );
    if (written < 0 || (size_t) written >= sizeof(socket_mem_arg)) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "failed to render DPDK socket memory argument"
        );
        return -1;
    }

    written = snprintf(
        file_prefix_arg,
        sizeof(file_prefix_arg),
        "--file-prefix=pktlab-%ld",
        (long) getpid()
    );
    if (written < 0 || (size_t) written >= sizeof(file_prefix_arg)) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "failed to render DPDK file prefix argument"
        );
        return -1;
    }

    argc = 0;
    argv[argc++] = program_name;
    argv[argc++] = lcores_flag;
    argv[argc++] = eal->lcores;
    argv[argc++] = no_pci_flag;
    argv[argc++] = in_memory_flag;
    argv[argc++] = iova_mode_flag;
    argv[argc++] = huge_unlink_flag;
    argv[argc++] = no_telemetry_flag;
    argv[argc++] = socket_mem_arg;
    argv[argc++] = file_prefix_arg;
    argv[argc++] = eal->ingress_vdev_arg;
    argv[argc++] = eal->egress_vdev_arg;

    if (rte_eal_init(argc, argv) < 0) {
        pktlab_eal_set_error(error, PKTLAB_DPDKD_ERR_PORT_INIT, "failed to initialize DPDK EAL");
        return -1;
    }

    eal->initialized = true;
    return 0;
#else
    (void) eal;
    pktlab_eal_set_error(
        error,
        PKTLAB_DPDKD_ERR_STATE_CONFLICT,
        "libdpdk was not available at build time"
    );
    return -1;
#endif
}

void pktlab_eal_cleanup(struct pktlab_eal_config *eal)
{
#if PKTLAB_DPDKD_HAS_DPDK
    if (!eal->initialized) {
        return;
    }

    (void) rte_eal_cleanup();
#endif

    eal->initialized = false;
}
