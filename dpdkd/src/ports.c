#include "ports.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

#include "datapath.h"

static void pktlab_ports_set_error(
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

static int pktlab_ports_copy_name(char *dst, size_t dst_len, const char *value)
{
    int written;

    written = snprintf(dst, dst_len, "%s", value);
    if (written < 0 || (size_t) written >= dst_len) {
        return -1;
    }
    return 0;
}

int pktlab_ports_prepare(
    struct pktlab_ports_config *ports,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
)
{
    memset(ports, 0, sizeof(*ports));

    if (config->burst_size == 0U || config->burst_size > UINT16_MAX) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "burst_size must be between 1 and 65535"
        );
        return -1;
    }
    if (config->rx_queue_size == 0U || config->rx_queue_size > UINT16_MAX) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "rx_queue_size must be between 1 and 65535"
        );
        return -1;
    }
    if (config->tx_queue_size == 0U || config->tx_queue_size > UINT16_MAX) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "tx_queue_size must be between 1 and 65535"
        );
        return -1;
    }
    if (config->mempool_size == 0U) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "mempool_size must be greater than zero"
        );
        return -1;
    }
    if (
        config->ingress_port_name == NULL
        || config->ingress_port_name[0] == '\0'
        || config->egress_port_name == NULL
        || config->egress_port_name[0] == '\0'
    ) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "ingress and egress port names must be non-empty"
        );
        return -1;
    }
    if (strcmp(config->ingress_port_name, config->egress_port_name) == 0) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "ingress and egress port names must be different"
        );
        return -1;
    }

    ports->burst_size = (uint16_t) config->burst_size;
    ports->rx_queue_size = (uint16_t) config->rx_queue_size;
    ports->tx_queue_size = (uint16_t) config->tx_queue_size;
    ports->mempool_size = config->mempool_size;

    if (
        pktlab_ports_copy_name(
            ports->infos[0].name,
            sizeof(ports->infos[0].name),
            config->ingress_port_name
        ) != 0
    ) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "ingress port name exceeds the supported length"
        );
        return -1;
    }
    ports->infos[0].port_id = 0U;
    ports->infos[0].role = PKTLAB_PORT_ROLE_INGRESS;
    ports->infos[0].state = PKTLAB_PORT_STATE_DOWN;

    if (
        pktlab_ports_copy_name(
            ports->infos[1].name,
            sizeof(ports->infos[1].name),
            config->egress_port_name
        ) != 0
    ) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "egress port name exceeds the supported length"
        );
        return -1;
    }
    ports->infos[1].port_id = 1U;
    ports->infos[1].role = PKTLAB_PORT_ROLE_EGRESS;
    ports->infos[1].state = PKTLAB_PORT_STATE_DOWN;

    return 0;
}

void pktlab_ports_set_state(struct pktlab_ports_config *ports, enum pktlab_port_state state)
{
    size_t index;

    for (index = 0U; index < PKTLAB_DPDKD_PORT_COUNT; index++) {
        ports->infos[index].state = state;
    }
}
