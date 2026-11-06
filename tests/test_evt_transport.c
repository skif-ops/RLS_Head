#include "evt_transport.h"

#include <stdint.h>
#include <string.h>

static int round_trip(void)
{
    uint8_t input[137];
    for (size_t i = 0; i < sizeof(input); ++i) {
        input[i] = (uint8_t)(i ^ 0x5au);
    }

    evt_transport_rx_t rx;
    evt_transport_rx_init(&rx);

    uint8_t frame[EVT_CAN_FRAME_SIZE];
    const uint8_t *packet = NULL;
    size_t packet_length = 0u;
    uint16_t offset = 0u;

    while (offset < sizeof(input)) {
        const size_t remaining = sizeof(input) - offset;
        const uint8_t chunk = (uint8_t)(
            remaining > EVT_CAN_PAYLOAD_SIZE ? EVT_CAN_PAYLOAD_SIZE : remaining);
        if (evt_transport_encode_segment(
                42u,
                offset,
                sizeof(input),
                &input[offset],
                chunk,
                frame) == 0u) {
            return 1;
        }

        const evt_transport_result_t result = evt_transport_rx_accept(
            &rx, frame, &packet, &packet_length);
        offset = (uint16_t)(offset + chunk);

        if (offset < sizeof(input) && result != EVT_TRANSPORT_MORE) {
            return 2;
        }
        if (offset == sizeof(input) && result != EVT_TRANSPORT_COMPLETE) {
            return 3;
        }
    }

    if (packet_length != sizeof(input) || memcmp(packet, input, sizeof(input)) != 0) {
        return 4;
    }
    return rx.completed_transfers == 1u && rx.rejected_frames == 0u ? 0 : 5;
}

static int rejects_gap(void)
{
    const uint8_t payload[4] = {1u, 2u, 3u, 4u};
    uint8_t frame[EVT_CAN_FRAME_SIZE];
    evt_transport_rx_t rx;
    const uint8_t *packet;
    size_t packet_length;

    evt_transport_rx_init(&rx);
    if (evt_transport_encode_segment(1u, 0u, 8u, payload, 4u, frame) == 0u) {
        return 1;
    }
    if (evt_transport_rx_accept(&rx, frame, &packet, &packet_length) != EVT_TRANSPORT_MORE) {
        return 2;
    }
    if (evt_transport_encode_segment(1u, 5u, 8u, payload, 3u, frame) == 0u) {
        return 3;
    }
    return evt_transport_rx_accept(&rx, frame, &packet, &packet_length)
        == EVT_TRANSPORT_REJECTED ? 0 : 4;
}

int main(void)
{
    if (round_trip() != 0) {
        return 1;
    }
    return rejects_gap() == 0 ? 0 : 2;
}
