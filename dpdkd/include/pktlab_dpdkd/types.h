#ifndef PKTLAB_DPDKD_TYPES_H
#define PKTLAB_DPDKD_TYPES_H

#include <stdbool.h>
#include <stdint.h>

#define PKTLAB_DPDKD_NAME_LEN 32
#define PKTLAB_DPDKD_MESSAGE_LEN 128

enum pktlab_l4_proto {
    PKTLAB_L4_PROTO_ANY = 0,
    PKTLAB_L4_PROTO_ICMP = 1,
    PKTLAB_L4_PROTO_TCP = 6,
    PKTLAB_L4_PROTO_UDP = 17
};

enum dp_action_type {
    DP_ACTION_FORWARD = 1,
    DP_ACTION_DROP = 2,
    DP_ACTION_COUNT = 3,
    DP_ACTION_MIRROR = 4
};

enum pktlab_port_role {
    PKTLAB_PORT_ROLE_INGRESS = 1,
    PKTLAB_PORT_ROLE_EGRESS = 2
};

enum pktlab_port_state {
    PKTLAB_PORT_STATE_DOWN = 0,
    PKTLAB_PORT_STATE_UP = 1
};

enum pktlab_dp_state {
    PKTLAB_DP_STATE_STARTING = 1,
    PKTLAB_DP_STATE_RUNNING = 2,
    PKTLAB_DP_STATE_PAUSED = 3,
    PKTLAB_DP_STATE_DEGRADED = 4,
    PKTLAB_DP_STATE_STOPPING = 5,
    PKTLAB_DP_STATE_FAILED = 6
};

struct pkt_meta {
    uint16_t ether_type;
    uint8_t l4_proto;
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint16_t pkt_len;
    uint8_t flags;
};

struct dp_rule_match {
    uint8_t proto;
    uint32_t src_ip;
    uint32_t dst_ip;
    uint32_t src_cidr_ip;
    uint32_t src_cidr_mask;
    uint32_t dst_cidr_ip;
    uint32_t dst_cidr_mask;
    uint16_t src_port;
    uint16_t dst_port;

    uint8_t has_src_ip;
    uint8_t has_dst_ip;
    uint8_t has_src_cidr;
    uint8_t has_dst_cidr;
    uint8_t has_src_port;
    uint8_t has_dst_port;
};

struct dp_rule {
    uint32_t id;
    uint32_t priority;
    struct dp_rule_match match;
    enum dp_action_type action_type;
    uint16_t out_port_id;
};

struct dp_stats_snapshot {
    uint64_t rx_packets;
    uint64_t tx_packets;
    uint64_t drop_packets;
    uint64_t drop_parse_errors;
    uint64_t drop_no_match;
    uint64_t rx_bursts;
    uint64_t tx_bursts;
    uint64_t unsent_packets;
};

struct pktlab_port_info {
    char name[PKTLAB_DPDKD_NAME_LEN];
    uint16_t port_id;
    enum pktlab_port_role role;
    enum pktlab_port_state state;
};

struct pktlab_health_snapshot {
    enum pktlab_dp_state state;
    char message[PKTLAB_DPDKD_MESSAGE_LEN];
    uint32_t applied_rule_version;
    bool ports_ready;
    bool paused;
};

#endif /* PKTLAB_DPDKD_TYPES_H */
