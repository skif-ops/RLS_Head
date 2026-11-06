#ifndef EVT_TRANSPORT_H
#define EVT_TRANSPORT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define EVT_CAN_TRANSPORT_MAGIC 0x5645u
#define EVT_CAN_TRANSPORT_VERSION 1u
#define EVT_CAN_FRAME_SIZE 64u
#define EVT_CAN_HEADER_SIZE 12u
#define EVT_CAN_PAYLOAD_SIZE (EVT_CAN_FRAME_SIZE - EVT_CAN_HEADER_SIZE)
#define EVT_CAN_MAX_TRANSFER_SIZE 3400u

enum {
    EVT_CAN_FLAG_START = 1u << 0,
    EVT_CAN_FLAG_END = 1u << 1,
};

typedef enum {
    EVT_TRANSPORT_MORE = 0,
    EVT_TRANSPORT_COMPLETE,
    EVT_TRANSPORT_REJECTED,
} evt_transport_result_t;

typedef struct {
    uint8_t payload[EVT_CAN_MAX_TRANSFER_SIZE];
    uint16_t transfer_sequence;
    uint16_t total_length;
    uint16_t received_length;
    uint32_t completed_transfers;
    uint32_t rejected_frames;
    bool active;
} evt_transport_rx_t;

void evt_transport_rx_init(evt_transport_rx_t *rx);

evt_transport_result_t evt_transport_rx_accept(
    evt_transport_rx_t *rx,
    const uint8_t frame[EVT_CAN_FRAME_SIZE],
    const uint8_t **packet,
    size_t *packet_length);

size_t evt_transport_encode_segment(
    uint16_t transfer_sequence,
    uint16_t offset,
    uint16_t total_length,
    const uint8_t *payload,
    uint8_t payload_length,
    uint8_t frame[EVT_CAN_FRAME_SIZE]);

#ifdef __cplusplus
}
#endif

#endif
