#include "rls/hil_r1.h"
#include "stm32h753_memory.h"

#include <stdint.h>

volatile uint32_t g_stm32h753_link_smoke_sink;

int main(void)
{
    HilRuntime runtime;

    hil_runtime_init(
        &runtime,
        0x524C5301u,
        0x00000001u);

    g_stm32h753_link_smoke_sink =
        runtime.boot_id ^
        runtime.source_id ^
        (uint32_t)g_stm32h753_mpu_plan_count;

    for (;;) {
        __asm volatile ("wfi");
    }
}
