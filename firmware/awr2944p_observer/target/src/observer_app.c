#include "rls/observer_app.h"

#include "rls/awr2944p_observer.h"
#include "rls/observer_mcan_port.h"

#include <kernel/dpl/AddrTranslateP.h>
#include <kernel/dpl/ClockP.h>

#include <string.h>

typedef struct {
    rls_awr2944p_observer_t observer;
    rls_observer_mcan_port_t mcan;
    uint32_t processed_frames;
    uint32_t rejected_service_frames;
    bool initialized;
    bool observation_enabled;
} rls_observer_app_context_t;

static rls_observer_app_context_t context;

static uint32_t make_session_id(uint64_t timestamp_us)
{
    uint32_t session_id = (uint32_t)timestamp_us
        ^ (uint32_t)(timestamp_us >> 32)
        ^ 0xa2944f01u;
    return session_id == 0u ? 1u : session_id;
}

static void send_service_ack(
    const rls_radar_service_request_t *request,
    uint8_t status,
    uint64_t timestamp_us)
{
    rls_radar_link_frame_t frame;
    rls_radar_service_ack_t ack;
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];

    memset(&frame, 0, sizeof(frame));
    ack.operation = request->operation;
    ack.status = status;
    ack.request_id = request->request_id;
    frame.version = RLS_RADAR_LINK_VERSION;
    frame.sequence = context.observer.next_sequence++;
    frame.timestamp_us = timestamp_us;
    frame.session_id = context.observer.session_id;
    if (rls_radar_service_ack_pack(&ack, &frame) == RLS_RADAR_LINK_OK
        && rls_radar_link_encode(&frame, wire, sizeof(wire))
            == RLS_RADAR_LINK_OK) {
        (void)rls_observer_mcan_send(
            &context.mcan,
            RLS_RADAR_CAN_AWR_TO_CARRIER_ID,
            1u,
            wire);
    }
}

static void service_control_channel(uint64_t timestamp_us)
{
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];
    rls_radar_link_frame_t frame;
    rls_radar_service_request_t request;

    if (rls_observer_mcan_receive_service(&context.mcan, wire) != 1) {
        return;
    }
    if (rls_radar_link_decode(wire, sizeof(wire), &frame)
            != RLS_RADAR_LINK_OK
        || rls_radar_service_request_unpack(&frame, &request)
            != RLS_RADAR_LINK_OK) {
        context.rejected_service_frames++;
        return;
    }

    uint8_t status = RLS_RADAR_SERVICE_ACK_OK;
    switch (request.operation) {
    case RLS_RADAR_SERVICE_START_OBSERVATION:
        context.observation_enabled = true;
        break;
    case RLS_RADAR_SERVICE_STOP_OBSERVATION:
        context.observation_enabled = false;
        break;
    case RLS_RADAR_SERVICE_RESET_STATISTICS:
        context.processed_frames = 0u;
        context.rejected_service_frames = 0u;
        rls_observer_mcan_reset_statistics(&context.mcan);
        break;
    default:
        status = RLS_RADAR_SERVICE_ACK_UNSUPPORTED;
        break;
    }
    send_service_ack(&request, status, timestamp_us);
}

int rls_awr2944p_observer_app_init(void)
{
    rls_awr2944p_observer_config_t config;
    const uint64_t timestamp_us = ClockP_getTimeUsec();

    memset(&context, 0, sizeof(context));
    rls_awr2944p_observer_default_config(&config);
    if (rls_awr2944p_observer_init(
            &context.observer,
            &config,
            make_session_id(timestamp_us),
            1u) != 0) {
        return -1;
    }
    if (rls_observer_mcan_init(&context.mcan) != 0) {
        return -2;
    }
    context.observation_enabled = true;
    context.initialized = true;
    return 0;
}

void rls_awr2944p_observer_app_process(
    DPC_ObjectDetection_ExecuteResult *result)
{
    if (!context.initialized || result == NULL) {
        return;
    }

    const uint64_t timestamp_us = ClockP_getTimeUsec();
    rls_observer_mcan_service_bus(&context.mcan, timestamp_us);
    service_control_channel(timestamp_us);

    if (rls_awr2944p_observer_begin_frame(
            &context.observer, timestamp_us) != 0) {
        return;
    }

    DPIF_PointCloudCartesian *points = NULL;
    DPIF_PointCloudSideInfo *side_info = NULL;
    if (result->numObjOut != 0u
        && result->objOut != NULL
        && result->objOutSideInfo != NULL) {
        points = (DPIF_PointCloudCartesian *)AddrTranslateP_getLocalAddr(
            (uint32_t)result->objOut);
        side_info = (DPIF_PointCloudSideInfo *)AddrTranslateP_getLocalAddr(
            (uint32_t)result->objOutSideInfo);
    }
    for (uint32_t i = 0u; i < result->numObjOut
            && points != NULL && side_info != NULL; ++i) {
        const rls_awr2944p_detection_t detection = {
            points[i].x,
            points[i].y,
            points[i].z,
            points[i].velocity,
            side_info[i].snr,
            side_info[i].noise
        };
        (void)rls_awr2944p_observer_consider_detection(
            &context.observer, &detection);
    }

    rls_awr2944p_observer_output_t output;
    if (rls_awr2944p_observer_end_frame(&context.observer, &output) != 0) {
        return;
    }
    context.processed_frames++;
    if (!context.observation_enabled) {
        return;
    }
    if (rls_observer_mcan_take_recovered_event(&context.mcan)) {
        output.status_flags |= RLS_RADAR_STATUS_BUS_OFF_RECOVERED;
    }

    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];
    if (rls_awr2944p_observer_build_can_frame(
            &context.observer, &output, wire) == RLS_RADAR_LINK_OK) {
        (void)rls_observer_mcan_send(
            &context.mcan,
            RLS_RADAR_CAN_AWR_TO_CARRIER_ID,
            0u,
            wire);
    }
}
