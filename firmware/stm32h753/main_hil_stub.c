#include "rls/hil_r1.h"

#include <stdint.h>

__attribute__((section(".sram4_status")))
static volatile uint32_t g_hil_build_marker = 0x48375231u; /* H7R1 */

__attribute__((section(".dma_rx"), aligned(32)))
static uint8_t g_hil_rx[HIL_HEADER_WIRE_SIZE + HIL_DETECTION_WIRE_SIZE + HIL_CRC_WIRE_SIZE];

__attribute__((section(".dma_tx"), aligned(32)))
static uint8_t g_hil_tx[TARGETSTATE_PACKET_SIZE];

int main(void)
{
    HilRuntime runtime;
    hil_runtime_init(&runtime, 1u, 1u);

    g_hil_build_marker ^= runtime.boot_id;
    g_hil_rx[0] = 0u;
    g_hil_tx[0] = 0u;

    for (;;) {
        __asm volatile ("nop");
    }
}
