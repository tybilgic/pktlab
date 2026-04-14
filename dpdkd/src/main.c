#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <stdint.h>

#include "datapath.h"
#include "daemon.h"
#include "log.h"

static volatile sig_atomic_t g_stop_requested = 0;

static void pktlab_handle_signal(int signal_number)
{
    (void) signal_number;
    g_stop_requested = 1;
}

static int pktlab_install_signal_handlers(void)
{
    struct sigaction action;

    memset(&action, 0, sizeof(action));
    action.sa_handler = pktlab_handle_signal;

    if (sigaction(SIGINT, &action, NULL) != 0) {
        return -1;
    }
    if (sigaction(SIGTERM, &action, NULL) != 0) {
        return -1;
    }

    signal(SIGPIPE, SIG_IGN);
    return 0;
}

static void pktlab_print_usage(const char *program_name)
{
    fprintf(
        stderr,
        "Usage: %s [--socket-path PATH] [--lcores SPEC] [--hugepages-mb MB]\n"
        "          [--burst-size N] [--rx-queue-size N] [--tx-queue-size N]\n"
        "          [--mempool-size N] [--ingress-port-name NAME] [--egress-port-name NAME]\n"
        "Default socket path: %s\n"
        "Default lcores: %s\n"
        "Default hugepages: %u MB\n"
        "Default burst size: %u\n"
        "Default queue sizes: rx=%u tx=%u\n"
        "Default mempool size: %u\n"
        "Default TAP ports: ingress=%s egress=%s\n",
        program_name,
        PKTLAB_DPDKD_DEFAULT_SOCKET_PATH,
        PKTLAB_DPDKD_DEFAULT_LCORES,
        PKTLAB_DPDKD_DEFAULT_HUGEPAGES_MB,
        PKTLAB_DPDKD_DEFAULT_BURST_SIZE,
        PKTLAB_DPDKD_DEFAULT_RX_QUEUE_SIZE,
        PKTLAB_DPDKD_DEFAULT_TX_QUEUE_SIZE,
        PKTLAB_DPDKD_DEFAULT_MEMPOOL_SIZE,
        PKTLAB_DPDKD_DEFAULT_INGRESS_PORT_NAME,
        PKTLAB_DPDKD_DEFAULT_EGRESS_PORT_NAME
    );
}

static int pktlab_parse_u32_arg(const char *name, const char *value, uint32_t *out)
{
    char *endptr;
    unsigned long parsed;

    if (value == NULL || value[0] == '\0') {
        fprintf(stderr, "%s requires a non-empty value\n", name);
        return -1;
    }

    endptr = NULL;
    parsed = strtoul(value, &endptr, 10);
    if (endptr == value || *endptr != '\0') {
        fprintf(stderr, "%s requires an integer value\n", name);
        return -1;
    }
    if (parsed > UINT32_MAX) {
        fprintf(stderr, "%s exceeds the supported range\n", name);
        return -1;
    }

    *out = (uint32_t) parsed;
    return 0;
}

int main(int argc, char **argv)
{
    struct pktlab_daemon daemon;
    struct pktlab_daemon_config config;
    struct pktlab_dpdkd_error error;
    int argi;
    int exit_code;

    memset(&config, 0, sizeof(config));
    config.socket_path = PKTLAB_DPDKD_DEFAULT_SOCKET_PATH;
    config.log_level = PKTLAB_LOG_LEVEL_INFO;
    config.datapath.lcores = PKTLAB_DPDKD_DEFAULT_LCORES;
    config.datapath.hugepages_mb = PKTLAB_DPDKD_DEFAULT_HUGEPAGES_MB;
    config.datapath.burst_size = PKTLAB_DPDKD_DEFAULT_BURST_SIZE;
    config.datapath.rx_queue_size = PKTLAB_DPDKD_DEFAULT_RX_QUEUE_SIZE;
    config.datapath.tx_queue_size = PKTLAB_DPDKD_DEFAULT_TX_QUEUE_SIZE;
    config.datapath.mempool_size = PKTLAB_DPDKD_DEFAULT_MEMPOOL_SIZE;
    config.datapath.ingress_port_name = PKTLAB_DPDKD_DEFAULT_INGRESS_PORT_NAME;
    config.datapath.egress_port_name = PKTLAB_DPDKD_DEFAULT_EGRESS_PORT_NAME;

    for (argi = 1; argi < argc; argi++) {
        if (strcmp(argv[argi], "--socket-path") == 0) {
            if (argi + 1 >= argc) {
                pktlab_print_usage(argv[0]);
                return EXIT_FAILURE;
            }
            config.socket_path = argv[++argi];
        } else if (strcmp(argv[argi], "--lcores") == 0) {
            if (argi + 1 >= argc) {
                pktlab_print_usage(argv[0]);
                return EXIT_FAILURE;
            }
            config.datapath.lcores = argv[++argi];
        } else if (strcmp(argv[argi], "--hugepages-mb") == 0) {
            if (
                argi + 1 >= argc
                || pktlab_parse_u32_arg(
                    "--hugepages-mb",
                    argv[argi + 1],
                    &config.datapath.hugepages_mb
                ) != 0
            ) {
                return EXIT_FAILURE;
            }
            argi++;
        } else if (strcmp(argv[argi], "--burst-size") == 0) {
            if (
                argi + 1 >= argc
                || pktlab_parse_u32_arg(
                    "--burst-size",
                    argv[argi + 1],
                    &config.datapath.burst_size
                ) != 0
            ) {
                return EXIT_FAILURE;
            }
            argi++;
        } else if (strcmp(argv[argi], "--rx-queue-size") == 0) {
            if (
                argi + 1 >= argc
                || pktlab_parse_u32_arg(
                    "--rx-queue-size",
                    argv[argi + 1],
                    &config.datapath.rx_queue_size
                ) != 0
            ) {
                return EXIT_FAILURE;
            }
            argi++;
        } else if (strcmp(argv[argi], "--tx-queue-size") == 0) {
            if (
                argi + 1 >= argc
                || pktlab_parse_u32_arg(
                    "--tx-queue-size",
                    argv[argi + 1],
                    &config.datapath.tx_queue_size
                ) != 0
            ) {
                return EXIT_FAILURE;
            }
            argi++;
        } else if (strcmp(argv[argi], "--mempool-size") == 0) {
            if (
                argi + 1 >= argc
                || pktlab_parse_u32_arg(
                    "--mempool-size",
                    argv[argi + 1],
                    &config.datapath.mempool_size
                ) != 0
            ) {
                return EXIT_FAILURE;
            }
            argi++;
        } else if (strcmp(argv[argi], "--ingress-port-name") == 0) {
            if (argi + 1 >= argc) {
                pktlab_print_usage(argv[0]);
                return EXIT_FAILURE;
            }
            config.datapath.ingress_port_name = argv[++argi];
        } else if (strcmp(argv[argi], "--egress-port-name") == 0) {
            if (argi + 1 >= argc) {
                pktlab_print_usage(argv[0]);
                return EXIT_FAILURE;
            }
            config.datapath.egress_port_name = argv[++argi];
        } else if (strcmp(argv[argi], "--help") == 0) {
            pktlab_print_usage(argv[0]);
            return EXIT_SUCCESS;
        } else {
            pktlab_print_usage(argv[0]);
            return EXIT_FAILURE;
        }
    }

    pktlab_log_init(config.log_level);

    if (pktlab_install_signal_handlers() != 0) {
        PKTLAB_LOG_ERROR("failed to install signal handlers");
        return EXIT_FAILURE;
    }

    memset(&error, 0, sizeof(error));
    if (pktlab_daemon_init(&daemon, &config, &error) != 0) {
        PKTLAB_LOG_ERROR("daemon initialization failed: %s", error.message);
        return EXIT_FAILURE;
    }

    exit_code = EXIT_SUCCESS;
    if (pktlab_daemon_run(&daemon, &g_stop_requested) != 0) {
        exit_code = EXIT_FAILURE;
    }

    pktlab_daemon_cleanup(&daemon);
    return exit_code;
}
