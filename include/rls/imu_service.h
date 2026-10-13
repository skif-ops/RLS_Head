#ifndef RLS_IMU_SERVICE_H
#define RLS_IMU_SERVICE_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    RLS_IMU_IDLE = 0,
    RLS_IMU_PENDING,
    RLS_IMU_TRANSFER_ACTIVE
} rls_imu_state_t;

typedef struct {
    uint64_t drdy_timestamp_us;
    uint64_t last_sample_timestamp_us;
    uint32_t next_sequence;
    uint32_t completed_samples;
    uint32_t overrun_count;
    uint32_t transfer_error_count;
    rls_imu_state_t state;
    bool sample_seen;
} rls_imu_service_t;

typedef struct {
    uint64_t sample_timeout_us;
} rls_imu_limits_t;

typedef struct {
    uint64_t sample_age_us;
    uint32_t completed_samples;
    uint32_t overrun_count;
    uint32_t transfer_error_count;
    bool fresh;
    bool transfer_busy;
} rls_imu_report_t;

void rls_imu_service_init(
    rls_imu_service_t *service
);

bool rls_imu_service_note_drdy(
    rls_imu_service_t *service,
    uint64_t timestamp_us,
    uint32_t *sequence_out
);

bool rls_imu_service_begin_transfer(
    rls_imu_service_t *service
);

bool rls_imu_service_complete_transfer(
    rls_imu_service_t *service,
    bool success
);

int rls_imu_service_evaluate(
    const rls_imu_service_t *service,
    const rls_imu_limits_t *limits,
    uint64_t now_us,
    rls_imu_report_t *report
);

#ifdef __cplusplus
}
#endif

#endif
