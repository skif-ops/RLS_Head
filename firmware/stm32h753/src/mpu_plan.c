#include "stm32h753_memory.h"

#define ALIGNED_TO_SIZE(base, size) (((base) & ((size) - 1u)) == 0u)

_Static_assert(ALIGNED_TO_SIZE(STM32H753_ITCM_BASE, STM32H753_ITCM_SIZE),
               "ITCM base must align to region size");
_Static_assert(ALIGNED_TO_SIZE(STM32H753_DTCM_BASE, STM32H753_DTCM_SIZE),
               "DTCM base must align to region size");
_Static_assert(ALIGNED_TO_SIZE(STM32H753_AXI_BASE, STM32H753_AXI_SIZE),
               "AXI SRAM base must align to region size");
_Static_assert(ALIGNED_TO_SIZE(STM32H753_SRAM1_BASE, STM32H753_SRAM1_SIZE),
               "SRAM1 base must align to region size");
_Static_assert(ALIGNED_TO_SIZE(STM32H753_SRAM2_BASE, STM32H753_SRAM2_SIZE),
               "SRAM2 base must align to region size");
_Static_assert(ALIGNED_TO_SIZE(STM32H753_SRAM3_BASE, STM32H753_SRAM3_SIZE),
               "SRAM3 base must align to region size");
_Static_assert(ALIGNED_TO_SIZE(STM32H753_SRAM4_BASE, STM32H753_SRAM4_SIZE),
               "SRAM4 base must align to region size");

const MpuRegionPlan g_stm32h753_mpu_plan[] = {
    {
        "ITCM",
        STM32H753_ITCM_BASE,
        STM32H753_ITCM_SIZE,
        MPU_PLAN_TCM,
        1u,
        0u,
        0u
    },
    {
        "DTCM",
        STM32H753_DTCM_BASE,
        STM32H753_DTCM_SIZE,
        MPU_PLAN_TCM,
        0u,
        0u,
        0u
    },
    {
        "AXI_SRAM",
        STM32H753_AXI_BASE,
        STM32H753_AXI_SIZE,
        MPU_PLAN_NORMAL_CACHEABLE,
        0u,
        0u,
        0u
    },
    {
        "SRAM1_DMA_RX",
        STM32H753_SRAM1_BASE,
        STM32H753_SRAM1_SIZE,
        MPU_PLAN_NORMAL_NONCACHEABLE,
        0u,
        1u,
        1u
    },
    {
        "SRAM2_DMA_TX",
        STM32H753_SRAM2_BASE,
        STM32H753_SRAM2_SIZE,
        MPU_PLAN_NORMAL_NONCACHEABLE,
        0u,
        1u,
        1u
    },
    {
        "SRAM3_ETH",
        STM32H753_SRAM3_BASE,
        STM32H753_SRAM3_SIZE,
        MPU_PLAN_NORMAL_NONCACHEABLE,
        0u,
        1u,
        1u
    },
    {
        "SRAM4_STATUS",
        STM32H753_SRAM4_BASE,
        STM32H753_SRAM4_SIZE,
        MPU_PLAN_NORMAL_NONCACHEABLE,
        0u,
        1u,
        0u
    }
};

const size_t g_stm32h753_mpu_plan_count =
    sizeof(g_stm32h753_mpu_plan) / sizeof(g_stm32h753_mpu_plan[0]);
