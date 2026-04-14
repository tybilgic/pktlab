#include "datapath.h"

#include <stdio.h>
#include <string.h>

static void pktlab_datapath_set_error(
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

int pktlab_datapath_init(
    struct pktlab_datapath *datapath,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
)
{
    memset(datapath, 0, sizeof(*datapath));

    if (pktlab_eal_prepare(&datapath->eal, config, error) != 0) {
        return -1;
    }
    if (pktlab_ports_prepare(&datapath->ports, config, error) != 0) {
        return -1;
    }

    datapath->configured = true;
    return 0;
}

int pktlab_datapath_start(
    struct pktlab_datapath *datapath,
    struct pktlab_dpdkd_error *error
)
{
    if (!datapath->configured) {
        pktlab_datapath_set_error(
            error,
            PKTLAB_DPDKD_ERR_STATE_CONFLICT,
            "datapath runtime configuration is not initialized"
        );
        return -1;
    }

    pktlab_ports_set_state(&datapath->ports, PKTLAB_PORT_STATE_DOWN);
    return 0;
}

void pktlab_datapath_cleanup(struct pktlab_datapath *datapath)
{
    if (!datapath->configured) {
        return;
    }

    pktlab_ports_set_state(&datapath->ports, PKTLAB_PORT_STATE_DOWN);
    datapath->configured = false;
}

void pktlab_datapath_running_message(
    const struct pktlab_datapath *datapath,
    char *buffer,
    size_t buffer_cap
)
{
    if (buffer_cap == 0U) {
        return;
    }

#if PKTLAB_DPDKD_HAS_DPDK
    (void) snprintf(
        buffer,
        buffer_cap,
        "configured TAP ports %s/%s; DPDK startup is the next PLN-008 slice",
        datapath->ports.infos[0].name,
        datapath->ports.infos[1].name
    );
#else
    (void) snprintf(
        buffer,
        buffer_cap,
        "configured TAP ports %s/%s; libdpdk was not available at build time",
        datapath->ports.infos[0].name,
        datapath->ports.infos[1].name
    );
#endif

    buffer[buffer_cap - 1U] = '\0';
}
