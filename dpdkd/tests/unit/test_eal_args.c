#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

#include "datapath.h"
#include "eal.h"
#include "pktlab_dpdkd/errors.h"

static bool pktlab_argv_contains(
    const struct pktlab_eal_argv *argv,
    const char *expected
)
{
    int index;

    for (index = 0; index < argv->argc; index++) {
        if (strcmp(argv->argv[index], expected) == 0) {
            return true;
        }
    }

    return false;
}

static const char *pktlab_find_arg_with_prefix(
    const struct pktlab_eal_argv *argv,
    const char *prefix
)
{
    size_t prefix_len;
    int index;

    prefix_len = strlen(prefix);
    for (index = 0; index < argv->argc; index++) {
        if (strncmp(argv->argv[index], prefix, prefix_len) == 0) {
            return argv->argv[index];
        }
    }

    return NULL;
}

int main(void)
{
    struct pktlab_datapath_config config = {
        .lcores = "1",
        .hugepages_mb = 256U,
        .burst_size = PKTLAB_DPDKD_DEFAULT_BURST_SIZE,
        .rx_queue_size = PKTLAB_DPDKD_DEFAULT_RX_QUEUE_SIZE,
        .tx_queue_size = PKTLAB_DPDKD_DEFAULT_TX_QUEUE_SIZE,
        .mempool_size = PKTLAB_DPDKD_DEFAULT_MEMPOOL_SIZE,
        .ingress_port_name = PKTLAB_DPDKD_DEFAULT_INGRESS_PORT_NAME,
        .egress_port_name = PKTLAB_DPDKD_DEFAULT_EGRESS_PORT_NAME,
    };
    struct pktlab_eal_config eal;
    struct pktlab_eal_argv eal_argv;
    struct pktlab_dpdkd_error error = {0};

    assert(pktlab_eal_prepare(&eal, &config, &error) == 0);
    assert(pktlab_eal_build_argv(&eal, &eal_argv, &error) == 0);
    assert(eal_argv.argc == PKTLAB_DPDKD_EAL_ARGC);
    assert(pktlab_argv_contains(&eal_argv, "--in-memory"));
    assert(!pktlab_argv_contains(&eal_argv, "--huge-unlink=always"));
    assert(pktlab_argv_contains(&eal_argv, "--socket-mem=256"));
    assert(pktlab_argv_contains(&eal_argv, "--vdev=net_tap0,iface=dtap0"));
    assert(pktlab_argv_contains(&eal_argv, "--vdev=net_tap1,iface=dtap1"));
    assert(
        pktlab_find_arg_with_prefix(&eal_argv, "--file-prefix=pktlab-") != NULL
    );

    return 0;
}
