#include "evt_transport.h"

#include <string.h>

static uint16_t read_u16(const uint8_t *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static void write_u16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
}

void evt_transport_rx_init(evt_transport_rx_t *rx)
{
    if (rx != NULL) {
        memset(rx, 0, sizeof(*rx));
    }
}

evt_transport_result_t evt_transport_rx_accept(
    evt_transport_rx_t *rx,
    const uint8_t frame[EVT_CAN_FRAME_SIZE],
    const uint8_t **packet,
    size_t *packet_length)
{
    if (rx == NULL || frame == NULL || packet == NULL || packet_length == NULL) {
        return EVT_TRANSPORT_REJECTED;
    }

    *packet = NULL;
    *packet_length = 0u;

    const uint16_t magic = read_u16(&frame[0]);
    const uint8_t version = frame[2];
    const uint8_t flags = frame[3];
    const uint16_t sequence = read_u16(&frame[4]);
    const uint16_t offset = read_u16(&frame[6]);
    const uint16_t total = read_u16(&frame[8]);
    const uint8_t length = frame[10];

    const bool header_ok =
        magic == EVT_CAN_TRANSPORT_MAGIC
        && version == EVT_CAN_TRANSPORT_VERSION
        && (flags & ~(EVT_CAN_FLAG_START | EVT_CAN_FLAG_END)) == 0u
        && frame[11] == 0u
        && length <= EVT_CAN_PAYLOAD_SIZE
        && total > 0u
        && total <= EVT_CAN_MAX_TRANSFER_SIZE
        && (uint32_t)offset + length <= total;

    if (!header_ok) {
        rx->active = false;
        rx->rejected_frames++;
        return EVT_TRANSPORT_REJECTED;
    }

    if ((flags & EVT_CAN_FLAG_START) != 0u) {
        if (offset != 0u) {
            rx->active = false;
            rx->rejected_frames++;
            return EVT_TRANSPORT_REJECTED;
        }

        rx->transfer_sequence = sequence;
        rx->total_length = total;
        rx->received_length = 0u;
        rx->active = true;
    }

    if (!rx->active
        || sequence != rx->transfer_sequence
        || total != rx->total_length
        || offset != rx->received_length) {
        rx->active = false;
        rx->rejected_frames++;
        return EVT_TRANSPORT_REJECTED;
    }

    memcpy(&rx->payload[offset], &frame[EVT_CAN_HEADER_SIZE], length);
    rx->received_length = (uint16_t)(rx->received_length + length);

    if ((flags & EVT_CAN_FLAG_END) == 0u) {
        return EVT_TRANSPORT_MORE;
    }

    if (rx->received_length != rx->total_length) {
        rx->active = false;
        rx->rejected_frames++;
        return EVT_TRANSPORT_REJECTED;
    }

    rx->active = false;
    rx->completed_transfers++;
    *packet = rx->payload;
    *packet_length = rx->total_length;
    return EVT_TRANSPORT_COMPLETE;
}

size_t evt_transport_encode_segment(
    uint16_t transfer_sequence,
    uint16_t offset,
    uint16_t total_length,
    const uint8_t *payload,
    uint8_t payload_length,
    uint8_t frame[EVT_CAN_FRAME_SIZE])
{
    if (frame == NULL
        || payload == NULL
        || payload_length == 0u
        || payload_length > EVT_CAN_PAYLOAD_SIZE
        || total_length == 0u
        || total_length > EVT_CAN_MAX_TRANSFER_SIZE
        || (uint32_t)offset + payload_length > total_length) {
        return 0u;
    }

    memset(frame, 0, EVT_CAN_FRAME_SIZE);
    write_u16(&frame[0], EVT_CAN_TRANSPORT_MAGIC);
    frame[2] = EVT_CAN_TRANSPORT_VERSION;
    if (offset == 0u) {
        frame[3] |= EVT_CAN_FLAG_START;
    }
    if ((uint32_t)offset + payload_length == total_length) {
        frame[3] |= EVT_CAN_FLAG_END;
    }
    write_u16(&frame[4], transfer_sequence);
    write_u16(&frame[6], offset);
    write_u16(&frame[8], total_length);
    frame[10] = payload_length;
    memcpy(&frame[EVT_CAN_HEADER_SIZE], payload, payload_length);
    return EVT_CAN_HEADER_SIZE + payload_length;
}
