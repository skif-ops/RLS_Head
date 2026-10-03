#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

int main(void);

void Default_Handler(void)
{
    for (;;) {
    }
}

void Reset_Handler(void)
{
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;

    while (dst < &_edata) {
        *dst++ = *src++;
    }

    dst = &_sbss;

    while (dst < &_ebss) {
        *dst++ = 0u;
    }

    (void)main();

    for (;;) {
    }
}

__attribute__((section(".isr_vector")))
const uintptr_t vector_table[] = {
    (uintptr_t)&_estack,
    (uintptr_t)Reset_Handler,
    (uintptr_t)Default_Handler,
    (uintptr_t)Default_Handler,
    (uintptr_t)Default_Handler,
    (uintptr_t)Default_Handler,
    (uintptr_t)Default_Handler,
    0u,
    0u,
    0u,
    0u,
    (uintptr_t)Default_Handler,
    (uintptr_t)Default_Handler,
    0u,
    (uintptr_t)Default_Handler,
    (uintptr_t)Default_Handler
};
