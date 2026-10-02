cmake_minimum_required(VERSION 3.20)
project(rls_head_hil_r1 C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

add_library(hil_r1 STATIC
    src/hil_r1.c
)

target_include_directories(hil_r1 PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

if(MSVC)
    target_compile_options(hil_r1 PRIVATE /W4 /WX)
else()
    target_compile_options(hil_r1 PRIVATE -Wall -Wextra -Wpedantic -Werror)
    target_link_libraries(hil_r1 PUBLIC m)
endif()

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
