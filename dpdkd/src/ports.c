#include "ports.h"

#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "datapath.h"

#if PKTLAB_DPDKD_HAS_DPDK
#include <rte_common.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#endif

#define PKTLAB_DPDKD_MEMPOOL_NAME_LEN 64

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

    if (config->burst_size == 0U || config->burst_size > PKTLAB_DPDKD_MAX_BURST_SIZE) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "burst_size must be between 1 and 256"
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

int pktlab_ports_start(
    struct pktlab_ports_config *ports,
    const struct pktlab_eal_config *eal,
    struct pktlab_dpdkd_error *error
)
{
#if PKTLAB_DPDKD_HAS_DPDK
    const char *vdev_names[PKTLAB_DPDKD_PORT_COUNT];
    char mempool_name[PKTLAB_DPDKD_MEMPOOL_NAME_LEN];
    size_t index;
    int written;

    if (ports->ready) {
        return 0;
    }

    written = snprintf(
        mempool_name,
        sizeof(mempool_name),
        "pktlab-mbuf-%ld",
        (long) getpid()
    );
    if (written < 0 || (size_t) written >= sizeof(mempool_name)) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "failed to render the datapath mempool name"
        );
        return -1;
    }

    ports->mempool = rte_pktmbuf_pool_create(
        mempool_name,
        ports->mempool_size,
        0U,
        0U,
        RTE_MBUF_DEFAULT_BUF_SIZE,
        SOCKET_ID_ANY
    );
    if (ports->mempool == NULL) {
        pktlab_ports_set_error(
            error,
            PKTLAB_DPDKD_ERR_PORT_INIT,
            "failed to create the datapath mbuf pool"
        );
        return -1;
    }

    vdev_names[0] = eal->ingress_vdev_name;
    vdev_names[1] = eal->egress_vdev_name;

    for (index = 0U; index < PKTLAB_DPDKD_PORT_COUNT; index++) {
        struct rte_eth_conf port_conf;
        uint16_t port_id;
        uint16_t rx_desc;
        uint16_t tx_desc;
        int socket_id;

        memset(&port_conf, 0, sizeof(port_conf));
        if (rte_eth_dev_get_port_by_name(vdev_names[index], &port_id) != 0) {
            pktlab_ports_set_error(
                error,
                PKTLAB_DPDKD_ERR_PORT_INIT,
                "failed to resolve the TAP PMD port identifier"
            );
            return -1;
        }

        ports->infos[index].port_id = port_id;
        ports->attached[index] = true;
        rx_desc = ports->rx_queue_size;
        tx_desc = ports->tx_queue_size;

        if (rte_eth_dev_adjust_nb_rx_tx_desc(port_id, &rx_desc, &tx_desc) < 0) {
            pktlab_ports_set_error(
                error,
                PKTLAB_DPDKD_ERR_PORT_INIT,
                "failed to adjust TAP PMD queue descriptor counts"
            );
            return -1;
        }

        if (rte_eth_dev_configure(port_id, 1U, 1U, &port_conf) < 0) {
            pktlab_ports_set_error(
                error,
                PKTLAB_DPDKD_ERR_PORT_INIT,
                "failed to configure the TAP PMD port"
            );
            return -1;
        }

        socket_id = rte_eth_dev_socket_id(port_id);
        if (socket_id < 0) {
            socket_id = SOCKET_ID_ANY;
        }

        if (rte_eth_rx_queue_setup(port_id, 0U, rx_desc, (unsigned int) socket_id, NULL, ports->mempool) < 0) {
            pktlab_ports_set_error(
                error,
                PKTLAB_DPDKD_ERR_PORT_INIT,
                "failed to configure the TAP PMD receive queue"
            );
            return -1;
        }

        if (rte_eth_tx_queue_setup(port_id, 0U, tx_desc, (unsigned int) socket_id, NULL) < 0) {
            pktlab_ports_set_error(
                error,
                PKTLAB_DPDKD_ERR_PORT_INIT,
                "failed to configure the TAP PMD transmit queue"
            );
            return -1;
        }

        if (rte_eth_dev_start(port_id) < 0) {
            pktlab_ports_set_error(
                error,
                PKTLAB_DPDKD_ERR_PORT_INIT,
                "failed to start the TAP PMD port"
            );
            return -1;
        }
    }

    ports->ready = true;
    pktlab_ports_set_state(ports, PKTLAB_PORT_STATE_UP);
    return 0;
#else
    (void) ports;
    (void) eal;
    pktlab_ports_set_error(
        error,
        PKTLAB_DPDKD_ERR_STATE_CONFLICT,
        "libdpdk was not available at build time"
    );
    return -1;
#endif
}

void pktlab_ports_cleanup(struct pktlab_ports_config *ports)
{
#if PKTLAB_DPDKD_HAS_DPDK
    size_t index;

    for (index = 0U; index < PKTLAB_DPDKD_PORT_COUNT; index++) {
        if (!ports->attached[index]) {
            continue;
        }

        (void) rte_eth_dev_stop(ports->infos[index].port_id);
        (void) rte_eth_dev_close(ports->infos[index].port_id);
        ports->attached[index] = false;
    }

    if (ports->mempool != NULL) {
        rte_mempool_free(ports->mempool);
        ports->mempool = NULL;
    }
#endif

    ports->ready = false;
    pktlab_ports_set_state(ports, PKTLAB_PORT_STATE_DOWN);
}

bool pktlab_ports_ready(const struct pktlab_ports_config *ports)
{
    return ports->ready;
}

void pktlab_ports_set_state(struct pktlab_ports_config *ports, enum pktlab_port_state state)
{
    size_t index;

    for (index = 0U; index < PKTLAB_DPDKD_PORT_COUNT; index++) {
        ports->infos[index].state = state;
    }
}
