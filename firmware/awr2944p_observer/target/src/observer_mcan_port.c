#include "rls/observer_mcan_port.h"

#include "ti_drivers_config.h"

#include <drivers/mcan.h>
#include <kernel/dpl/AddrTranslateP.h>

#include <string.h>

#define RLS_MCAN_STD_ID_MASK 0x7ffu
#define RLS_MCAN_STD_ID_SHIFT 18u
#define RLS_MCAN_SERVICE_RX_BUFFER 0u
#define RLS_MCAN_MEASUREMENT_TX_BUFFER 0u
#define RLS_MCAN_SERVICE_TX_BUFFER 1u
#define RLS_MCAN_BUS_OFF_RECOVERY_US UINT64_C(100000)

static void init_message_ram(MCAN_MsgRAMConfigParams *config)
{
    MCAN_initMsgRamConfigParams(config);
    config->lss = 1u;
    config->lse = 0u;
    config->txBufCnt = 2u;
    config->txFIFOCnt = 0u;
    config->txBufMode = MCAN_TX_MEM_TYPE_BUF;
    config->txEventFIFOCnt = 0u;
    config->rxFIFO0Cnt = 0u;
    config->rxFIFO1Cnt = 0u;
    config->rxFIFO0OpMode = MCAN_RX_FIFO_OPERATION_MODE_BLOCKING;
    config->rxFIFO1OpMode = MCAN_RX_FIFO_OPERATION_MODE_BLOCKING;
}

int rls_observer_mcan_init(rls_observer_mcan_port_t *port)
{
    if (port == NULL) {
        return -1;
    }

    MCAN_InitParams init_params = {0};
    MCAN_ConfigParams config_params = {0};
    MCAN_MsgRAMConfigParams ram_params = {0};
    MCAN_BitTimingParams bit_times = {0};
    MCAN_StdMsgIDFilterElement filter = {0};

    memset(port, 0, sizeof(*port));
    port->base_address = (uint32_t)AddrTranslateP_getLocalAddr(
        CONFIG_MCAN0_BASE_ADDR);

    MCAN_initOperModeParams(&init_params);
    init_params.fdMode = TRUE;
    init_params.brsEnable = TRUE;

    MCAN_initGlobalFilterConfigParams(&config_params);
    config_params.filterConfig.anfs = 2u;
    config_params.filterConfig.anfe = 2u;

    bit_times.nomRatePrescalar = 7u;
    bit_times.nomTimeSeg1 = 15u;
    bit_times.nomTimeSeg2 = 2u;
    bit_times.nomSynchJumpWidth = 0u;
    bit_times.dataRatePrescalar = 3u;
    bit_times.dataTimeSeg1 = 5u;
    bit_times.dataTimeSeg2 = 0u;
    bit_times.dataSynchJumpWidth = 0u;

    init_message_ram(&ram_params);
    if (MCAN_calcMsgRamParamsStartAddr(&ram_params) != 0) {
        return -2;
    }

    filter.sfid1 = RLS_RADAR_CAN_CARRIER_TO_AWR_ID;
    filter.sfid2 = RLS_MCAN_SERVICE_RX_BUFFER;
    filter.sfec = MCAN_STD_FILT_ELEM_BUFFER;
    filter.sft = MCAN_STD_FILT_TYPE_RANGE;

    while (MCAN_isMemInitDone(port->base_address) == FALSE) {
    }
    MCAN_setOpMode(port->base_address, MCAN_OPERATION_MODE_SW_INIT);
    while (MCAN_getOpMode(port->base_address) != MCAN_OPERATION_MODE_SW_INIT) {
    }

    if (MCAN_init(port->base_address, &init_params) != 0
        || MCAN_config(port->base_address, &config_params) != 0
        || MCAN_setBitTime(port->base_address, &bit_times) != 0
        || MCAN_msgRAMConfig(port->base_address, &ram_params) != 0) {
        return -3;
    }
    MCAN_addStdMsgIDFilter(port->base_address, 0u, &filter);
    MCAN_setExtIDAndMask(port->base_address, 0x1fffffffu);
    MCAN_setOpMode(port->base_address, MCAN_OPERATION_MODE_NORMAL);
    while (MCAN_getOpMode(port->base_address) != MCAN_OPERATION_MODE_NORMAL) {
    }

    port->initialized = true;
    return 0;
}

int rls_observer_mcan_send(
    rls_observer_mcan_port_t *port,
    uint32_t standard_id,
    uint32_t buffer_number,
    const uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE])
{
    if (port == NULL || wire == NULL || !port->initialized
        || standard_id > RLS_MCAN_STD_ID_MASK
        || buffer_number > RLS_MCAN_SERVICE_TX_BUFFER) {
        return -1;
    }
    if ((MCAN_getTxBufReqPend(port->base_address)
            & (1u << buffer_number)) != 0u) {
        port->dropped_transmissions++;
        return 1;
    }

    MCAN_TxBufElement tx = {0};
    MCAN_initTxBufElement(&tx);
    tx.id = (standard_id & RLS_MCAN_STD_ID_MASK) << RLS_MCAN_STD_ID_SHIFT;
    tx.dlc = MCAN_DATA_SIZE_64BYTES;
    tx.brs = TRUE;
    tx.fdf = TRUE;
    tx.efc = FALSE;
    memcpy(tx.data, wire, RLS_RADAR_LINK_WIRE_SIZE);
    MCAN_writeMsgRam(
        port->base_address,
        MCAN_MEM_TYPE_BUF,
        buffer_number,
        &tx);
    if (MCAN_txBufAddReq(port->base_address, buffer_number) != 0) {
        port->dropped_transmissions++;
        return -2;
    }
    port->transmitted_frames++;
    return 0;
}

int rls_observer_mcan_receive_service(
    rls_observer_mcan_port_t *port,
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE])
{
    if (port == NULL || wire == NULL || !port->initialized) {
        return -1;
    }

    MCAN_RxNewDataStatus status = {0};
    MCAN_getNewDataStatus(port->base_address, &status);
    if ((status.statusLow & 1u) == 0u) {
        return 0;
    }

    MCAN_RxBufElement rx = {0};
    MCAN_readMsgRam(
        port->base_address,
        MCAN_MEM_TYPE_BUF,
        RLS_MCAN_SERVICE_RX_BUFFER,
        MCAN_RX_FIFO_NUM_0,
        &rx);
    MCAN_clearNewDataStatus(port->base_address, &status);

    const uint32_t id = (rx.id >> RLS_MCAN_STD_ID_SHIFT)
        & RLS_MCAN_STD_ID_MASK;
    if (id != RLS_RADAR_CAN_CARRIER_TO_AWR_ID
        || rx.xtd != FALSE
        || rx.rtr != FALSE
        || rx.fdf != TRUE
        || rx.brs != TRUE
        || rx.dlc != MCAN_DATA_SIZE_64BYTES) {
        port->rejected_receptions++;
        return -2;
    }
    memcpy(wire, rx.data, RLS_RADAR_LINK_WIRE_SIZE);
    port->received_frames++;
    return 1;
}

void rls_observer_mcan_service_bus(
    rls_observer_mcan_port_t *port,
    uint64_t timestamp_us)
{
    if (port == NULL || !port->initialized) {
        return;
    }
    MCAN_ProtocolStatus status = {0};
    MCAN_getProtocolStatus(port->base_address, &status);
    if (status.busOffStatus != 0u) {
        if (!port->bus_off_active) {
            port->bus_off_active = true;
            port->bus_off_since_us = timestamp_us;
            port->bus_off_count++;
        } else if (timestamp_us - port->bus_off_since_us
                >= RLS_MCAN_BUS_OFF_RECOVERY_US) {
            MCAN_setOpMode(port->base_address, MCAN_OPERATION_MODE_NORMAL);
        }
        return;
    }
    if (port->bus_off_active) {
        port->bus_off_active = false;
        port->recovered_event = true;
    }
}

bool rls_observer_mcan_take_recovered_event(
    rls_observer_mcan_port_t *port)
{
    if (port == NULL) {
        return false;
    }
    const bool recovered = port->recovered_event;
    port->recovered_event = false;
    return recovered;
}

void rls_observer_mcan_reset_statistics(
    rls_observer_mcan_port_t *port)
{
    if (port == NULL) {
        return;
    }
    port->transmitted_frames = 0u;
    port->received_frames = 0u;
    port->dropped_transmissions = 0u;
    port->rejected_receptions = 0u;
    port->bus_off_count = 0u;
}
