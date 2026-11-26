#include "icm42688p.h"

#include <stddef.h>

enum {
    ICM_REG_PWR_MGMT0 = 0x4eu,
    ICM_REG_GYRO_CONFIG0 = 0x4fu,
    ICM_REG_ACCEL_CONFIG0 = 0x50u,
    ICM_REG_INT_SOURCE0 = 0x65u,
    ICM_REG_WHO_AM_I = 0x75u,
    ICM_WHO_AM_I_VALUE = 0x47u,
};

static int16_t read_i16_be(const uint8_t *p)
{
    return (int16_t)((uint16_t)p[0] << 8 | p[1]);
}

bool icm42688p_initialize(
    icm42688p_read_fn read_register,
    icm42688p_write_fn write_register,
    uint8_t *who_am_i)
{
    if (read_register == NULL || write_register == NULL || who_am_i == NULL) {
        return false;
    }

    if (!read_register(ICM_REG_WHO_AM_I, who_am_i)
        || *who_am_i != ICM_WHO_AM_I_VALUE) {
        return false;
    }

    /* ±2000 dps and ±16 g at 1 kHz, matching the datasheet reset ODR. */
    if (!write_register(ICM_REG_GYRO_CONFIG0, 0x06u)
        || !write_register(ICM_REG_ACCEL_CONFIG0, 0x06u)
        || !write_register(ICM_REG_INT_SOURCE0, 0x08u)
        || !write_register(ICM_REG_PWR_MGMT0, 0x0fu)) {
        return false;
    }

    return true;
}

bool icm42688p_decode_burst(
    const uint8_t burst[14],
    icm42688p_sample_t *sample)
{
    if (burst == NULL || sample == NULL) {
        return false;
    }

    const int16_t temp = read_i16_be(&burst[0]);
    const float accel_scale = 9.80665f / 2048.0f;
    const float gyro_scale = 0.017453292519943295f / 16.4f;

    sample->temperature_c = (float)temp / 132.48f + 25.0f;
    for (size_t axis = 0u; axis < 3u; ++axis) {
        sample->acceleration_m_s2[axis] =
            (float)read_i16_be(&burst[2u + axis * 2u]) * accel_scale;
        sample->angular_rate_rad_s[axis] =
            (float)read_i16_be(&burst[8u + axis * 2u]) * gyro_scale;
    }
    return true;
}
