#include "rls/hil_r1.h"
#include "stm32h753_memory.h"

#include <stddef.h>
#include <stdint.h>

#define DMA_ALIGN __attribute__((aligned(32)))

static HilRuntime g_hil_runtime
    __attribute__((section(".dtcm_bss"), aligned(8)));

static uint8_t g_hil_request[
    HIL_HEADER_WIRE_SIZE +
    HIL_DETECTION_WIRE_SIZE +
    HIL_CRC_WIRE_SIZE]
    __attribute__((section(".dma_rx"))) DMA_ALIGN;

static uint8_t g_targetstate_response[TARGETSTATE_PACKET_SIZE]
    __attribute__((section(".dma_tx"))) DMA_ALIGN;

static volatile uint32_t g_smoke_status
    __attribute__((section(".sram4_status"), aligned(32)));

static volatile uint32_t g_smoke_response_len
    __attribute__((section(".sram4_status"), aligned(4)));

int main(void)
{
    size_t response_len = 0u;

    hil_runtime_init(
        &g_hil_runtime,
        0x524C5301u,
        0x00000001u);

    /*
     * The request buffer is intentionally not made into a valid frame here.
     * This target is a cross-link/placement gate, not a hardware execution
     * image. Calling the full runtime keeps the production HIL-R1 call graph
     * reachable in the Cortex-M7 ELF so link/memory evidence reflects the
     * actual sensing pipeline.
     */
    const HilRuntimeResult result =
        hil_runtime_process_packet(
            &g_hil_runtime,
            g_hil_request,
            sizeof(g_hil_request),
            1u,
            2u,
            g_targetstate_response,
            sizeof(g_targetstate_response),
            &response_len);

    g_smoke_status =
        (uint32_t)result ^
        (uint32_t)g_stm32h753_mpu_plan_count;

    g_smoke_response_len =
        (uint32_t)response_len;

    for (;;) {
        __asm volatile ("wfi");
    }
}
