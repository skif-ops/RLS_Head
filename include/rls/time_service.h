#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    TIME_SERVICE_UNINITIALIZED = 0,
    TIME_SERVICE_PHASE_ONLY,
    TIME_SERVICE_LOCKED,
    TIME_SERVICE_HOLDOVER
} TimeServiceState;

typedef enum {
    TIME_OBSERVE_ACCEPTED_PHASE = 0,
    TIME_OBSERVE_ACCEPTED_LOCK,
    TIME_OBSERVE_REJECTED_ARGUMENT,
    TIME_OBSERVE_REJECTED_NONMONOTONIC,
    TIME_OBSERVE_REJECTED_RATE
} TimeObserveResult;

typedef struct {
    uint64_t reference_local_us;
    int64_t offset_us;

    int32_t rate_correction_ppb;

    uint64_t last_pps_local_us;
    int64_t last_observed_offset_us;

    float phase_sigma_us;
    float drift_sigma_ppm;
    float max_abs_rate_ppm;

    TimeServiceState state;
    bool have_reference;
} TimeService;

bool time_service_init(
    TimeService *service,
    float phase_sigma_us,
    float drift_sigma_ppm,
    float max_abs_rate_ppm);

TimeObserveResult time_service_observe_pps(
    TimeService *service,
    uint64_t local_capture_us,
    int64_t reference_time_us);

bool time_service_map_us(
    const TimeService *service,
    uint64_t local_time_us,
    int64_t *disciplined_time_us);

float time_service_uncertainty_us(
    const TimeService *service,
    uint64_t local_time_us);

bool time_service_mark_holdover(
    TimeService *service);

const char *time_service_state_name(
    TimeServiceState state);

#ifdef __cplusplus
}
#endif
