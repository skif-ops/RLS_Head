#include "rls/imu_service.h"

#include <stddef.h>
#include <string.h>

static uint64_t age_us(
    uint64_t now_us,
    uint64_t then_us
)
{
    if (now_us < then_us) {
        return UINT64_MAX;
    }
    return now_us - then_us;
}

void rls_imu_service_init(
    rls_imu_service_t *service
)
{
    if (service == NULL) {
        return;
    }

    memset(service, 0, sizeof(*service));
    service->state = RLS_IMU_IDLE;
}

bool rls_imu_service_note_drdy(
    rls_imu_service_t *service,
    uint64_t timestamp_us,
    uint32_t *sequence_out
)
{
    if (service == NULL) {
        return false;
    }

    if (service->state != RLS_IMU_IDLE) {
        service->overrun_count++;
        return false;
    }

    service->drdy_timestamp_us =
        timestamp_us;

    if (sequence_out != NULL) {
        *sequence_out =
            service->next_sequence;
    }

    service->next_sequence++;
    service->state =
        RLS_IMU_PENDING;

    return true;
}

bool rls_imu_service_begin_transfer(
    rls_imu_service_t *service
)
{
    if (
        service == NULL
        || service->state
            != RLS_IMU_PENDING
    ) {
        return false;
    }

    service->state =
        RLS_IMU_TRANSFER_ACTIVE;

    return true;
}

bool rls_imu_service_complete_transfer(
    rls_imu_service_t *service,
    bool success
)
{
    if (
        service == NULL
        || service->state
            != RLS_IMU_TRANSFER_ACTIVE
    ) {
        return false;
    }

    if (success) {
        service->last_sample_timestamp_us =
            service->drdy_timestamp_us;
        service->completed_samples++;
        service->sample_seen = true;
    } else {
        service->transfer_error_count++;
    }

    service->state =
        RLS_IMU_IDLE;

    return true;
}

int rls_imu_service_evaluate(
    const rls_imu_service_t *service,
    const rls_imu_limits_t *limits,
    uint64_t now_us,
    rls_imu_report_t *report
)
{
    if (
        service == NULL
        || limits == NULL
        || report == NULL
    ) {
        return -1;
    }

    report->sample_age_us =
        service->sample_seen
            ? age_us(
                now_us,
                service->last_sample_timestamp_us
            )
            : UINT64_MAX;

    report->completed_samples =
        service->completed_samples;
    report->overrun_count =
        service->overrun_count;
    report->transfer_error_count =
        service->transfer_error_count;
    report->fresh =
        service->sample_seen
        && report->sample_age_us
            <= limits->sample_timeout_us;
    report->transfer_busy =
        service->state
        != RLS_IMU_IDLE;

    return 0;
}
