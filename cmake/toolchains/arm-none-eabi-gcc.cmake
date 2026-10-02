set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

find_program(CMAKE_C_COMPILER arm-none-eabi-gcc REQUIRED)
find_program(CMAKE_ASM_COMPILER arm-none-eabi-gcc REQUIRED)
find_program(CMAKE_OBJCOPY arm-none-eabi-objcopy REQUIRED)
find_program(CMAKE_SIZE arm-none-eabi-size REQUIRED)

set(STM32_CPU_FLAGS
    "-mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard"
    CACHE STRING "STM32H753 Cortex-M7 compiler flags")

set(CMAKE_C_FLAGS_INIT
    "${STM32_CPU_FLAGS} -ffunction-sections -fdata-sections -fno-common")

set(CMAKE_ASM_FLAGS_INIT
    "${STM32_CPU_FLAGS} -x assembler-with-cpp")
