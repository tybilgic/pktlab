#include "eal.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "datapath.h"

#if PKTLAB_DPDKD_HAS_DPDK
#include <rte_eal.h>
#endif

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

int pktlab_eal_build_argv(
    const struct pktlab_eal_config *eal,
    struct pktlab_eal_argv *eal_argv,
    struct pktlab_dpdkd_error *error
)
{
    int argc;
    int written;

    memset(eal_argv, 0, sizeof(*eal_argv));

    written = snprintf(
        eal_argv->socket_mem_arg,
        sizeof(eal_argv->socket_mem_arg),
        "--socket-mem=%u",
        eal->hugepages_mb
    );
    if (written < 0 || (size_t) written >= sizeof(eal_argv->socket_mem_arg)) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "failed to render DPDK socket memory argument"
        );
        return -1;
    }

    written = snprintf(
        eal_argv->file_prefix_arg,
        sizeof(eal_argv->file_prefix_arg),
        "--file-prefix=pktlab-%ld",
        (long) getpid()
    );
    if (written < 0 || (size_t) written >= sizeof(eal_argv->file_prefix_arg)) {
        pktlab_eal_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "failed to render DPDK file prefix argument"
        );
        return -1;
    }

    argc = 0;
    eal_argv->argv[argc++] = "pktlab-dpdkd";
    eal_argv->argv[argc++] = "-l";
    eal_argv->argv[argc++] = (char *) eal->lcores;
    eal_argv->argv[argc++] = "--no-pci";
    eal_argv->argv[argc++] = "--in-memory";
    eal_argv->argv[argc++] = "--iova-mode=va";
    eal_argv->argv[argc++] = "--no-telemetry";
    eal_argv->argv[argc++] = eal_argv->socket_mem_arg;
    eal_argv->argv[argc++] = eal_argv->file_prefix_arg;
    eal_argv->argv[argc++] = (char *) eal->ingress_vdev_arg;
    eal_argv->argv[argc++] = (char *) eal->egress_vdev_arg;
    eal_argv->argc = argc;

    return 0;
}

int pktlab_eal_start(
    struct pktlab_eal_config *eal,
    struct pktlab_dpdkd_error *error
)
{
#if PKTLAB_DPDKD_HAS_DPDK
    struct pktlab_eal_argv eal_argv;

    if (eal->initialized) {
        return 0;
    }

    if (pktlab_eal_build_argv(eal, &eal_argv, error) != 0) {
        return -1;
    }

    if (rte_eal_init(eal_argv.argc, eal_argv.argv) < 0) {
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
