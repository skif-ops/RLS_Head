#pragma once

#include <stddef.h>
#include <stdint.h>

#define STM32H753_FLASH_BASE   0x08000000u
#define STM32H753_FLASH_SIZE   (2u * 1024u * 1024u)

#define STM32H753_ITCM_BASE    0x00000000u
#define STM32H753_ITCM_SIZE    (64u * 1024u)

#define STM32H753_DTCM_BASE    0x20000000u
#define STM32H753_DTCM_SIZE    (128u * 1024u)

#define STM32H753_AXI_BASE     0x24000000u
#define STM32H753_AXI_SIZE     (512u * 1024u)

#define STM32H753_SRAM1_BASE   0x30000000u
#define STM32H753_SRAM1_SIZE   (128u * 1024u)

#define STM32H753_SRAM2_BASE   0x30020000u
#define STM32H753_SRAM2_SIZE   (128u * 1024u)

#define STM32H753_SRAM3_BASE   0x30040000u
#define STM32H753_SRAM3_SIZE   (32u * 1024u)

#define STM32H753_SRAM4_BASE   0x38000000u
#define STM32H753_SRAM4_SIZE   (64u * 1024u)

typedef enum {
    MPU_PLAN_NORMAL_CACHEABLE = 0,
    MPU_PLAN_NORMAL_NONCACHEABLE,
    MPU_PLAN_TCM
} MpuPlanMemoryType;

typedef struct {
    const char *name;
    uint32_t base;
    uint32_t size;
    MpuPlanMemoryType memory_type;
    uint8_t executable;
    uint8_t shareable;
    uint8_t dma_owned;
} MpuRegionPlan;

extern const MpuRegionPlan g_stm32h753_mpu_plan[];
extern const size_t g_stm32h753_mpu_plan_count;
