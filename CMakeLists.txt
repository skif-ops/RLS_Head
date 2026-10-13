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

add_library(sys_err STATIC
    src/sys_err.c
)

add_library(targetstate_uncertainty STATIC
    src/targetstate_uncertainty.c
)

add_library(targetstate_error_ledger STATIC
    src/targetstate_error_ledger.c
)

add_library(hil_r2_evidence STATIC
    src/hil_r2_evidence.c
)

add_library(time_service STATIC
    src/time_service.c
)

add_library(radar_link STATIC
    src/radar_link.c
)

add_library(carrier_health STATIC
    src/carrier_health.c
)

add_library(measurement_session STATIC
    src/measurement_session.c
)

add_library(evidence_export STATIC
    src/evidence_export.c
)

add_library(capture_router STATIC
    src/capture_router.c
)

add_library(ethernet_reset STATIC
    src/ethernet_reset.c
)

add_library(config_lock STATIC
    src/config_lock.c
)

target_include_directories(hil_r1 PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(hil_r2 PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(sys_err PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(targetstate_uncertainty PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(targetstate_error_ledger PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(hil_r2_evidence PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(time_service PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(radar_link PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(carrier_health PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(measurement_session PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(evidence_export PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(capture_router PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(ethernet_reset PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_include_directories(config_lock PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

if(MSVC)
    target_compile_options(hil_r1 PRIVATE /W4 /WX)
    target_compile_options(hil_r2 PRIVATE /W4 /WX)
    target_compile_options(sys_err PRIVATE /W4 /WX)
    target_compile_options(targetstate_uncertainty PRIVATE /W4 /WX)
    target_compile_options(targetstate_error_ledger PRIVATE /W4 /WX)
    target_compile_options(hil_r2_evidence PRIVATE /W4 /WX)
    target_compile_options(time_service PRIVATE /W4 /WX)
    target_compile_options(radar_link PRIVATE /W4 /WX)
    target_compile_options(carrier_health PRIVATE /W4 /WX)
    target_compile_options(measurement_session PRIVATE /W4 /WX)
    target_compile_options(evidence_export PRIVATE /W4 /WX)
    target_compile_options(capture_router PRIVATE /W4 /WX)
    target_compile_options(ethernet_reset PRIVATE /W4 /WX)
    target_compile_options(config_lock PRIVATE /W4 /WX)
else()
    target_compile_options(hil_r1 PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(hil_r2 PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(sys_err PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(targetstate_uncertainty PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(targetstate_error_ledger PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(hil_r2_evidence PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(time_service PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(radar_link PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(carrier_health PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(measurement_session PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(evidence_export PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(capture_router PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(ethernet_reset PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_compile_options(config_lock PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(hil_r1 PUBLIC m)
    target_link_libraries(hil_r2 PUBLIC m)
endif()

target_link_libraries(sys_err PUBLIC hil_r2)
target_link_libraries(targetstate_uncertainty PUBLIC hil_r1 sys_err)
target_link_libraries(targetstate_error_ledger PUBLIC targetstate_uncertainty)
target_link_libraries(hil_r2_evidence PUBLIC m)
target_link_libraries(evidence_export PUBLIC measurement_session time_service carrier_health)

if(NOT MSVC)
    target_link_libraries(time_service PUBLIC m)
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

    add_executable(test_sys_err
        tests/test_sys_err.c
    )

    target_link_libraries(test_sys_err PRIVATE sys_err)

    if(MSVC)
        target_compile_options(test_sys_err PRIVATE /W4 /WX)
    else()
        target_compile_options(test_sys_err PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME sys_err_covariance COMMAND test_sys_err)

    add_executable(test_targetstate_uncertainty
        tests/test_targetstate_uncertainty.c
    )

    target_link_libraries(test_targetstate_uncertainty PRIVATE targetstate_uncertainty)

    if(MSVC)
        target_compile_options(test_targetstate_uncertainty PRIVATE /W4 /WX)
    else()
        target_compile_options(test_targetstate_uncertainty PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME targetstate_syserr COMMAND test_targetstate_uncertainty)

    add_executable(test_targetstate_error_ledger
        tests/test_targetstate_error_ledger.c
    )

    target_link_libraries(test_targetstate_error_ledger PRIVATE targetstate_error_ledger)

    if(MSVC)
        target_compile_options(test_targetstate_error_ledger PRIVATE /W4 /WX)
    else()
        target_compile_options(test_targetstate_error_ledger PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME targetstate_error_ledger COMMAND test_targetstate_error_ledger)

    add_executable(test_hil_r2_evidence
        tests/test_hil_r2_evidence.c
    )

    target_link_libraries(test_hil_r2_evidence PRIVATE hil_r2_evidence)

    if(MSVC)
        target_compile_options(test_hil_r2_evidence PRIVATE /W4 /WX)
    else()
        target_compile_options(test_hil_r2_evidence PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME hil_r2_runtime_evidence COMMAND test_hil_r2_evidence)

    add_executable(test_time_service
        tests/test_time_service.c
    )

    target_link_libraries(test_time_service PRIVATE time_service)

    if(MSVC)
        target_compile_options(test_time_service PRIVATE /W4 /WX)
    else()
        target_compile_options(test_time_service PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME time_service_discipline COMMAND test_time_service)

    add_executable(test_radar_link
        tests/test_radar_link.c
    )

    target_link_libraries(test_radar_link PRIVATE radar_link)

    if(MSVC)
        target_compile_options(test_radar_link PRIVATE /W4 /WX)
    else()
        target_compile_options(test_radar_link PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME radar_link_wire COMMAND test_radar_link)

    add_executable(test_carrier_health
        tests/test_carrier_health.c
    )

    target_link_libraries(test_carrier_health PRIVATE carrier_health)

    if(MSVC)
        target_compile_options(test_carrier_health PRIVATE /W4 /WX)
    else()
        target_compile_options(test_carrier_health PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME carrier_health_logic COMMAND test_carrier_health)

    add_executable(test_measurement_session
        tests/test_measurement_session.c
    )

    target_link_libraries(test_measurement_session PRIVATE measurement_session)

    if(MSVC)
        target_compile_options(test_measurement_session PRIVATE /W4 /WX)
    else()
        target_compile_options(test_measurement_session PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME measurement_session_logic COMMAND test_measurement_session)

    add_executable(test_evidence_export
        tests/test_evidence_export.c
    )

    target_link_libraries(test_evidence_export PRIVATE evidence_export)

    if(MSVC)
        target_compile_options(test_evidence_export PRIVATE /W4 /WX)
    else()
        target_compile_options(test_evidence_export PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME carrier_evidence_export COMMAND test_evidence_export)

    add_executable(test_capture_router
        tests/test_capture_router.c
    )

    target_link_libraries(test_capture_router PRIVATE capture_router)

    if(MSVC)
        target_compile_options(test_capture_router PRIVATE /W4 /WX)
    else()
        target_compile_options(test_capture_router PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME carrier_capture_router COMMAND test_capture_router)

    add_executable(test_ethernet_reset
        tests/test_ethernet_reset.c
    )

    target_link_libraries(test_ethernet_reset PRIVATE ethernet_reset)

    if(MSVC)
        target_compile_options(test_ethernet_reset PRIVATE /W4 /WX)
    else()
        target_compile_options(test_ethernet_reset PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME carrier_ethernet_reset COMMAND test_ethernet_reset)

    add_executable(test_config_lock
        tests/test_config_lock.c
    )

    target_link_libraries(test_config_lock PRIVATE config_lock)

    if(MSVC)
        target_compile_options(test_config_lock PRIVATE /W4 /WX)
    else()
        target_compile_options(test_config_lock PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME carrier_config_lock COMMAND test_config_lock)
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
        sys_err
        targetstate_uncertainty
        targetstate_error_ledger
        hil_r2_evidence
        time_service
        radar_link
        carrier_health
        measurement_session
        evidence_export
        capture_router
        ethernet_reset
        config_lock
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
