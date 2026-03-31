#ifndef PKTLAB_DPDKD_ERRORS_H
#define PKTLAB_DPDKD_ERRORS_H

enum pktlab_dpdkd_error_code {
    PKTLAB_DPDKD_ERR_NONE = 0,
    PKTLAB_DPDKD_ERR_INVALID_REQUEST,
    PKTLAB_DPDKD_ERR_INVALID_PAYLOAD,
    PKTLAB_DPDKD_ERR_UNKNOWN_COMMAND,
    PKTLAB_DPDKD_ERR_RULE_VALIDATION,
    PKTLAB_DPDKD_ERR_PORT_INIT,
    PKTLAB_DPDKD_ERR_STATE_CONFLICT,
    PKTLAB_DPDKD_ERR_INTERNAL
};

struct pktlab_dpdkd_error {
    enum pktlab_dpdkd_error_code code;
    const char *message;
};

const char *pktlab_dpdkd_error_code_name(enum pktlab_dpdkd_error_code code);

#endif /* PKTLAB_DPDKD_ERRORS_H */
