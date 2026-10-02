.syntax unified
.cpu cortex-m7
.fpu fpv5-d16
.thumb

.global Reset_Handler
.global Default_Handler

.extern main
.extern _estack
.extern _sidata
.extern _sdata
.extern _edata
.extern _sbss
.extern _ebss
.extern _sitcm_load
.extern _sitcm_start
.extern _sitcm_end
.extern _sdtcm_load
.extern _sdtcm_start
.extern _sdtcm_end

.section .isr_vector,"a",%progbits
.type g_pfnVectors, %object

g_pfnVectors:
    .word _estack
    .word Reset_Handler
    .rept 14
    .word Default_Handler
    .endr

.size g_pfnVectors, .-g_pfnVectors

.section .text.Reset_Handler,"ax",%progbits
.thumb_func
.type Reset_Handler, %function

Reset_Handler:
    /* Copy .data from FLASH to AXI SRAM. */
    ldr r0, =_sidata
    ldr r1, =_sdata
    ldr r2, =_edata
1:
    cmp r1, r2
    bcs 2f
    ldr r3, [r0], #4
    str r3, [r1], #4
    b 1b

2:
    /* Copy optional ITCM text. */
    ldr r0, =_sitcm_load
    ldr r1, =_sitcm_start
    ldr r2, =_sitcm_end
3:
    cmp r1, r2
    bcs 4f
    ldr r3, [r0], #4
    str r3, [r1], #4
    b 3b

4:
    /* Copy optional DTCM initialized data. */
    ldr r0, =_sdtcm_load
    ldr r1, =_sdtcm_start
    ldr r2, =_sdtcm_end
5:
    cmp r1, r2
    bcs 6f
    ldr r3, [r0], #4
    str r3, [r1], #4
    b 5b

6:
    /* Clear AXI .bss. */
    movs r0, #0
    ldr r1, =_sbss
    ldr r2, =_ebss
7:
    cmp r1, r2
    bcs 8f
    str r0, [r1], #4
    b 7b

8:
    bl main

9:
    b 9b

.size Reset_Handler, .-Reset_Handler

.section .text.Default_Handler,"ax",%progbits
.thumb_func
.type Default_Handler, %function

Default_Handler:
    b Default_Handler

.size Default_Handler, .-Default_Handler
