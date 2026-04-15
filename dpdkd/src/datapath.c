#include "datapath.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

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

    datapath->ports_ready = false;

#if !PKTLAB_DPDKD_HAS_DPDK
    (void) snprintf(
        datapath->running_message,
        sizeof(datapath->running_message),
        "TAP ports %s/%s configured; libdpdk not available at build time",
        datapath->ports.infos[0].name,
        datapath->ports.infos[1].name
    );
    datapath->running_message[sizeof(datapath->running_message) - 1U] = '\0';
    datapath->started = true;
    return 0;
#endif

    if (geteuid() != 0) {
        (void) snprintf(
            datapath->running_message,
            sizeof(datapath->running_message),
            "TAP ports %s/%s need root/CAP_NET_ADMIN",
            datapath->ports.infos[0].name,
            datapath->ports.infos[1].name
        );
        datapath->running_message[sizeof(datapath->running_message) - 1U] = '\0';
        datapath->started = true;
        return 0;
    }

    if (pktlab_eal_start(&datapath->eal, error) != 0) {
        return -1;
    }
    if (pktlab_ports_start(&datapath->ports, &datapath->eal, error) != 0) {
        pktlab_ports_cleanup(&datapath->ports);
        pktlab_eal_cleanup(&datapath->eal);
        return -1;
    }

    datapath->ports_ready = pktlab_ports_ready(&datapath->ports);
    (void) snprintf(
        datapath->running_message,
        sizeof(datapath->running_message),
        "DPDK TAP ports %s/%s ready",
        datapath->ports.infos[0].name,
        datapath->ports.infos[1].name
    );
    datapath->running_message[sizeof(datapath->running_message) - 1U] = '\0';
    datapath->started = true;
    return 0;
}

void pktlab_datapath_cleanup(struct pktlab_datapath *datapath)
{
    if (!datapath->configured) {
        return;
    }

    pktlab_ports_cleanup(&datapath->ports);
    pktlab_eal_cleanup(&datapath->eal);
    datapath->ports_ready = false;
    datapath->started = false;
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

    if (datapath->running_message[0] == '\0') {
        (void) snprintf(
            buffer,
            buffer_cap,
            "configured TAP ports %s/%s",
            datapath->ports.infos[0].name,
            datapath->ports.infos[1].name
        );
        buffer[buffer_cap - 1U] = '\0';
        return;
    }

    (void) snprintf(buffer, buffer_cap, "%s", datapath->running_message);
    buffer[buffer_cap - 1U] = '\0';
}

bool pktlab_datapath_ports_ready(const struct pktlab_datapath *datapath)
{
    return datapath->ports_ready;
}
