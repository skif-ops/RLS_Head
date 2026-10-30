#include "evt_app.h"

#include "evt_board.h"
#include "evt_gnss_parser.h"
#include "evt_transport.h"
#include "icm42688p.h"
#include "rls/carrier_health.h"
#include "rls/gnss_service.h"
#include "rls/hil_r1.h"
#include "rls/imu_service.h"
#include "rls/time_service.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define EVT_STATUS_MAGIC 0x53545645u
#define EVT_CONFIG_CRC32C 0xaa89a125u
#define EVT_SOURCE_ID 0x45565431u

evt_app_status_t g_evt_app_status
    __attribute__((section(".sram4_status"), aligned(32)));

static uint32_t boot_id(void)
{
    return HAL_GetUIDw0() ^ HAL_GetUIDw1() ^ HAL_GetUIDw2() ^ HAL_GetTick();
}

static void initialize_status(uint32_t init_errors, uint32_t current_boot_id)
{
    memset(&g_evt_app_status, 0, sizeof(g_evt_app_status));
    g_evt_app_status.magic = EVT_STATUS_MAGIC;
    g_evt_app_status.version_major = 1u;
    g_evt_app_status.version_minor = 0u;
    g_evt_app_status.init_error_flags = init_errors;
    g_evt_app_status.config_crc32c = EVT_CONFIG_CRC32C;
    g_evt_app_status.boot_id = current_boot_id;
}

static void process_capture_events(
    evt_capture_snapshot_t *previous,
    rls_carrier_health_state_t *health,
    rls_gnss_service_t *gnss,
    rls_imu_service_t *imu,
    bool *gnss_spoof_suspect,
    uint64_t *previous_pps)
{
    evt_capture_snapshot_t current;
    evt_board_capture_snapshot(&current);

    if (current.sequence[EVT_CAPTURE_GNSS_PPS]
        != previous->sequence[EVT_CAPTURE_GNSS_PPS]) {
        const uint64_t timestamp = current.timestamp_us[EVT_CAPTURE_GNSS_PPS];
        if (*previous_pps != 0u) {
            const uint64_t interval = timestamp - *previous_pps;
            if (interval < 900000u || interval > 1100000u) {
                *gnss_spoof_suspect = true;
            }
        }
        *previous_pps = timestamp;
        rls_carrier_health_note_gnss_pps(health, timestamp);
        rls_gnss_service_note_pps(gnss, timestamp);
    }

    if (current.sequence[EVT_CAPTURE_RADAR_REF]
        != previous->sequence[EVT_CAPTURE_RADAR_REF]) {
        rls_carrier_health_note_radar_ref(
            health, current.timestamp_us[EVT_CAPTURE_RADAR_REF]);
    }

    if (current.sequence[EVT_CAPTURE_IMU_DRDY]
        != previous->sequence[EVT_CAPTURE_IMU_DRDY]) {
        const uint64_t timestamp = current.timestamp_us[EVT_CAPTURE_IMU_DRDY];
        rls_carrier_health_note_imu_drdy(health, timestamp);
        uint32_t sequence;
        if (rls_imu_service_note_drdy(imu, timestamp, &sequence)
            && rls_imu_service_begin_transfer(imu)
            && !evt_board_imu_start_burst()) {
            (void)rls_imu_service_complete_transfer(imu, false);
        }
    }

    *previous = current;
}

static void process_imu(rls_imu_service_t *imu)
{
    uint8_t burst[14];
    bool success;
    if (!evt_board_imu_take_burst(burst, &success)) {
        return;
    }

    icm42688p_sample_t sample;
    const bool decoded = success && icm42688p_decode_burst(burst, &sample);
    (void)sample;
    (void)rls_imu_service_complete_transfer(imu, decoded);
    if (decoded) {
        g_evt_app_status.imu_samples++;
    } else {
        g_evt_app_status.imu_errors++;
    }
}

static void process_gnss(
    evt_gnss_parser_t *parser,
    rls_gnss_service_t *service,
    TimeService *time_service,
    uint64_t latest_pps,
    bool gnss_spoof_suspect,
    uint64_t *observed_pps)
{
    uint8_t bytes[128];
    const size_t length = evt_board_gnss_read(bytes, sizeof(bytes));
    if (length > 0u) {
        rls_gnss_service_note_uart(service, evt_board_time_us());
        evt_gnss_parser_feed(parser, bytes, length);
    }

    rls_gnss_service_update_quality(
        service,
        parser->fix_valid,
        parser->time_valid && !gnss_spoof_suspect,
        false,
        gnss_spoof_suspect);

    if (parser->have_reference_time
        && latest_pps != 0u
        && latest_pps != *observed_pps
        && !gnss_spoof_suspect) {
        const TimeObserveResult result = time_service_observe_pps(
            time_service, latest_pps, (int64_t)parser->reference_time_us);
        if (result == TIME_OBSERVE_ACCEPTED_PHASE
            || result == TIME_OBSERVE_ACCEPTED_LOCK) {
            *observed_pps = latest_pps;
        }
    }
}

static void process_radar(
    evt_transport_rx_t *transport,
    HilRuntime *runtime)
{
    uint8_t can_frame[EVT_CAN_FRAME_SIZE];
    while (evt_board_can_receive(can_frame)) {
        const uint8_t *packet;
        size_t packet_length;
        const evt_transport_result_t result = evt_transport_rx_accept(
            transport, can_frame, &packet, &packet_length);
        if (result != EVT_TRANSPORT_COMPLETE) {
            continue;
        }

        g_evt_app_status.radar_packets++;
        uint8_t response[TARGETSTATE_PACKET_SIZE];
        size_t response_length = 0u;
        const uint64_t now = evt_board_time_us();
        const HilRuntimeResult runtime_result = hil_runtime_process_packet(
            runtime,
            packet,
            packet_length,
            now,
            now,
            response,
            sizeof(response),
            &response_length);
        if (runtime_result == HIL_RUNTIME_OK
            && response_length == TARGETSTATE_PACKET_SIZE
            && evt_board_host_publish(response, response_length)) {
            g_evt_app_status.targetstate_packets++;
        }
    }
}

static void update_health(
    rls_carrier_health_state_t *health,
    rls_gnss_service_t *gnss,
    uint64_t now)
{
    const rls_carrier_health_limits_t health_limits = {
        .radar_timeout_us = 250000u,
        .gnss_pps_timeout_us = 1500000u,
        .imu_timeout_us = 20000u,
    };
    const rls_gnss_limits_t gnss_limits = {
        .uart_timeout_us = 2000000u,
        .pps_timeout_us = 1500000u,
    };
    rls_carrier_health_report_t health_report;
    rls_gnss_report_t gnss_report;
    rls_carrier_health_set_power_faults(health, evt_board_power_fault_flags());
    if (rls_carrier_health_evaluate(health, &health_limits, now, &health_report) == 0) {
        g_evt_app_status.health_flags = health_report.fault_flags;
    }
    if (rls_gnss_service_evaluate(gnss, &gnss_limits, now, &gnss_report) == 0) {
        g_evt_app_status.gnss_flags = gnss_report.flags;
    }
}

int evt_app_main(void)
{
    const uint32_t init_errors = evt_board_initialize();
    const uint32_t current_boot_id = boot_id();
    initialize_status(init_errors, current_boot_id);
    if (init_errors != 0u) {
        evt_board_fatal(init_errors);
    }

    rls_carrier_health_state_t health;
    rls_gnss_service_t gnss;
    rls_imu_service_t imu;
    TimeService disciplined_time;
    evt_gnss_parser_t gnss_parser;
    evt_transport_rx_t transport;
    HilRuntime runtime;
    rls_carrier_health_init(&health);
    rls_gnss_service_init(&gnss);
    rls_imu_service_init(&imu);
    evt_gnss_parser_init(&gnss_parser);
    evt_transport_rx_init(&transport);
    hil_runtime_init(&runtime, EVT_SOURCE_ID, current_boot_id);
    if (!time_service_init(&disciplined_time, 0.1f, 0.5f, 100.0f)) {
        evt_board_fatal(0x54494d45u);
    }

    HAL_Delay(10u);
    if (!icm42688p_initialize(
            evt_board_imu_read_register,
            evt_board_imu_write_register,
            &g_evt_app_status.imu_who_am_i)) {
        g_evt_app_status.imu_errors++;
    }
    HAL_Delay(50u);

    evt_capture_snapshot_t captures = {0};
    uint64_t previous_pps = 0u;
    uint64_t observed_pps = 0u;
    uint64_t last_health_update = 0u;
    bool gnss_spoof_suspect = false;

    for (;;) {
        evt_board_service();
        process_capture_events(
            &captures, &health, &gnss, &imu,
            &gnss_spoof_suspect, &previous_pps);
        process_imu(&imu);
        process_gnss(
            &gnss_parser, &gnss, &disciplined_time,
            captures.timestamp_us[EVT_CAPTURE_GNSS_PPS],
            gnss_spoof_suspect, &observed_pps);
        process_radar(&transport, &runtime);

        const uint64_t now = evt_board_time_us();
        if (now - last_health_update >= 100000u) {
            update_health(&health, &gnss, now);
            g_evt_app_status.transport_rejects = transport.rejected_frames;
            g_evt_app_status.can_bus_offs = evt_board_can_bus_off_count();
            g_evt_app_status.uart1_drops = evt_board_host_drop_count(0u);
            g_evt_app_status.uart2_drops = evt_board_host_drop_count(1u);
            g_evt_app_status.gnss_overflows = evt_board_gnss_overflow_count();
            last_health_update = now;
        }
        evt_board_watchdog_refresh();
    }
}
