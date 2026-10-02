#include "rls/time_service.h"

#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define CHECK(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return false; \
    } \
} while (0)

static bool nearf_abs(
    float actual,
    float expected,
    float tolerance)
{
    return fabsf(actual - expected) <= tolerance;
}

static bool test_time_001_lock_and_map(void)
{
    TimeService service;

    CHECK(time_service_init(
        &service,
        0.25f,
        2.0f,
        100.0f));

    CHECK(
        time_service_observe_pps(
            &service,
            1000000u,
            10000000) ==
        TIME_OBSERVE_ACCEPTED_PHASE);

    CHECK(
        service.state ==
        TIME_SERVICE_PHASE_ONLY);

    int64_t mapped;

    CHECK(time_service_map_us(
        &service,
        1000000u,
        &mapped));

    CHECK(mapped == 10000000);

    /*
     * One second later the reference-local offset increased by 2 us:
     * estimated rate correction = +2000 ppb = +2 ppm.
     */
    CHECK(
        time_service_observe_pps(
            &service,
            2000000u,
            11000002) ==
        TIME_OBSERVE_ACCEPTED_LOCK);

    CHECK(
        service.state ==
        TIME_SERVICE_LOCKED);

    CHECK(
        service.rate_correction_ppb ==
        2000);

    CHECK(time_service_map_us(
        &service,
        2500000u,
        &mapped));

    CHECK(mapped == 11500003);

    return true;
}

static bool test_time_002_holdover_2ppm(void)
{
    TimeService service;

    CHECK(time_service_init(
        &service,
        0.0f,
        2.0f,
        100.0f));

    CHECK(
        time_service_observe_pps(
            &service,
            1000000u,
            10000000) ==
        TIME_OBSERVE_ACCEPTED_PHASE);

    CHECK(
        time_service_observe_pps(
            &service,
            2000000u,
            11000002) ==
        TIME_OBSERVE_ACCEPTED_LOCK);

    CHECK(time_service_mark_holdover(
        &service));

    CHECK(
        service.state ==
        TIME_SERVICE_HOLDOVER);

    struct {
        uint64_t seconds;
        float expected_uncertainty_us;
    } cases[] = {
        {1u, 2.0f},
        {10u, 20.0f},
        {30u, 60.0f},
        {60u, 120.0f},
        {300u, 600.0f}
    };

    for (unsigned i = 0;
         i < sizeof(cases) / sizeof(cases[0]);
         ++i) {
        const uint64_t local =
            service.last_pps_local_us +
            cases[i].seconds * 1000000u;

        CHECK(nearf_abs(
            time_service_uncertainty_us(
                &service,
                local),
            cases[i].expected_uncertainty_us,
            1.0e-5f));
    }

    int64_t mapped;

    CHECK(time_service_map_us(
        &service,
        service.last_pps_local_us +
            300000000u,
        &mapped));

    /*
     * 300 s at +2 ppm correction adds 600 us.
     */
    CHECK(mapped == 311000602);

    return true;
}

static bool test_time_003_nonmonotonic_reject(void)
{
    TimeService service;

    CHECK(time_service_init(
        &service,
        0.1f,
        2.0f,
        100.0f));

    CHECK(
        time_service_observe_pps(
            &service,
            1000000u,
            10000000) ==
        TIME_OBSERVE_ACCEPTED_PHASE);

    CHECK(
        time_service_observe_pps(
            &service,
            999999u,
            11000000) ==
        TIME_OBSERVE_REJECTED_NONMONOTONIC);

    CHECK(
        service.last_pps_local_us ==
        1000000u);

    return true;
}

static bool test_time_004_implausible_rate_reject(void)
{
    TimeService service;

    CHECK(time_service_init(
        &service,
        0.1f,
        2.0f,
        100.0f));

    CHECK(
        time_service_observe_pps(
            &service,
            1000000u,
            10000000) ==
        TIME_OBSERVE_ACCEPTED_PHASE);

    /*
     * +1000 us offset step over one second -> +1000 ppm,
     * outside the configured +/-100 ppm plausibility gate.
     */
    CHECK(
        time_service_observe_pps(
            &service,
            2000000u,
            11001000) ==
        TIME_OBSERVE_REJECTED_RATE);

    CHECK(
        service.state ==
        TIME_SERVICE_PHASE_ONLY);

    CHECK(
        service.rate_correction_ppb ==
        0);

    return true;
}

static bool test_time_005_uninitialized_map_reject(void)
{
    TimeService service;

    CHECK(time_service_init(
        &service,
        0.1f,
        2.0f,
        100.0f));

    int64_t mapped;

    CHECK(!time_service_map_us(
        &service,
        100u,
        &mapped));

    CHECK(isnan(
        time_service_uncertainty_us(
            &service,
            100u)));

    return true;
}

static bool test_time_006_state_names(void)
{
    CHECK(strcmp(
        time_service_state_name(
            TIME_SERVICE_UNINITIALIZED),
        "UNINITIALIZED") == 0);

    CHECK(strcmp(
        time_service_state_name(
            TIME_SERVICE_PHASE_ONLY),
        "PHASE_ONLY") == 0);

    CHECK(strcmp(
        time_service_state_name(
            TIME_SERVICE_LOCKED),
        "LOCKED") == 0);

    CHECK(strcmp(
        time_service_state_name(
            TIME_SERVICE_HOLDOVER),
        "HOLDOVER") == 0);

    return true;
}

typedef bool (*TestFn)(void);

typedef struct {
    const char *name;
    TestFn fn;
} TestCase;

int main(void)
{
    const TestCase tests[] = {
        {"TIME-001 lock/map", test_time_001_lock_and_map},
        {"TIME-002 holdover", test_time_002_holdover_2ppm},
        {"TIME-003 monotonic", test_time_003_nonmonotonic_reject},
        {"TIME-004 rate gate", test_time_004_implausible_rate_reject},
        {"TIME-005 uninitialized", test_time_005_uninitialized_map_reject},
        {"TIME-006 state names", test_time_006_state_names}
    };

    const size_t count =
        sizeof(tests) / sizeof(tests[0]);

    for (size_t i = 0; i < count; ++i) {
        if (!tests[i].fn()) {
            fprintf(
                stderr,
                "%s FAILED\n",
                tests[i].name);

            return 1;
        }

        printf(
            "%s PASS\n",
            tests[i].name);
    }

    printf(
        "TIME SERVICE SUITE PASS (%zu tests)\n",
        count);

    return 0;
}
