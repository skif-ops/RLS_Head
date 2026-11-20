#ifndef ICM42688P_H
#define ICM42688P_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    float temperature_c;
    float acceleration_m_s2[3];
    float angular_rate_rad_s[3];
} icm42688p_sample_t;

typedef bool (*icm42688p_read_fn)(uint8_t reg, uint8_t *value);
typedef bool (*icm42688p_write_fn)(uint8_t reg, uint8_t value);

bool icm42688p_initialize(
    icm42688p_read_fn read_register,
    icm42688p_write_fn write_register,
    uint8_t *who_am_i);

bool icm42688p_decode_burst(
    const uint8_t burst[14],
    icm42688p_sample_t *sample);

#endif
