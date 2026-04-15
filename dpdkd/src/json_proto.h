#ifndef PKTLAB_DPDKD_JSON_PROTO_H
#define PKTLAB_DPDKD_JSON_PROTO_H

#include <stddef.h>

#include "pktlab_dpdkd/errors.h"
#include "pktlab_dpdkd/types.h"

#define PKTLAB_JSON_PROTO_MAX_FRAME_SIZE 16384U
#define PKTLAB_JSON_PROTO_MAX_ID_LEN 64U
#define PKTLAB_JSON_PROTO_MAX_CMD_LEN 32U
#define PKTLAB_JSON_PROTO_STATUS_OK 0
#define PKTLAB_JSON_PROTO_STATUS_EOF 1
#define PKTLAB_JSON_PROTO_STATUS_ERROR -1

struct pktlab_ipc_request {
    char id[PKTLAB_JSON_PROTO_MAX_ID_LEN + 1U];
    char cmd[PKTLAB_JSON_PROTO_MAX_CMD_LEN + 1U];
};

int pktlab_json_proto_read_frame(
    int fd,
    char *buffer,
    size_t buffer_cap,
    size_t *frame_len,
    struct pktlab_dpdkd_error *error
);
int pktlab_json_proto_write_frame(
    int fd,
    const char *json,
    size_t json_len,
    struct pktlab_dpdkd_error *error
);
int pktlab_json_proto_parse_request(
    const char *json,
    size_t json_len,
    struct pktlab_ipc_request *request,
    struct pktlab_dpdkd_error *error
);
int pktlab_json_proto_make_pong_payload(char *buffer, size_t buffer_cap, size_t *json_len);
int pktlab_json_proto_make_version_payload(char *buffer, size_t buffer_cap, size_t *json_len);
int pktlab_json_proto_make_health_payload(
    const struct pktlab_health_snapshot *health,
    char *buffer,
    size_t buffer_cap,
    size_t *json_len
);
int pktlab_json_proto_make_ports_payload(
    const struct pktlab_port_info *ports,
    size_t port_count,
    char *buffer,
    size_t buffer_cap,
    size_t *json_len
);
int pktlab_json_proto_make_stats_payload(
    const struct dp_stats_snapshot *stats,
    char *buffer,
    size_t buffer_cap,
    size_t *json_len
);
int pktlab_json_proto_make_success(
    const char *request_id,
    const char *payload_json,
    char *buffer,
    size_t buffer_cap,
    size_t *json_len,
    struct pktlab_dpdkd_error *error
);
int pktlab_json_proto_make_error(
    const char *request_id,
    const struct pktlab_dpdkd_error *error,
    char *buffer,
    size_t buffer_cap,
    size_t *json_len
);

#endif /* PKTLAB_DPDKD_JSON_PROTO_H */
