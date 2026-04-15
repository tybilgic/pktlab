#include "datapath.h"

#include <errno.h>
#include <stdbool.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "actions.h"
#include "parser.h"

#if PKTLAB_DPDKD_HAS_DPDK
#include <rte_ethdev.h>
#include <rte_lcore.h>
#include <rte_pause.h>
#endif

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

static void pktlab_datapath_copy_message(char *dst, size_t dst_len, const char *message)
{
    if (dst_len == 0U) {
        return;
    }

    if (message == NULL) {
        dst[0] = '\0';
        return;
    }

    (void) snprintf(dst, dst_len, "%s", message);
    dst[dst_len - 1U] = '\0';
}

static int pktlab_datapath_init_worker_sync(
    struct pktlab_datapath *datapath,
    struct pktlab_dpdkd_error *error
)
{
    int status;

    if (datapath->worker_sync_initialized) {
        return 0;
    }

    status = pthread_mutex_init(&datapath->worker_lock, NULL);
    if (status != 0) {
        pktlab_datapath_copy_message(
            datapath->worker_error_message,
            sizeof(datapath->worker_error_message),
            "failed to initialize datapath worker mutex"
        );
        pktlab_datapath_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            datapath->worker_error_message
        );
        return -1;
    }

    status = pthread_cond_init(&datapath->worker_cond, NULL);
    if (status != 0) {
        (void) pthread_mutex_destroy(&datapath->worker_lock);
        pktlab_datapath_copy_message(
            datapath->worker_error_message,
            sizeof(datapath->worker_error_message),
            "failed to initialize datapath worker condition variable"
        );
        pktlab_datapath_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            datapath->worker_error_message
        );
        return -1;
    }

    datapath->worker_sync_initialized = true;
    return 0;
}

static void pktlab_datapath_destroy_worker_sync(struct pktlab_datapath *datapath)
{
    if (!datapath->worker_sync_initialized) {
        return;
    }

    (void) pthread_cond_destroy(&datapath->worker_cond);
    (void) pthread_mutex_destroy(&datapath->worker_lock);
    datapath->worker_sync_initialized = false;
}

static void pktlab_datapath_signal_worker_start(
    struct pktlab_datapath *datapath,
    bool start_ok,
    enum pktlab_dpdkd_error_code error_code,
    const char *message
)
{
    (void) pthread_mutex_lock(&datapath->worker_lock);
    datapath->worker_start_ok = start_ok;
    datapath->worker_start_ready = true;
    datapath->worker_error_code = error_code;
    pktlab_datapath_copy_message(
        datapath->worker_error_message,
        sizeof(datapath->worker_error_message),
        message
    );
    (void) pthread_cond_signal(&datapath->worker_cond);
    (void) pthread_mutex_unlock(&datapath->worker_lock);
}

#if PKTLAB_DPDKD_HAS_DPDK
static bool pktlab_datapath_forward_direction(
    struct pktlab_datapath *datapath,
    size_t ingress_index,
    size_t egress_index
)
{
    struct rte_mbuf *packets[PKTLAB_DPDKD_MAX_BURST_SIZE];
    struct dp_stats_snapshot burst_stats;
    uint16_t rx_count;
    uint16_t candidate_count;
    uint16_t index;
    uint16_t sent_count;

    memset(&burst_stats, 0, sizeof(burst_stats));
    rx_count = rte_eth_rx_burst(
        datapath->ports.infos[ingress_index].port_id,
        0U,
        packets,
        datapath->ports.burst_size
    );
    if (rx_count == 0U) {
        return false;
    }

    burst_stats.rx_bursts = 1U;
    burst_stats.rx_packets = rx_count;

    candidate_count = 0U;
    for (index = 0U; index < rx_count; index++) {
        struct pkt_meta meta;

        if (pktlab_parser_parse(packets[index], &meta) != 0) {
            burst_stats.drop_parse_errors++;
            burst_stats.drop_packets++;
            pktlab_actions_drop_burst(&packets[index], 1U);
            continue;
        }

        packets[candidate_count++] = packets[index];
    }

    if (candidate_count == 0U) {
        pktlab_stats_add(&datapath->stats, &burst_stats);
        return true;
    }

    burst_stats.tx_bursts = 1U;
    sent_count = pktlab_actions_forward_burst(
        datapath->ports.infos[egress_index].port_id,
        packets,
        candidate_count
    );
    burst_stats.tx_packets = sent_count;
    if (sent_count < candidate_count) {
        const uint16_t unsent_count = (uint16_t) (candidate_count - sent_count);

        burst_stats.unsent_packets = unsent_count;
        burst_stats.drop_packets += unsent_count;
    }

    pktlab_stats_add(&datapath->stats, &burst_stats);
    return true;
}
#endif

static void *pktlab_datapath_worker_main(void *ctx)
{
    struct pktlab_datapath *datapath;

    datapath = ctx;

#if !PKTLAB_DPDKD_HAS_DPDK
    pktlab_datapath_signal_worker_start(
        datapath,
        false,
        PKTLAB_DPDKD_ERR_STATE_CONFLICT,
        "libdpdk was not available at build time"
    );
    return NULL;
#else
    if (rte_thread_register() != 0) {
        pktlab_datapath_signal_worker_start(
            datapath,
            false,
            PKTLAB_DPDKD_ERR_PORT_INIT,
            "failed to register the datapath forwarding thread with DPDK"
        );
        return NULL;
    }

    pktlab_datapath_signal_worker_start(datapath, true, PKTLAB_DPDKD_ERR_NONE, NULL);

    while (!atomic_load_explicit(&datapath->stop_requested, memory_order_relaxed)) {
        bool did_work;

        did_work = pktlab_datapath_forward_direction(datapath, 0U, 1U);
        did_work = pktlab_datapath_forward_direction(datapath, 1U, 0U) || did_work;
        if (!did_work) {
            rte_pause();
        }
    }

    rte_thread_unregister();
    return NULL;
#endif
}

static int pktlab_datapath_start_worker(
    struct pktlab_datapath *datapath,
    struct pktlab_dpdkd_error *error
)
{
    int status;

    if (pktlab_datapath_init_worker_sync(datapath, error) != 0) {
        return -1;
    }

    atomic_store_explicit(&datapath->stop_requested, false, memory_order_relaxed);
    datapath->worker_start_ready = false;
    datapath->worker_start_ok = false;
    datapath->worker_error_code = PKTLAB_DPDKD_ERR_NONE;
    datapath->worker_error_message[0] = '\0';
    pktlab_stats_reset(&datapath->stats);

    status = pthread_create(&datapath->worker_thread, NULL, pktlab_datapath_worker_main, datapath);
    if (status != 0) {
        (void) snprintf(
            datapath->worker_error_message,
            sizeof(datapath->worker_error_message),
            "failed to start the datapath forwarding thread: %s",
            strerror(status)
        );
        datapath->worker_error_message[sizeof(datapath->worker_error_message) - 1U] = '\0';
        pktlab_datapath_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            datapath->worker_error_message
        );
        return -1;
    }

    datapath->worker_thread_started = true;

    (void) pthread_mutex_lock(&datapath->worker_lock);
    while (!datapath->worker_start_ready) {
        (void) pthread_cond_wait(&datapath->worker_cond, &datapath->worker_lock);
    }
    (void) pthread_mutex_unlock(&datapath->worker_lock);

    if (!datapath->worker_start_ok) {
        atomic_store_explicit(&datapath->stop_requested, true, memory_order_relaxed);
        (void) pthread_join(datapath->worker_thread, NULL);
        datapath->worker_thread_started = false;
        pktlab_datapath_set_error(
            error,
            datapath->worker_error_code,
            datapath->worker_error_message
        );
        return -1;
    }

    return 0;
}

static void pktlab_datapath_stop_worker(struct pktlab_datapath *datapath)
{
    if (!datapath->worker_thread_started) {
        return;
    }

    atomic_store_explicit(&datapath->stop_requested, true, memory_order_relaxed);
    (void) pthread_join(datapath->worker_thread, NULL);
    datapath->worker_thread_started = false;
    datapath->worker_start_ready = false;
    datapath->worker_start_ok = false;
}

int pktlab_datapath_init(
    struct pktlab_datapath *datapath,
    const struct pktlab_datapath_config *config,
    struct pktlab_dpdkd_error *error
)
{
    memset(datapath, 0, sizeof(*datapath));
    atomic_init(&datapath->stop_requested, false);
    if (pktlab_stats_init(&datapath->stats) != 0) {
        pktlab_datapath_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "failed to initialize datapath stats tracking"
        );
        return -1;
    }

    if (pktlab_eal_prepare(&datapath->eal, config, error) != 0) {
        pktlab_stats_destroy(&datapath->stats);
        return -1;
    }
    if (pktlab_ports_prepare(&datapath->ports, config, error) != 0) {
        pktlab_stats_destroy(&datapath->stats);
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
    if (pktlab_datapath_start_worker(datapath, error) != 0) {
        pktlab_ports_cleanup(&datapath->ports);
        pktlab_eal_cleanup(&datapath->eal);
        return -1;
    }

    datapath->ports_ready = pktlab_ports_ready(&datapath->ports);
    (void) snprintf(
        datapath->running_message,
        sizeof(datapath->running_message),
        "DPDK TAP ports %s/%s ready; forwarding loop active",
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

    pktlab_datapath_stop_worker(datapath);
    pktlab_ports_cleanup(&datapath->ports);
    pktlab_eal_cleanup(&datapath->eal);
    pktlab_datapath_destroy_worker_sync(datapath);
    pktlab_stats_destroy(&datapath->stats);
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

void pktlab_datapath_ports_snapshot(
    const struct pktlab_datapath *datapath,
    struct pktlab_port_info *infos,
    size_t infos_cap,
    size_t *info_count
)
{
    pktlab_ports_snapshot(&datapath->ports, infos, infos_cap, info_count);
}

void pktlab_datapath_stats_snapshot(
    const struct pktlab_datapath *datapath,
    struct dp_stats_snapshot *snapshot
)
{
    pktlab_stats_snapshot(&datapath->stats, snapshot);
}
