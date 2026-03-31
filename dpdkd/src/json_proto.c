#include "json_proto.h"

#include <arpa/inet.h>
#include <errno.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "health.h"
#include "pktlab_dpdkd/version.h"

#define PKTLAB_JSON_PROTO_MAX_NESTING 16U
#define PKTLAB_JSON_PROTO_UNKNOWN_ID "unknown"

static void pktlab_json_proto_set_error(
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

const char *pktlab_dpdkd_error_code_name(enum pktlab_dpdkd_error_code code)
{
    switch (code) {
    case PKTLAB_DPDKD_ERR_NONE:
        return "NONE";
    case PKTLAB_DPDKD_ERR_INVALID_REQUEST:
        return "INVALID_REQUEST";
    case PKTLAB_DPDKD_ERR_INVALID_PAYLOAD:
        return "INVALID_PAYLOAD";
    case PKTLAB_DPDKD_ERR_UNKNOWN_COMMAND:
        return "UNKNOWN_COMMAND";
    case PKTLAB_DPDKD_ERR_RULE_VALIDATION:
        return "RULE_VALIDATION_ERROR";
    case PKTLAB_DPDKD_ERR_PORT_INIT:
        return "PORT_INIT_ERROR";
    case PKTLAB_DPDKD_ERR_STATE_CONFLICT:
        return "STATE_CONFLICT";
    case PKTLAB_DPDKD_ERR_INTERNAL:
        return "INTERNAL_ERROR";
    default:
        return "INTERNAL_ERROR";
    }
}

static int pktlab_json_proto_read_exact(int fd, void *buffer, size_t length)
{
    size_t total;
    ssize_t bytes_read;
    uint8_t *cursor;

    total = 0U;
    cursor = buffer;

    while (total < length) {
        bytes_read = read(fd, cursor + total, length - total);
        if (bytes_read == 0) {
            return PKTLAB_JSON_PROTO_STATUS_EOF;
        }
        if (bytes_read < 0) {
            if (errno == EINTR) {
                continue;
            }
            return PKTLAB_JSON_PROTO_STATUS_ERROR;
        }
        total += (size_t) bytes_read;
    }

    return PKTLAB_JSON_PROTO_STATUS_OK;
}

static int pktlab_json_proto_write_exact(int fd, const void *buffer, size_t length)
{
    size_t total;
    ssize_t bytes_written;
    const uint8_t *cursor;

    total = 0U;
    cursor = buffer;

    while (total < length) {
        bytes_written = write(fd, cursor + total, length - total);
        if (bytes_written < 0) {
            if (errno == EINTR) {
                continue;
            }
            return PKTLAB_JSON_PROTO_STATUS_ERROR;
        }
        total += (size_t) bytes_written;
    }

    return PKTLAB_JSON_PROTO_STATUS_OK;
}

int pktlab_json_proto_read_frame(
    int fd,
    char *buffer,
    size_t buffer_cap,
    size_t *frame_len,
    struct pktlab_dpdkd_error *error
)
{
    uint32_t net_length;
    uint32_t payload_length;
    int status;

    status = pktlab_json_proto_read_exact(fd, &net_length, sizeof(net_length));
    if (status != PKTLAB_JSON_PROTO_STATUS_OK) {
        return status;
    }

    payload_length = ntohl(net_length);
    if (payload_length == 0U || payload_length >= buffer_cap) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "frame length is invalid or exceeds the configured maximum"
        );
        return PKTLAB_JSON_PROTO_STATUS_ERROR;
    }

    status = pktlab_json_proto_read_exact(fd, buffer, payload_length);
    if (status != PKTLAB_JSON_PROTO_STATUS_OK) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "failed to read full JSON frame payload"
        );
        return PKTLAB_JSON_PROTO_STATUS_ERROR;
    }

    buffer[payload_length] = '\0';
    *frame_len = payload_length;
    return PKTLAB_JSON_PROTO_STATUS_OK;
}

int pktlab_json_proto_write_frame(
    int fd,
    const char *json,
    size_t json_len,
    struct pktlab_dpdkd_error *error
)
{
    uint32_t net_length;
    int status;

    if (json_len == 0U || json_len > UINT32_MAX) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "cannot send an empty or oversized JSON payload"
        );
        return PKTLAB_JSON_PROTO_STATUS_ERROR;
    }

    net_length = htonl((uint32_t) json_len);

    status = pktlab_json_proto_write_exact(fd, &net_length, sizeof(net_length));
    if (status != PKTLAB_JSON_PROTO_STATUS_OK) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "failed to write frame length"
        );
        return PKTLAB_JSON_PROTO_STATUS_ERROR;
    }

    status = pktlab_json_proto_write_exact(fd, json, json_len);
    if (status != PKTLAB_JSON_PROTO_STATUS_OK) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "failed to write frame payload"
        );
        return PKTLAB_JSON_PROTO_STATUS_ERROR;
    }

    return PKTLAB_JSON_PROTO_STATUS_OK;
}

static size_t pktlab_json_proto_skip_ws(const char *json, size_t json_len, size_t pos)
{
    while (pos < json_len) {
        if (json[pos] != ' ' && json[pos] != '\n' && json[pos] != '\r' && json[pos] != '\t') {
            break;
        }
        pos++;
    }

    return pos;
}

static int pktlab_json_proto_parse_string(
    const char *json,
    size_t json_len,
    size_t *pos,
    char *buffer,
    size_t buffer_cap,
    struct pktlab_dpdkd_error *error
)
{
    size_t out_len;
    bool needs_output;

    *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
    if (*pos >= json_len || json[*pos] != '"') {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "expected a JSON string"
        );
        return -1;
    }

    (*pos)++;
    out_len = 0U;
    needs_output = (buffer != NULL && buffer_cap > 0U);

    while (*pos < json_len) {
        char ch;

        ch = json[*pos];
        if (ch == '"') {
            if (needs_output) {
                buffer[out_len] = '\0';
            }
            (*pos)++;
            return 0;
        }

        if (ch == '\\') {
            char escaped;

            (*pos)++;
            if (*pos >= json_len) {
                pktlab_json_proto_set_error(
                    error,
                    PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                    "unterminated JSON escape sequence"
                );
                return -1;
            }

            switch (json[*pos]) {
            case '"':
                escaped = '"';
                break;
            case '\\':
                escaped = '\\';
                break;
            case '/':
                escaped = '/';
                break;
            case 'b':
                escaped = '\b';
                break;
            case 'f':
                escaped = '\f';
                break;
            case 'n':
                escaped = '\n';
                break;
            case 'r':
                escaped = '\r';
                break;
            case 't':
                escaped = '\t';
                break;
            default:
                pktlab_json_proto_set_error(
                    error,
                    PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                    "unsupported JSON escape sequence"
                );
                return -1;
            }
            ch = escaped;
        }

        if (needs_output) {
            if (out_len + 1U >= buffer_cap) {
                pktlab_json_proto_set_error(
                    error,
                    PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                    "JSON string exceeds the allowed size"
                );
                return -1;
            }
            buffer[out_len++] = ch;
        }

        (*pos)++;
    }

    pktlab_json_proto_set_error(
        error,
        PKTLAB_DPDKD_ERR_INVALID_REQUEST,
        "unterminated JSON string"
    );
    return -1;
}

static int pktlab_json_proto_skip_value(
    const char *json,
    size_t json_len,
    size_t *pos,
    unsigned int depth,
    struct pktlab_dpdkd_error *error
);

static int pktlab_json_proto_skip_object(
    const char *json,
    size_t json_len,
    size_t *pos,
    unsigned int depth,
    struct pktlab_dpdkd_error *error
)
{
    bool expect_member;

    if (depth > PKTLAB_JSON_PROTO_MAX_NESTING) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "JSON nesting exceeds the supported limit"
        );
        return -1;
    }

    *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
    if (*pos >= json_len || json[*pos] != '{') {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "expected a JSON object"
        );
        return -1;
    }

    (*pos)++;
    expect_member = true;

    while (*pos < json_len) {
        *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
        if (*pos < json_len && json[*pos] == '}') {
            (*pos)++;
            return 0;
        }

        if (!expect_member) {
            pktlab_json_proto_set_error(
                error,
                PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                "expected object member separator"
            );
            return -1;
        }

        if (pktlab_json_proto_parse_string(json, json_len, pos, NULL, 0U, error) != 0) {
            return -1;
        }

        *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
        if (*pos >= json_len || json[*pos] != ':') {
            pktlab_json_proto_set_error(
                error,
                PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                "expected ':' after object key"
            );
            return -1;
        }

        (*pos)++;
        if (pktlab_json_proto_skip_value(json, json_len, pos, depth + 1U, error) != 0) {
            return -1;
        }

        *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
        if (*pos < json_len && json[*pos] == ',') {
            (*pos)++;
            expect_member = true;
            continue;
        }
        if (*pos < json_len && json[*pos] == '}') {
            (*pos)++;
            return 0;
        }

        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "expected ',' or '}' in object"
        );
        return -1;
    }

    pktlab_json_proto_set_error(
        error,
        PKTLAB_DPDKD_ERR_INVALID_REQUEST,
        "unterminated JSON object"
    );
    return -1;
}

static int pktlab_json_proto_skip_array(
    const char *json,
    size_t json_len,
    size_t *pos,
    unsigned int depth,
    struct pktlab_dpdkd_error *error
)
{
    if (depth > PKTLAB_JSON_PROTO_MAX_NESTING) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "JSON nesting exceeds the supported limit"
        );
        return -1;
    }

    *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
    if (*pos >= json_len || json[*pos] != '[') {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "expected a JSON array"
        );
        return -1;
    }

    (*pos)++;

    while (*pos < json_len) {
        *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
        if (*pos < json_len && json[*pos] == ']') {
            (*pos)++;
            return 0;
        }

        if (pktlab_json_proto_skip_value(json, json_len, pos, depth + 1U, error) != 0) {
            return -1;
        }

        *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
        if (*pos < json_len && json[*pos] == ',') {
            (*pos)++;
            continue;
        }
        if (*pos < json_len && json[*pos] == ']') {
            (*pos)++;
            return 0;
        }

        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "expected ',' or ']' in array"
        );
        return -1;
    }

    pktlab_json_proto_set_error(
        error,
        PKTLAB_DPDKD_ERR_INVALID_REQUEST,
        "unterminated JSON array"
    );
    return -1;
}

static int pktlab_json_proto_skip_literal(
    const char *json,
    size_t json_len,
    size_t *pos,
    const char *literal,
    struct pktlab_dpdkd_error *error
)
{
    size_t literal_len;

    literal_len = strlen(literal);
    if (*pos + literal_len > json_len || strncmp(json + *pos, literal, literal_len) != 0) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "invalid JSON literal"
        );
        return -1;
    }

    *pos += literal_len;
    return 0;
}

static int pktlab_json_proto_skip_number(
    const char *json,
    size_t json_len,
    size_t *pos,
    struct pktlab_dpdkd_error *error
)
{
    size_t start;

    start = *pos;
    if (json[*pos] == '-') {
        (*pos)++;
    }

    while (*pos < json_len && json[*pos] >= '0' && json[*pos] <= '9') {
        (*pos)++;
    }

    if (*pos == start || (*pos == start + 1U && json[start] == '-')) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "invalid JSON number"
        );
        return -1;
    }

    if (*pos < json_len && json[*pos] == '.') {
        (*pos)++;
        while (*pos < json_len && json[*pos] >= '0' && json[*pos] <= '9') {
            (*pos)++;
        }
    }

    if (*pos < json_len && (json[*pos] == 'e' || json[*pos] == 'E')) {
        (*pos)++;
        if (*pos < json_len && (json[*pos] == '+' || json[*pos] == '-')) {
            (*pos)++;
        }
        while (*pos < json_len && json[*pos] >= '0' && json[*pos] <= '9') {
            (*pos)++;
        }
    }

    return 0;
}

static int pktlab_json_proto_skip_value(
    const char *json,
    size_t json_len,
    size_t *pos,
    unsigned int depth,
    struct pktlab_dpdkd_error *error
)
{
    *pos = pktlab_json_proto_skip_ws(json, json_len, *pos);
    if (*pos >= json_len) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "unexpected end of JSON input"
        );
        return -1;
    }

    switch (json[*pos]) {
    case '{':
        return pktlab_json_proto_skip_object(json, json_len, pos, depth, error);
    case '[':
        return pktlab_json_proto_skip_array(json, json_len, pos, depth, error);
    case '"':
        return pktlab_json_proto_parse_string(json, json_len, pos, NULL, 0U, error);
    case 't':
        return pktlab_json_proto_skip_literal(json, json_len, pos, "true", error);
    case 'f':
        return pktlab_json_proto_skip_literal(json, json_len, pos, "false", error);
    case 'n':
        return pktlab_json_proto_skip_literal(json, json_len, pos, "null", error);
    default:
        if (json[*pos] == '-' || (json[*pos] >= '0' && json[*pos] <= '9')) {
            return pktlab_json_proto_skip_number(json, json_len, pos, error);
        }
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "unexpected JSON token"
        );
        return -1;
    }
}

int pktlab_json_proto_parse_request(
    const char *json,
    size_t json_len,
    struct pktlab_ipc_request *request,
    struct pktlab_dpdkd_error *error
)
{
    size_t pos;
    bool have_id;
    bool have_cmd;
    bool have_payload;

    memset(request, 0, sizeof(*request));
    pos = 0U;
    have_id = false;
    have_cmd = false;
    have_payload = false;

    pos = pktlab_json_proto_skip_ws(json, json_len, pos);
    if (pos >= json_len || json[pos] != '{') {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "request must be a JSON object"
        );
        return -1;
    }
    pos++;

    while (pos < json_len) {
        char key[32];

        pos = pktlab_json_proto_skip_ws(json, json_len, pos);
        if (pos < json_len && json[pos] == '}') {
            pos++;
            break;
        }

        if (pktlab_json_proto_parse_string(
                json, json_len, &pos, key, sizeof(key), error) != 0) {
            return -1;
        }

        pos = pktlab_json_proto_skip_ws(json, json_len, pos);
        if (pos >= json_len || json[pos] != ':') {
            pktlab_json_proto_set_error(
                error,
                PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                "expected ':' after request key"
            );
            return -1;
        }
        pos++;

        if (strcmp(key, "id") == 0) {
            if (have_id) {
                pktlab_json_proto_set_error(
                    error,
                    PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                    "duplicate request id field"
                );
                return -1;
            }
            if (pktlab_json_proto_parse_string(
                    json, json_len, &pos, request->id, sizeof(request->id), error) != 0) {
                return -1;
            }
            have_id = true;
        } else if (strcmp(key, "cmd") == 0) {
            if (have_cmd) {
                pktlab_json_proto_set_error(
                    error,
                    PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                    "duplicate request command field"
                );
                return -1;
            }
            if (pktlab_json_proto_parse_string(
                    json, json_len, &pos, request->cmd, sizeof(request->cmd), error) != 0) {
                return -1;
            }
            have_cmd = true;
        } else if (strcmp(key, "payload") == 0) {
            size_t payload_pos;
            size_t payload_value_pos;

            if (have_payload) {
                pktlab_json_proto_set_error(
                    error,
                    PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                    "duplicate request payload field"
                );
                return -1;
            }

            payload_pos = pktlab_json_proto_skip_ws(json, json_len, pos);
            payload_value_pos = payload_pos;
            if (pktlab_json_proto_skip_value(json, json_len, &payload_value_pos, 1U, error) != 0) {
                return -1;
            }
            if (payload_pos >= json_len || json[payload_pos] != '{') {
                pktlab_json_proto_set_error(
                    error,
                    PKTLAB_DPDKD_ERR_INVALID_PAYLOAD,
                    "request payload must be a JSON object"
                );
                return -1;
            }
            pos = payload_value_pos;
            have_payload = true;
        } else {
            pktlab_json_proto_set_error(
                error,
                PKTLAB_DPDKD_ERR_INVALID_REQUEST,
                "unexpected top-level request field"
            );
            return -1;
        }

        pos = pktlab_json_proto_skip_ws(json, json_len, pos);
        if (pos < json_len && json[pos] == ',') {
            pos++;
            continue;
        }
        if (pos < json_len && json[pos] == '}') {
            pos++;
            break;
        }

        if (pos >= json_len) {
            break;
        }

        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "expected ',' or '}' in request object"
        );
        return -1;
    }

    pos = pktlab_json_proto_skip_ws(json, json_len, pos);
    if (pos != json_len) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "request contains trailing data"
        );
        return -1;
    }

    if (!have_id || !have_cmd || !have_payload) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INVALID_REQUEST,
            "request must include id, cmd, and payload"
        );
        return -1;
    }

    return 0;
}

static int pktlab_json_proto_escape_string(
    const char *input,
    char *buffer,
    size_t buffer_cap,
    size_t *output_len
)
{
    size_t in_pos;
    size_t out_pos;

    in_pos = 0U;
    out_pos = 0U;

    while (input[in_pos] != '\0') {
        const char *replacement;
        size_t replacement_len;
        char ch;

        replacement = NULL;
        replacement_len = 0U;
        ch = input[in_pos];

        switch (ch) {
        case '\\':
            replacement = "\\\\";
            replacement_len = 2U;
            break;
        case '"':
            replacement = "\\\"";
            replacement_len = 2U;
            break;
        case '\n':
            replacement = "\\n";
            replacement_len = 2U;
            break;
        case '\r':
            replacement = "\\r";
            replacement_len = 2U;
            break;
        case '\t':
            replacement = "\\t";
            replacement_len = 2U;
            break;
        default:
            break;
        }

        if (replacement != NULL) {
            if (out_pos + replacement_len + 1U > buffer_cap) {
                return -1;
            }
            memcpy(buffer + out_pos, replacement, replacement_len);
            out_pos += replacement_len;
        } else {
            if (out_pos + 2U > buffer_cap) {
                return -1;
            }
            buffer[out_pos++] = ch;
        }

        in_pos++;
    }

    if (buffer_cap == 0U) {
        return -1;
    }

    buffer[out_pos] = '\0';
    *output_len = out_pos;
    return 0;
}

static int pktlab_json_proto_snprintf(
    char *buffer,
    size_t buffer_cap,
    size_t *json_len,
    struct pktlab_dpdkd_error *error,
    const char *format,
    ...
)
{
    int written;
    va_list args;

    va_start(args, format);
    written = vsnprintf(buffer, buffer_cap, format, args);
    va_end(args);

    if (written < 0 || (size_t) written >= buffer_cap) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "JSON output buffer is too small"
        );
        return -1;
    }

    *json_len = (size_t) written;
    return 0;
}

int pktlab_json_proto_make_pong_payload(char *buffer, size_t buffer_cap, size_t *json_len)
{
    struct pktlab_dpdkd_error error;

    return pktlab_json_proto_snprintf(
        buffer,
        buffer_cap,
        json_len,
        &error,
        "{\"message\":\"pong\"}"
    );
}

int pktlab_json_proto_make_version_payload(char *buffer, size_t buffer_cap, size_t *json_len)
{
    struct pktlab_dpdkd_error error;

    return pktlab_json_proto_snprintf(
        buffer,
        buffer_cap,
        json_len,
        &error,
        "{\"service\":\"%s\",\"version\":\"%s\",\"dpdk_version\":\"%s\"}",
        PKTLAB_DPDKD_SERVICE_NAME,
        PKTLAB_DPDKD_VERSION,
        PKTLAB_DPDKD_DPDK_VERSION
    );
}

int pktlab_json_proto_make_health_payload(
    const struct pktlab_health_snapshot *health,
    char *buffer,
    size_t buffer_cap,
    size_t *json_len
)
{
    char escaped_message[PKTLAB_DPDKD_MESSAGE_LEN * 2U];
    size_t ignored_len;
    struct pktlab_dpdkd_error error;

    if (pktlab_json_proto_escape_string(
            health->message, escaped_message, sizeof(escaped_message), &ignored_len) != 0) {
        pktlab_json_proto_set_error(
            &error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "health message could not be escaped"
        );
        return -1;
    }

    return pktlab_json_proto_snprintf(
        buffer,
        buffer_cap,
        json_len,
        &error,
        "{\"health\":{\"state\":\"%s\",\"message\":\"%s\",\"applied_rule_version\":%u,"
        "\"ports_ready\":%s,\"paused\":%s}}",
        pktlab_dp_state_name(health->state),
        escaped_message,
        health->applied_rule_version,
        health->ports_ready ? "true" : "false",
        health->paused ? "true" : "false"
    );
}

int pktlab_json_proto_make_success(
    const char *request_id,
    const char *payload_json,
    char *buffer,
    size_t buffer_cap,
    size_t *json_len,
    struct pktlab_dpdkd_error *error
)
{
    char escaped_id[(PKTLAB_JSON_PROTO_MAX_ID_LEN * 2U) + 1U];
    size_t ignored_len;

    if (pktlab_json_proto_escape_string(request_id, escaped_id, sizeof(escaped_id), &ignored_len) != 0) {
        pktlab_json_proto_set_error(
            error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "request id could not be escaped"
        );
        return -1;
    }

    return pktlab_json_proto_snprintf(
        buffer,
        buffer_cap,
        json_len,
        error,
        "{\"id\":\"%s\",\"ok\":true,\"payload\":%s}",
        escaped_id,
        payload_json
    );
}

int pktlab_json_proto_make_error(
    const char *request_id,
    const struct pktlab_dpdkd_error *error,
    char *buffer,
    size_t buffer_cap,
    size_t *json_len
)
{
    char escaped_id[(PKTLAB_JSON_PROTO_MAX_ID_LEN * 2U) + 1U];
    char escaped_message[256];
    size_t ignored_len;
    struct pktlab_dpdkd_error internal_error;
    const char *safe_id;
    const char *safe_message;

    safe_id = request_id;
    if (safe_id == NULL || safe_id[0] == '\0') {
        safe_id = PKTLAB_JSON_PROTO_UNKNOWN_ID;
    }

    safe_message = error->message;
    if (safe_message == NULL || safe_message[0] == '\0') {
        safe_message = "internal error";
    }

    if (pktlab_json_proto_escape_string(safe_id, escaped_id, sizeof(escaped_id), &ignored_len) != 0 ||
        pktlab_json_proto_escape_string(
            safe_message, escaped_message, sizeof(escaped_message), &ignored_len) != 0) {
        pktlab_json_proto_set_error(
            &internal_error,
            PKTLAB_DPDKD_ERR_INTERNAL,
            "error response could not be escaped"
        );
        return pktlab_json_proto_snprintf(
            buffer,
            buffer_cap,
            json_len,
            &internal_error,
            "{\"id\":\"%s\",\"ok\":false,\"error\":{\"code\":\"INTERNAL_ERROR\","
            "\"message\":\"internal error\"}}",
            PKTLAB_JSON_PROTO_UNKNOWN_ID
        );
    }

    return pktlab_json_proto_snprintf(
        buffer,
        buffer_cap,
        json_len,
        &internal_error,
        "{\"id\":\"%s\",\"ok\":false,\"error\":{\"code\":\"%s\",\"message\":\"%s\"}}",
        escaped_id,
        pktlab_dpdkd_error_code_name(error->code),
        escaped_message
    );
}
