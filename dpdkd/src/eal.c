#include "eal.h"

#include <stdio.h>
#include <string.h>

#include "datapath.h"

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
        eal->ingress_vdev_arg,
        sizeof(eal->ingress_vdev_arg),
        "net_tap0,iface=%s",
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
        eal->egress_vdev_arg,
        sizeof(eal->egress_vdev_arg),
        "net_tap1,iface=%s",
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
