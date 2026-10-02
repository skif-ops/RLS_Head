cmake_minimum_required(VERSION 3.20)
project(rls_head_hil_r1 C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

option(HIL_BUILD_HOST_TESTS "Build host-native HIL-R1 golden tests" ON)
option(HIL_BUILD_STM32H753_SMOKE "Build STM32H753 cross-link smoke target" OFF)

add_library(hil_r1 STATIC
    src/hil_r1.c
)

add_library(hil_r2 STATIC
    src/hil_r2.c
)

target_include_directories(hil_r1 PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(hil_r2 PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

if(MSVC)
    target_compile_options(hil_r1 PRIVATE /W4 /WX)
    target_compile_options(hil_r2 PRIVATE /W4 /WX)
else()
    target_compile_options(hil_r1 PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(hil_r2 PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(hil_r1 PUBLIC m)
    target_link_libraries(hil_r2 PUBLIC m)
endif()

if(HIL_BUILD_HOST_TESTS AND NOT CMAKE_CROSSCOMPILING)
    enable_testing()

    add_executable(test_hil_r1
        tests/test_hil_r1.c
    )

    target_link_libraries(test_hil_r1 PRIVATE hil_r1)

    if(MSVC)
        target_compile_options(test_hil_r1 PRIVATE /W4 /WX)
    else()
        target_compile_options(test_hil_r1 PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME hil_r1_golden COMMAND test_hil_r1)

    add_executable(test_hil_r2
        tests/test_hil_r2.c
    )

    target_link_libraries(test_hil_r2 PRIVATE hil_r2)

    if(MSVC)
        target_compile_options(test_hil_r2 PRIVATE /W4 /WX)
    else()
        target_compile_options(test_hil_r2 PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME hil_r2_deterministic COMMAND test_hil_r2)
endif()

if(HIL_BUILD_STM32H753_SMOKE)
    if(NOT CMAKE_CROSSCOMPILING)
        message(FATAL_ERROR "HIL_BUILD_STM32H753_SMOKE requires the ARM cross toolchain")
    endif()

    add_executable(stm32h753_link_smoke
        firmware/stm32h753/startup/link_smoke_startup.S
        firmware/stm32h753/src/link_smoke_main.c
        firmware/stm32h753/src/mpu_plan.c
    )

    set_target_properties(stm32h753_link_smoke PROPERTIES
        SUFFIX ".elf"
    )

    target_include_directories(stm32h753_link_smoke PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/firmware/stm32h753/include
    )

    target_compile_options(stm32h753_link_smoke PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -Werror
    )

    target_link_libraries(stm32h753_link_smoke PRIVATE
        hil_r1
        hil_r2
        c
        nosys
    )

    target_link_options(stm32h753_link_smoke PRIVATE
        -nostartfiles
        -Wl,--gc-sections
        -Wl,--print-memory-usage
        -Wl,-Map=${CMAKE_BINARY_DIR}/stm32h753_link_smoke.map
        -T${CMAKE_CURRENT_SOURCE_DIR}/firmware/stm32h753/linker/STM32H753IIT6_LINK_SMOKE.ld
    )

    if(CMAKE_SIZE)
        add_custom_command(
            TARGET stm32h753_link_smoke
            POST_BUILD
            COMMAND ${CMAKE_SIZE} $<TARGET_FILE:stm32h753_link_smoke>
            VERBATIM
        )
    endif()
endif()
