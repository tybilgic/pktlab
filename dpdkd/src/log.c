#include "log.h"

#include <stdio.h>
#include <time.h>

static enum pktlab_log_level g_log_level = PKTLAB_LOG_LEVEL_INFO;

static const char *pktlab_log_level_name(enum pktlab_log_level level)
{
    switch (level) {
    case PKTLAB_LOG_LEVEL_ERROR:
        return "ERROR";
    case PKTLAB_LOG_LEVEL_WARN:
        return "WARN";
    case PKTLAB_LOG_LEVEL_INFO:
        return "INFO";
    case PKTLAB_LOG_LEVEL_DEBUG:
        return "DEBUG";
    default:
        return "UNKNOWN";
    }
}

void pktlab_log_init(enum pktlab_log_level level)
{
    g_log_level = level;
}

void pktlab_log_message(
    enum pktlab_log_level level,
    const char *file,
    int line,
    const char *fmt,
    ...
)
{
    time_t now;
    struct tm tm_now;
    char timestamp[32];
    va_list args;

    if (level > g_log_level) {
        return;
    }

    now = time(NULL);
    localtime_r(&now, &tm_now);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", &tm_now);

    fprintf(stderr, "%s [%s] %s:%d ", timestamp, pktlab_log_level_name(level), file, line);

    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);

    fputc('\n', stderr);
}
