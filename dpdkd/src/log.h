#ifndef PKTLAB_DPDKD_LOG_H
#define PKTLAB_DPDKD_LOG_H

#include <stdarg.h>

enum pktlab_log_level {
    PKTLAB_LOG_LEVEL_ERROR = 0,
    PKTLAB_LOG_LEVEL_WARN = 1,
    PKTLAB_LOG_LEVEL_INFO = 2,
    PKTLAB_LOG_LEVEL_DEBUG = 3
};

void pktlab_log_init(enum pktlab_log_level level);
void pktlab_log_message(
    enum pktlab_log_level level,
    const char *file,
    int line,
    const char *fmt,
    ...
);

#define PKTLAB_LOG_ERROR(...) \
    pktlab_log_message(PKTLAB_LOG_LEVEL_ERROR, __FILE__, __LINE__, __VA_ARGS__)
#define PKTLAB_LOG_WARN(...) \
    pktlab_log_message(PKTLAB_LOG_LEVEL_WARN, __FILE__, __LINE__, __VA_ARGS__)
#define PKTLAB_LOG_INFO(...) \
    pktlab_log_message(PKTLAB_LOG_LEVEL_INFO, __FILE__, __LINE__, __VA_ARGS__)
#define PKTLAB_LOG_DEBUG(...) \
    pktlab_log_message(PKTLAB_LOG_LEVEL_DEBUG, __FILE__, __LINE__, __VA_ARGS__)

#endif /* PKTLAB_DPDKD_LOG_H */
