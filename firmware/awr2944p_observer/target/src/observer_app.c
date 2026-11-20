#include "rls/observer_app.h"

#include "rls/awr2944p_observer.h"
#include "rls/awr2944p_velocity_unwrap.h"
#include "rls/observer_mcan_port.h"

#include "../mmw_mss.h"

#include <kernel/dpl/AddrTranslateP.h>
#include <kernel/dpl/ClockP.h>

#include <math.h>
#include <string.h>

#define RLS_OBSERVER_EXPECTED_SUBFRAMES 3u
#define RLS_OBSERVER_EXPECTED_VIRTUAL_CHANNELS 16u

extern MmwDemo_MSS_MCB gMmwMssMCB;

typedef struct {
    rls_awr2944p_observer_t observer;
    rls_observer_mcan_port_t mcan;
    uint32_t processed_frames;
    uint32_t rejected_service_frames;
    rls_awr2944p_detection_t pending_detection[
        RLS_AWR2944P_VELOCITY_PROFILE_COUNT];
    uint8_t pending_detection_mask;
    bool initialized;
    bool observation_enabled;
} rls_observer_app_context_t;

static rls_observer_app_context_t context;

static bool near_value(float actual, float expected, float tolerance)
{
    return isfinite(actual) && fabsf(actual - expected) <= tolerance;
}

static bool profile_contract_matches(void)
{
    static const uint8_t expected_rows[RLS_OBSERVER_EXPECTED_VIRTUAL_CHANNELS] = {
        1u, 1u, 1u, 1u,
        0u, 0u, 0u, 0u,
        1u, 1u, 1u, 1u,
        1u, 1u, 1u, 1u
    };
    static const uint8_t expected_columns[
        RLS_OBSERVER_EXPECTED_VIRTUAL_CHANNELS] = {
        0u, 1u, 2u, 3u,
        2u, 3u, 4u, 5u,
        4u, 5u, 6u, 7u,
        8u, 9u, 10u, 11u
    };
    static const float expected_doppler_limits[3] = {7.5f, 6.8f, 5.8f};

    const DPC_ObjectDetection_PreStartCommonCfg *common =
        &gMmwMssMCB.objDetCommonCfg.preStartCommonCfg;
    if (gMmwMssMCB.sensorState != MmwDemo_SensorState_STARTED
        || gMmwMssMCB.cfg.openCfg.chCfg.rxChannelEn != 0x0fu
        || gMmwMssMCB.cfg.openCfg.chCfg.txChannelEn != 0x0fu
        || common->numSubFrames != RLS_OBSERVER_EXPECTED_SUBFRAMES
        || !near_value(common->antennaSpacing.xSpacingByLambda, 0.5f, 0.001f)
        || !near_value(common->antennaSpacing.zSpacingByLambda, 0.8f, 0.001f)) {
        return false;
    }
    for (uint32_t i = 0u; i < RLS_OBSERVER_EXPECTED_VIRTUAL_CHANNELS; ++i) {
        if (common->antGeometryCfg[i].row != expected_rows[i]
            || common->antGeometryCfg[i].col != expected_columns[i]) {
            return false;
        }
    }
    for (uint32_t i = 0u; i < RLS_OBSERVER_EXPECTED_SUBFRAMES; ++i) {
        const MmwDemo_SubFrameCfg *subframe = &gMmwMssMCB.subFrameCfg[i];
        const DPC_ObjectDetection_DynCfg *dynamic =
            &subframe->objDetDynCfg.dynCfg;
        if (subframe->numVirtualAntennas
                != RLS_OBSERVER_EXPECTED_VIRTUAL_CHANNELS
            || subframe->numAdcSamples != 800u
            || subframe->numRangeBins != 1024u
            || subframe->numChirpsPerSubFrame != 128u
            || dynamic->extMaxVelCfg.enabled != 0u
            || !near_value(dynamic->fovRange.min, 0.5f, 0.01f)
            || !near_value(dynamic->fovRange.max, 350.0f, 0.01f)
            || !near_value(dynamic->fovDoppler.min,
                -expected_doppler_limits[i], 0.01f)
            || !near_value(dynamic->fovDoppler.max,
                expected_doppler_limits[i], 0.01f)
            || !near_value(dynamic->fovAoaCfg.minAzimuthDeg, -60.0f, 0.01f)
            || !near_value(dynamic->fovAoaCfg.maxAzimuthDeg, 60.0f, 0.01f)
            || !near_value(dynamic->fovAoaCfg.minElevationDeg, -22.0f, 0.01f)
            || !near_value(dynamic->fovAoaCfg.maxElevationDeg, 22.0f, 0.01f)) {
            return false;
        }
    }
    return true;
}

static bool select_strongest_detection(
    DPC_ObjectDetection_ExecuteResult *result,
    rls_awr2944p_detection_t *selected)
{
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
    if (points == NULL || side_info == NULL) {
        return false;
    }
    bool found = false;
    int16_t strongest_snr = 0;
    for (uint32_t i = 0u; i < result->numObjOut; ++i) {
        if (!found || side_info[i].snr > strongest_snr) {
            *selected = (rls_awr2944p_detection_t){
                points[i].x,
                points[i].y,
                points[i].z,
                points[i].velocity,
                side_info[i].snr,
                side_info[i].noise
            };
            strongest_snr = side_info[i].snr;
            found = true;
        }
    }
    return found;
}

static bool process_three_prf_cycle(
    DPC_ObjectDetection_ExecuteResult *result,
    uint64_t timestamp_us,
    rls_awr2944p_observer_output_t *output)
{
    if (result->subFrameIdx >= RLS_OBSERVER_EXPECTED_SUBFRAMES) {
        return false;
    }
    if (result->subFrameIdx == 0u) {
        context.pending_detection_mask = 0u;
    }
    rls_awr2944p_detection_t detection;
    if (select_strongest_detection(result, &detection)) {
        context.pending_detection[result->subFrameIdx] = detection;
        context.pending_detection_mask |= (uint8_t)(1u << result->subFrameIdx);
    }
    if (result->subFrameIdx + 1u != RLS_OBSERVER_EXPECTED_SUBFRAMES) {
        return false;
    }

    rls_awr2944p_detection_t fused;
    size_t detection_count = 0u;
    if (context.pending_detection_mask
            == (1u << RLS_OBSERVER_EXPECTED_SUBFRAMES) - 1u) {
        rls_awr2944p_velocity_unwrap_config_t unwrap_config;
        float measured[RLS_AWR2944P_VELOCITY_PROFILE_COUNT];
        float velocity;
        float residual;
        rls_awr2944p_velocity_unwrap_default_config(&unwrap_config);
        memset(&fused, 0, sizeof(fused));
        for (size_t i = 0u; i < RLS_AWR2944P_VELOCITY_PROFILE_COUNT; ++i) {
            const rls_awr2944p_detection_t *source =
                &context.pending_detection[i];
            fused.x_m += source->x_m;
            fused.y_m += source->y_m;
            fused.z_m += source->z_m;
            measured[i] = source->radial_velocity_m_s;
            if (i == 0u || source->snr_decidb > fused.snr_decidb) {
                fused.snr_decidb = source->snr_decidb;
                fused.noise_decidb = source->noise_decidb;
            }
        }
        fused.x_m /= (float)RLS_AWR2944P_VELOCITY_PROFILE_COUNT;
        fused.y_m /= (float)RLS_AWR2944P_VELOCITY_PROFILE_COUNT;
        fused.z_m /= (float)RLS_AWR2944P_VELOCITY_PROFILE_COUNT;
        if (rls_awr2944p_velocity_unwrap(
                &unwrap_config,
                measured,
                context.observer.active,
                context.observer.radial_velocity_m_s,
                &velocity,
                &residual) == 0) {
            fused.radial_velocity_m_s = velocity;
            detection_count = 1u;
        }
    }
    context.pending_detection_mask = 0u;
    return rls_awr2944p_observer_process(
        &context.observer,
        detection_count == 0u ? NULL : &fused,
        detection_count,
        timestamp_us,
        output) == 0;
}

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

    context.observer.config.profile_config_match = profile_contract_matches();

    if (gMmwMssMCB.objDetCommonCfg.preStartCommonCfg.numSubFrames
            == RLS_OBSERVER_EXPECTED_SUBFRAMES) {
        rls_awr2944p_observer_output_t output;
        if (!process_three_prf_cycle(result, timestamp_us, &output)) {
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
        return;
    }

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
