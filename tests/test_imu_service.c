#include "rls/imu_service.h"

#include <stdint.h>
#include <stdlib.h>

#define CHECK(expr) do { if (!(expr)) abort(); } while (0)

static void test_nominal_sample_flow(void)
{
    rls_imu_service_t service;
    rls_imu_report_t report;
    uint32_t sequence = UINT32_MAX;

    const rls_imu_limits_t limits = {
        .sample_timeout_us = 20000u,
    };

    rls_imu_service_init(&service);

    CHECK(
        rls_imu_service_note_drdy(
            &service,
            1000u,
            &sequence
        )
    );
    CHECK(sequence == 0u);
    CHECK(service.state == RLS_IMU_PENDING);

    CHECK(
        rls_imu_service_begin_transfer(
            &service
        )
    );
    CHECK(
        rls_imu_service_complete_transfer(
            &service,
            true
        )
    );

    CHECK(
        rls_imu_service_evaluate(
            &service,
            &limits,
            1500u,
            &report
        ) == 0
    );

    CHECK(report.fresh);
    CHECK(report.completed_samples == 1u);
    CHECK(report.overrun_count == 0u);
    CHECK(report.transfer_error_count == 0u);
    CHECK(!report.transfer_busy);
}

static void test_overrun_and_transfer_error(void)
{
    rls_imu_service_t service;
    uint32_t sequence = 0u;

    rls_imu_service_init(&service);

    CHECK(
        rls_imu_service_note_drdy(
            &service,
            100u,
            &sequence
        )
    );

    CHECK(
        !rls_imu_service_note_drdy(
            &service,
            110u,
            NULL
        )
    );
    CHECK(service.overrun_count == 1u);

    CHECK(
        rls_imu_service_begin_transfer(
            &service
        )
    );
    CHECK(
        rls_imu_service_complete_transfer(
            &service,
            false
        )
    );
    CHECK(
        service.transfer_error_count
        == 1u
    );
}

static void test_stale_report(void)
{
    rls_imu_service_t service;
    rls_imu_report_t report;
    const rls_imu_limits_t limits = {
        .sample_timeout_us = 10u,
    };

    rls_imu_service_init(&service);

    CHECK(
        rls_imu_service_note_drdy(
            &service,
            10u,
            NULL
        )
    );
    CHECK(
        rls_imu_service_begin_transfer(
            &service
        )
    );
    CHECK(
        rls_imu_service_complete_transfer(
            &service,
            true
        )
    );

    CHECK(
        rls_imu_service_evaluate(
            &service,
            &limits,
            100u,
            &report
        ) == 0
    );
    CHECK(!report.fresh);
}

int main(void)
{
    test_nominal_sample_flow();
    test_overrun_and_transfer_error();
    test_stale_report();
    return 0;
}
