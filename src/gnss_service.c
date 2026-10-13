#include "rls/gnss_service.h"

#include <stddef.h>
#include <string.h>

static uint64_t age_us(
    uint64_t now_us,
    uint64_t timestamp_us
)
{
    if (now_us < timestamp_us) {
        return UINT64_MAX;
    }
    return now_us - timestamp_us;
}

void rls_gnss_service_init(
    rls_gnss_service_t *service
)
{
    if (service == NULL) {
        return;
    }
    memset(service, 0, sizeof(*service));
}

void rls_gnss_service_note_uart(
    rls_gnss_service_t *service,
    uint64_t timestamp_us
)
{
    if (service == NULL) {
        return;
    }
    service->last_uart_rx_us = timestamp_us;
    service->uart_seen = true;
}

void rls_gnss_service_note_pps(
    rls_gnss_service_t *service,
    uint64_t timestamp_us
)
{
    if (service == NULL) {
        return;
    }
    service->last_pps_us = timestamp_us;
    service->pps_seen = true;
}

void rls_gnss_service_update_quality(
    rls_gnss_service_t *service,
    bool fix_valid,
    bool time_valid,
    bool jamming_detected,
    bool spoofing_detected
)
{
    if (service == NULL) {
        return;
    }

    service->fix_valid = fix_valid;
    service->time_valid = time_valid;
    service->jamming_detected = jamming_detected;
    service->spoofing_detected = spoofing_detected;
}

int rls_gnss_service_evaluate(
    const rls_gnss_service_t *service,
    const rls_gnss_limits_t *limits,
    uint64_t now_us,
    rls_gnss_report_t *report
)
{
    if (
        service == NULL
        || limits == NULL
        || report == NULL
    ) {
        return -1;
    }

    report->uart_age_us =
        service->uart_seen
            ? age_us(
                now_us,
                service->last_uart_rx_us
            )
            : UINT64_MAX;

    report->pps_age_us =
        service->pps_seen
            ? age_us(
                now_us,
                service->last_pps_us
            )
            : UINT64_MAX;

    uint32_t flags = 0u;

    if (
        !service->uart_seen
        || report->uart_age_us
            > limits->uart_timeout_us
    ) {
        flags |= RLS_GNSS_UART_STALE;
    }

    if (
        !service->pps_seen
        || report->pps_age_us
            > limits->pps_timeout_us
    ) {
        flags |= RLS_GNSS_PPS_STALE;
    }

    if (!service->fix_valid) {
        flags |= RLS_GNSS_FIX_INVALID;
    }

    if (!service->time_valid) {
        flags |= RLS_GNSS_TIME_INVALID;
    }

    if (service->jamming_detected) {
        flags |= RLS_GNSS_JAMMING;
    }

    if (service->spoofing_detected) {
        flags |= RLS_GNSS_SPOOFING;
    }

    report->flags = flags;
    report->healthy = (flags == 0u);

    return 0;
}
