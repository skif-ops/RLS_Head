#include "rls/time_service.h"

#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define US_PER_SECOND 1000000LL
#define PPB_PER_ONE   1000000000LL
#define PPB_PER_PPM   1000LL

static bool finite_nonnegative(float value)
{
    return isfinite(value) && value >= 0.0f;
}

static bool correction_us(
    int64_t delta_local_us,
    int32_t rate_correction_ppb,
    int64_t *out)
{
    if (out == NULL) {
        return false;
    }

    /*
     * Split the product to avoid multiplying a long-running microsecond
     * counter directly by ppb. The reference is re-based on every accepted
     * PPS, so typical deltas are small; this remains safe through holdover.
     */
    const int64_t whole_seconds =
        delta_local_us / US_PER_SECOND;

    const int64_t remainder_us =
        delta_local_us % US_PER_SECOND;

    const int64_t whole_correction =
        (whole_seconds * (int64_t)rate_correction_ppb) /
        PPB_PER_PPM;

    const int64_t remainder_correction =
        (remainder_us * (int64_t)rate_correction_ppb) /
        PPB_PER_ONE;

    *out =
        whole_correction +
        remainder_correction;

    return true;
}

bool time_service_init(
    TimeService *service,
    float phase_sigma_us,
    float drift_sigma_ppm,
    float max_abs_rate_ppm)
{
    if (service == NULL ||
        !finite_nonnegative(phase_sigma_us) ||
        !finite_nonnegative(drift_sigma_ppm) ||
        !isfinite(max_abs_rate_ppm) ||
        max_abs_rate_ppm <= 0.0f) {
        return false;
    }

    memset(service, 0, sizeof(*service));

    service->phase_sigma_us =
        phase_sigma_us;

    service->drift_sigma_ppm =
        drift_sigma_ppm;

    service->max_abs_rate_ppm =
        max_abs_rate_ppm;

    service->state =
        TIME_SERVICE_UNINITIALIZED;

    return true;
}

TimeObserveResult time_service_observe_pps(
    TimeService *service,
    uint64_t local_capture_us,
    int64_t reference_time_us)
{
    if (service == NULL ||
        reference_time_us < 0) {
        return TIME_OBSERVE_REJECTED_ARGUMENT;
    }

    if (local_capture_us > (uint64_t)INT64_MAX) {
        return TIME_OBSERVE_REJECTED_ARGUMENT;
    }

    const int64_t local_signed =
        (int64_t)local_capture_us;

    const int64_t observed_offset =
        reference_time_us -
        local_signed;

    if (!service->have_reference) {
        service->reference_local_us =
            local_capture_us;

        service->offset_us =
            observed_offset;

        service->rate_correction_ppb = 0;

        service->last_pps_local_us =
            local_capture_us;

        service->last_observed_offset_us =
            observed_offset;

        service->have_reference = true;

        service->state =
            TIME_SERVICE_PHASE_ONLY;

        return TIME_OBSERVE_ACCEPTED_PHASE;
    }

    if (local_capture_us <=
        service->last_pps_local_us) {
        return TIME_OBSERVE_REJECTED_NONMONOTONIC;
    }

    const uint64_t delta_local_u =
        local_capture_us -
        service->last_pps_local_us;

    if (delta_local_u >
        (uint64_t)INT64_MAX) {
        return TIME_OBSERVE_REJECTED_ARGUMENT;
    }

    const int64_t delta_local =
        (int64_t)delta_local_u;

    const int64_t delta_offset =
        observed_offset -
        service->last_observed_offset_us;

    /*
     * rate_correction_ppb =
     *   d(reference-local) / d(local) * 1e9.
     */
    if (llabs(delta_offset) >
        INT64_MAX / PPB_PER_ONE) {
        return TIME_OBSERVE_REJECTED_RATE;
    }

    const int64_t rate_ppb_64 =
        (delta_offset * PPB_PER_ONE) /
        delta_local;

    const double rate_ppm =
        (double)rate_ppb_64 /
        (double)PPB_PER_PPM;

    if (!isfinite(rate_ppm) ||
        fabs(rate_ppm) >
            (double)service->max_abs_rate_ppm ||
        rate_ppb_64 < INT32_MIN ||
        rate_ppb_64 > INT32_MAX) {
        return TIME_OBSERVE_REJECTED_RATE;
    }

    service->rate_correction_ppb =
        (int32_t)rate_ppb_64;

    service->reference_local_us =
        local_capture_us;

    service->offset_us =
        observed_offset;

    service->last_pps_local_us =
        local_capture_us;

    service->last_observed_offset_us =
        observed_offset;

    service->state =
        TIME_SERVICE_LOCKED;

    return TIME_OBSERVE_ACCEPTED_LOCK;
}

bool time_service_map_us(
    const TimeService *service,
    uint64_t local_time_us,
    int64_t *disciplined_time_us)
{
    if (service == NULL ||
        disciplined_time_us == NULL ||
        !service->have_reference ||
        local_time_us > (uint64_t)INT64_MAX ||
        service->reference_local_us >
            (uint64_t)INT64_MAX) {
        return false;
    }

    const int64_t delta_local =
        (int64_t)local_time_us -
        (int64_t)service->reference_local_us;

    int64_t rate_correction;

    if (!correction_us(
            delta_local,
            service->rate_correction_ppb,
            &rate_correction)) {
        return false;
    }

    const int64_t local_signed =
        (int64_t)local_time_us;

    if ((service->offset_us > 0 &&
         local_signed >
             INT64_MAX - service->offset_us) ||
        (service->offset_us < 0 &&
         local_signed <
             INT64_MIN - service->offset_us)) {
        return false;
    }

    const int64_t phase_adjusted =
        local_signed +
        service->offset_us;

    if ((rate_correction > 0 &&
         phase_adjusted >
             INT64_MAX - rate_correction) ||
        (rate_correction < 0 &&
         phase_adjusted <
             INT64_MIN - rate_correction)) {
        return false;
    }

    *disciplined_time_us =
        phase_adjusted +
        rate_correction;

    return true;
}

float time_service_uncertainty_us(
    const TimeService *service,
    uint64_t local_time_us)
{
    if (service == NULL ||
        !service->have_reference ||
        local_time_us < service->last_pps_local_us) {
        return NAN;
    }

    const uint64_t elapsed_us =
        local_time_us -
        service->last_pps_local_us;

    const float elapsed_seconds =
        (float)elapsed_us /
        1000000.0f;

    /*
     * Conservative first-order holdover bound:
     * ppm * seconds = microseconds.
     */
    return
        service->phase_sigma_us +
        service->drift_sigma_ppm *
        elapsed_seconds;
}

bool time_service_mark_holdover(
    TimeService *service)
{
    if (service == NULL ||
        !service->have_reference) {
        return false;
    }

    service->state =
        TIME_SERVICE_HOLDOVER;

    return true;
}

const char *time_service_state_name(
    TimeServiceState state)
{
    switch (state) {
    case TIME_SERVICE_PHASE_ONLY:
        return "PHASE_ONLY";

    case TIME_SERVICE_LOCKED:
        return "LOCKED";

    case TIME_SERVICE_HOLDOVER:
        return "HOLDOVER";

    case TIME_SERVICE_UNINITIALIZED:
    default:
        return "UNINITIALIZED";
    }
}
