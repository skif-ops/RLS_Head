ENTRY(Reset_Handler)

_Min_Stack_Size = 0x4000;

MEMORY
{
    FLASH  (rx)  : ORIGIN = 0x08000000, LENGTH = 2048K
    DTCM   (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
    AXI    (xrw) : ORIGIN = 0x24000000, LENGTH = 512K
    SRAM1  (xrw) : ORIGIN = 0x30000000, LENGTH = 128K
    SRAM2  (xrw) : ORIGIN = 0x30020000, LENGTH = 128K
    SRAM4  (xrw) : ORIGIN = 0x38000000, LENGTH = 64K
}

_estack = ORIGIN(DTCM) + LENGTH(DTCM);

SECTIONS
{
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector))
        . = ALIGN(4);
    } > FLASH

    .text :
    {
        . = ALIGN(4);
        *(.text*)
        *(.rodata*)
        KEEP(*(.init))
        KEEP(*(.fini))
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    .ARM.extab :
    {
        *(.ARM.extab* .gnu.linkonce.armextab.*)
    } > FLASH

    .ARM.exidx :
    {
        __exidx_start = .;
        *(.ARM.exidx*)
        __exidx_end = .;
    } > FLASH

    .preinit_array :
    {
        PROVIDE_HIDDEN(__preinit_array_start = .);
        KEEP(*(.preinit_array*))
        PROVIDE_HIDDEN(__preinit_array_end = .);
    } > FLASH

    .init_array :
    {
        PROVIDE_HIDDEN(__init_array_start = .);
        KEEP(*(SORT(.init_array.*)))
        KEEP(*(.init_array*))
        PROVIDE_HIDDEN(__init_array_end = .);
    } > FLASH

    .fini_array :
    {
        PROVIDE_HIDDEN(__fini_array_start = .);
        KEEP(*(SORT(.fini_array.*)))
        KEEP(*(.fini_array*))
        PROVIDE_HIDDEN(__fini_array_end = .);
    } > FLASH

    _sidata = LOADADDR(.data);
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > AXI AT > FLASH

    .bss (NOLOAD) :
    {
        . = ALIGN(8);
        _sbss = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(8);
        _ebss = .;
    } > AXI

    .dma_rx (NOLOAD) :
    {
        . = ALIGN(32);
        *(.dma_rx*)
        . = ALIGN(32);
    } > SRAM1

    .dma_tx (NOLOAD) :
    {
        . = ALIGN(32);
        *(.dma_tx*)
        . = ALIGN(32);
    } > SRAM2

    .sram4_status (NOLOAD) :
    {
        . = ALIGN(32);
        *(.sram4_status*)
        . = ALIGN(32);
    } > SRAM4

    .stack (NOLOAD) :
    {
        . = ALIGN(8);
        _sstack = .;
        . = . + _Min_Stack_Size;
        . = ALIGN(8);
        _estack_reserve = .;
    } > DTCM

    .ARM.attributes 0 : { *(.ARM.attributes) }

    /DISCARD/ :
    {
        *(.note*)
        *(.comment*)
    }
}

ASSERT(SIZEOF(.isr_vector) >= 0x200, "STM32H753 vector table is incomplete")
ASSERT(SIZEOF(.stack) <= LENGTH(DTCM), "DTCM stack reserve overflow")
ASSERT(SIZEOF(.dma_rx) <= LENGTH(SRAM1), "DMA RX memory overflow")
ASSERT(SIZEOF(.dma_tx) <= LENGTH(SRAM2), "DMA TX memory overflow")
