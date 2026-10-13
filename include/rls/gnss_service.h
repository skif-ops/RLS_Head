#ifndef RLS_GNSS_SERVICE_H
#define RLS_GNSS_SERVICE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    RLS_GNSS_UART_STALE   = 1u << 0,
    RLS_GNSS_PPS_STALE    = 1u << 1,
    RLS_GNSS_FIX_INVALID  = 1u << 2,
    RLS_GNSS_TIME_INVALID = 1u << 3,
    RLS_GNSS_JAMMING      = 1u << 4,
    RLS_GNSS_SPOOFING     = 1u << 5,
};

typedef struct {
    uint64_t last_uart_rx_us;
    uint64_t last_pps_us;
    bool uart_seen;
    bool pps_seen;
    bool fix_valid;
    bool time_valid;
    bool jamming_detected;
    bool spoofing_detected;
} rls_gnss_service_t;

typedef struct {
    uint64_t uart_timeout_us;
    uint64_t pps_timeout_us;
} rls_gnss_limits_t;

typedef struct {
    uint32_t flags;
    uint64_t uart_age_us;
    uint64_t pps_age_us;
    bool healthy;
} rls_gnss_report_t;

void rls_gnss_service_init(
    rls_gnss_service_t *service
);

void rls_gnss_service_note_uart(
    rls_gnss_service_t *service,
    uint64_t timestamp_us
);

void rls_gnss_service_note_pps(
    rls_gnss_service_t *service,
    uint64_t timestamp_us
);

void rls_gnss_service_update_quality(
    rls_gnss_service_t *service,
    bool fix_valid,
    bool time_valid,
    bool jamming_detected,
    bool spoofing_detected
);

int rls_gnss_service_evaluate(
    const rls_gnss_service_t *service,
    const rls_gnss_limits_t *limits,
    uint64_t now_us,
    rls_gnss_report_t *report
);

#ifdef __cplusplus
}
#endif

#endif
