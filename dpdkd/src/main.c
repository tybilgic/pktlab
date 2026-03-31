#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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
        "Usage: %s [--socket-path PATH]\n"
        "Default socket path: %s\n",
        program_name,
        PKTLAB_DPDKD_DEFAULT_SOCKET_PATH
    );
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

    for (argi = 1; argi < argc; argi++) {
        if (strcmp(argv[argi], "--socket-path") == 0) {
            if (argi + 1 >= argc) {
                pktlab_print_usage(argv[0]);
                return EXIT_FAILURE;
            }
            config.socket_path = argv[++argi];
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
