ENTRY(Reset_Handler)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 2048K
    ITCM  (xrw) : ORIGIN = 0x00000000, LENGTH = 64K
    DTCM  (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
    AXISRAM (xrw) : ORIGIN = 0x24000000, LENGTH = 512K
    SRAM1 (xrw) : ORIGIN = 0x30000000, LENGTH = 128K
    SRAM2 (xrw) : ORIGIN = 0x30020000, LENGTH = 128K
    SRAM3 (xrw) : ORIGIN = 0x30040000, LENGTH = 32K
    SRAM4 (xrw) : ORIGIN = 0x38000000, LENGTH = 64K
}

_estack = ORIGIN(DTCM) + LENGTH(DTCM);

SECTIONS
{
    .isr_vector :
    {
        KEEP(*(.isr_vector))
    } > FLASH

    .text :
    {
        *(.text*)
        *(.rodata*)
        KEEP(*(.init))
        KEEP(*(.fini))
    } > FLASH

    .itcm_text :
    {
        *(.itcm_text*)
    } > ITCM AT > FLASH

    .data :
    {
        _sdata = .;
        *(.data*)
        _edata = .;
    } > DTCM AT > FLASH

    _sidata = LOADADDR(.data);

    .dtcm_data (NOLOAD) :
    {
        *(.dtcm_data*)
    } > DTCM

    .axi_data (NOLOAD) :
    {
        *(.axi_data*)
        *(.axi_bss*)
    } > AXISRAM

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

    .eth_buf (NOLOAD) :
    {
        . = ALIGN(32);
        *(.eth_buf*)
        . = ALIGN(32);
    } > SRAM3

    .sram4_status (NOLOAD) :
    {
        *(.sram4_status*)
    } > SRAM4

    .bss (NOLOAD) :
    {
        _sbss = .;
        *(.bss*)
        *(COMMON)
        _ebss = .;
    } > DTCM

    . = ALIGN(8);
    _end = .;
}
