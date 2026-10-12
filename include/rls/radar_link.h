#ifndef RLS_RADAR_LINK_H
#define RLS_RADAR_LINK_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RLS_RADAR_LINK_VERSION 1u
#define RLS_RADAR_LINK_WIRE_SIZE 24u

typedef enum {
    RLS_RADAR_MSG_HEARTBEAT = 1,
    RLS_RADAR_MSG_FRAME_META = 2,
    RLS_RADAR_MSG_HEALTH = 3
} rls_radar_msg_type_t;

typedef struct {
    uint8_t version;
    uint8_t type;
    uint16_t status_flags;
    uint32_t sequence;
    uint64_t radar_time_us;
    uint32_t config_crc32;
    int16_t temperature_cdeg;
    uint16_t measurement_count;
} rls_radar_link_msg_t;

int rls_radar_link_encode(
    const rls_radar_link_msg_t *msg,
    uint8_t *wire,
    size_t wire_size
);

int rls_radar_link_decode(
    const uint8_t *wire,
    size_t wire_size,
    rls_radar_link_msg_t *msg
);

int rls_radar_link_is_valid_type(uint8_t type);

#ifdef __cplusplus
}
#endif

#endif
