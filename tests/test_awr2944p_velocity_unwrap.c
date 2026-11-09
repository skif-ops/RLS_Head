#include "rls/awr2944p_velocity_unwrap.h"

#include <math.h>
#include <stdbool.h>
#include <stddef.h>

#define CHECK(condition) do { if (!(condition)) return __LINE__; } while (0)

static float wrap_velocity(float value, float half_period)
{
    const float period = 2.0f * half_period;
    return value - period * roundf(value / period);
}

static int check_velocity(float velocity_m_s, float noise_m_s)
{
    rls_awr2944p_velocity_unwrap_config_t config;
    float measured[RLS_AWR2944P_VELOCITY_PROFILE_COUNT];
    float result;
    float residual;
    rls_awr2944p_velocity_unwrap_default_config(&config);
    for (size_t i = 0u; i < RLS_AWR2944P_VELOCITY_PROFILE_COUNT; ++i) {
        const float signed_noise = (i & 1u) == 0u ? noise_m_s : -noise_m_s;
        measured[i] = wrap_velocity(
            velocity_m_s, config.unambiguous_velocity_m_s[i]) + signed_noise;
    }
    CHECK(rls_awr2944p_velocity_unwrap(
        &config, measured, true, velocity_m_s - 1.0f,
        &result, &residual) == 0);
    CHECK(fabsf(result - velocity_m_s) <= noise_m_s + 0.05f);
    CHECK(residual <= config.maximum_residual_m_s);
    return 0;
}

static int test_required_velocity_interval(void)
{
    CHECK(check_velocity(36.111111f, 0.0f) == 0);
    CHECK(check_velocity(52.777779f, 0.0f) == 0);
    CHECK(check_velocity(-36.111111f, 0.0f) == 0);
    CHECK(check_velocity(-52.777779f, 0.0f) == 0);
    CHECK(check_velocity(52.777779f, 0.2f) == 0);
    return 0;
}

static int test_full_candidate_interval(void)
{
    for (int velocity_tenths = -600; velocity_tenths <= 600;
            ++velocity_tenths) {
        CHECK(check_velocity((float)velocity_tenths * 0.1f, 0.0f) == 0);
    }
    return 0;
}

static int test_rejects_inconsistent_measurements(void)
{
    rls_awr2944p_velocity_unwrap_config_t config;
    const float measured[RLS_AWR2944P_VELOCITY_PROFILE_COUNT] = {
        0.0f, 3.0f, -3.0f
    };
    float result;
    float residual;
    rls_awr2944p_velocity_unwrap_default_config(&config);
    CHECK(rls_awr2944p_velocity_unwrap(
        &config, measured, false, 0.0f, &result, &residual) == 1);
    return 0;
}

int main(void)
{
    CHECK(test_required_velocity_interval() == 0);
    CHECK(test_full_candidate_interval() == 0);
    CHECK(test_rejects_inconsistent_measurements() == 0);
    return 0;
}
