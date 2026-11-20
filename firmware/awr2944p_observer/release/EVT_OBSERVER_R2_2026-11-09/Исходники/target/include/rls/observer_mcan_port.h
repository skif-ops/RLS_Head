#ifndef RLS_OBSERVER_MCAN_PORT_H
#define RLS_OBSERVER_MCAN_PORT_H

#include "rls/radar_link.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint32_t base_address;
    uint64_t bus_off_since_us;
    uint32_t transmitted_frames;
    uint32_t received_frames;
    uint32_t dropped_transmissions;
    uint32_t rejected_receptions;
    uint32_t bus_off_count;
    bool initialized;
    bool bus_off_active;
    bool recovered_event;
} rls_observer_mcan_port_t;

int rls_observer_mcan_init(rls_observer_mcan_port_t *port);

int rls_observer_mcan_send(
    rls_observer_mcan_port_t *port,
    uint32_t standard_id,
    uint32_t buffer_number,
    const uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE]
);

int rls_observer_mcan_receive_service(
    rls_observer_mcan_port_t *port,
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE]
);

void rls_observer_mcan_service_bus(
    rls_observer_mcan_port_t *port,
    uint64_t timestamp_us
);

bool rls_observer_mcan_take_recovered_event(
    rls_observer_mcan_port_t *port
);

void rls_observer_mcan_reset_statistics(
    rls_observer_mcan_port_t *port
);

#endif
