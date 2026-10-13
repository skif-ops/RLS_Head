#include "rls/gnss_service.h"

#include <stdint.h>
#include <stdlib.h>

#define CHECK(expr) do { if (!(expr)) abort(); } while (0)

static void test_nominal_quality(void)
{
    rls_gnss_service_t service;
    rls_gnss_report_t report;
    const rls_gnss_limits_t limits = {
        .uart_timeout_us = 2000000u,
        .pps_timeout_us = 1500000u,
    };

    rls_gnss_service_init(&service);
    rls_gnss_service_note_uart(
        &service,
        1000000u
    );
    rls_gnss_service_note_pps(
        &service,
        1000000u
    );
    rls_gnss_service_update_quality(
        &service,
        true,
        true,
        false,
        false
    );

    CHECK(
        rls_gnss_service_evaluate(
            &service,
            &limits,
            1500000u,
            &report
        ) == 0
    );
    CHECK(report.healthy);
    CHECK(report.flags == 0u);
}

static void test_stale_and_integrity_flags(void)
{
    rls_gnss_service_t service;
    rls_gnss_report_t report;
    const rls_gnss_limits_t limits = {
        .uart_timeout_us = 100u,
        .pps_timeout_us = 100u,
    };

    rls_gnss_service_init(&service);
    rls_gnss_service_note_uart(
        &service,
        10u
    );
    rls_gnss_service_note_pps(
        &service,
        10u
    );
    rls_gnss_service_update_quality(
        &service,
        false,
        false,
        true,
        true
    );

    CHECK(
        rls_gnss_service_evaluate(
            &service,
            &limits,
            200u,
            &report
        ) == 0
    );

    CHECK(!report.healthy);
    CHECK(
        (report.flags & RLS_GNSS_UART_STALE)
        != 0u
    );
    CHECK(
        (report.flags & RLS_GNSS_PPS_STALE)
        != 0u
    );
    CHECK(
        (report.flags & RLS_GNSS_FIX_INVALID)
        != 0u
    );
    CHECK(
        (report.flags & RLS_GNSS_TIME_INVALID)
        != 0u
    );
    CHECK(
        (report.flags & RLS_GNSS_JAMMING)
        != 0u
    );
    CHECK(
        (report.flags & RLS_GNSS_SPOOFING)
        != 0u
    );
}

int main(void)
{
    test_nominal_quality();
    test_stale_and_integrity_flags();
    return 0;
}
