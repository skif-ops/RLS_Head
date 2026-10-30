#ifndef EVT_APP_H
#define EVT_APP_H

#include <stdint.h>

typedef struct {
    uint32_t magic;
    uint16_t version_major;
    uint16_t version_minor;
    uint32_t init_error_flags;
    uint32_t config_crc32c;
    uint32_t boot_id;
    uint32_t radar_packets;
    uint32_t targetstate_packets;
    uint32_t transport_rejects;
    uint32_t can_bus_offs;
    uint32_t uart1_drops;
    uint32_t uart2_drops;
    uint32_t gnss_overflows;
    uint32_t imu_samples;
    uint32_t imu_errors;
    uint32_t health_flags;
    uint32_t gnss_flags;
    uint8_t imu_who_am_i;
    uint8_t reserved[3];
} evt_app_status_t;

extern evt_app_status_t g_evt_app_status;

int evt_app_main(void);

#endif
