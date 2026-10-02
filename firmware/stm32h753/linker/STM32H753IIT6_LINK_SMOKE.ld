ENTRY(Reset_Handler)

MEMORY
{
    FLASH  (rx)  : ORIGIN = 0x08000000, LENGTH = 2048K
    ITCM   (xrw) : ORIGIN = 0x00000000, LENGTH = 64K
    DTCM   (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
    AXI    (xrw) : ORIGIN = 0x24000000, LENGTH = 512K
    SRAM1  (xrw) : ORIGIN = 0x30000000, LENGTH = 128K
    SRAM2  (xrw) : ORIGIN = 0x30020000, LENGTH = 128K
    SRAM3  (xrw) : ORIGIN = 0x30040000, LENGTH = 32K
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

    .itcm_text :
    {
        . = ALIGN(4);
        _sitcm_start = .;
        *(.itcm_text*)
        . = ALIGN(4);
        _sitcm_end = .;
    } > ITCM AT > FLASH
    _sitcm_load = LOADADDR(.itcm_text);

    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > AXI AT > FLASH
    _sidata = LOADADDR(.data);

    .dtcm_data :
    {
        . = ALIGN(4);
        _sdtcm_start = .;
        *(.dtcm_data*)
        . = ALIGN(4);
        _sdtcm_end = .;
    } > DTCM AT > FLASH
    _sdtcm_load = LOADADDR(.dtcm_data);

    .dtcm_bss (NOLOAD) :
    {
        . = ALIGN(8);
        _sdtcm_bss = .;
        *(.dtcm_bss*)
        . = ALIGN(8);
        _edtcm_bss = .;
    } > DTCM

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

    .eth_buffers (NOLOAD) :
    {
        . = ALIGN(32);
        *(.eth_buffers*)
        . = ALIGN(32);
    } > SRAM3

    .sram4_status (NOLOAD) :
    {
        . = ALIGN(32);
        *(.sram4_status*)
        . = ALIGN(32);
    } > SRAM4

    .bss (NOLOAD) :
    {
        . = ALIGN(8);
        _sbss = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(8);
        _ebss = .;
    } > AXI

    .heap_stack (NOLOAD) :
    {
        . = ALIGN(8);
        PROVIDE(end = .);
        PROVIDE(_end = .);
        . = . + 0x0800; /* 2 KiB smoke-only heap reserve */
        . = . + 0x2000; /* 8 KiB smoke-only stack reserve */
        . = ALIGN(8);
    } > DTCM

    /DISCARD/ :
    {
        *(.note*)
        *(.comment*)
    }
}

ASSERT(SIZEOF(.isr_vector) >= 64, "vector table unexpectedly small")
ASSERT(SIZEOF(.heap_stack) <= LENGTH(DTCM), "DTCM reserve overflow")
