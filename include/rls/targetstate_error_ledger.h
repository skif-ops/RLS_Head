#pragma once

#include <stdbool.h>

#include "rls/targetstate_uncertainty.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    TS_ERROR_SOURCE_NONE = 0,
    TS_ERROR_SOURCE_BASE_TRACK,
    TS_ERROR_SOURCE_HOST_ATTITUDE,
    TS_ERROR_SOURCE_TIMESTAMP,
    TS_ERROR_SOURCE_EXTRINSIC
} TargetStateErrorSource;

typedef struct {
    float base_trace_m2;
    float attitude_trace_m2;
    float timestamp_trace_m2;
    float extrinsic_trace_m2;

    float added_trace_m2;
    float total_trace_m2;

    float base_fraction_total;
    float attitude_fraction_total;
    float timestamp_fraction_total;
    float extrinsic_fraction_total;

    TargetStateErrorSource dominant_overall_source;
    float dominant_overall_fraction;

    TargetStateErrorSource dominant_added_source;
    float dominant_added_fraction;
} TargetStateErrorLedger;

bool targetstate_build_error_ledger(
    const TargetStateSysErrResult *result,
    TargetStateErrorLedger *ledger);

const char *targetstate_error_source_name(
    TargetStateErrorSource source);

#ifdef __cplusplus
}
#endif
