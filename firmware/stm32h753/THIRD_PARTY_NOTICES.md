# Third-party firmware components

The EVT carrier firmware vendors the minimum STM32CubeH7 files needed to build
the STM32H753 target without requiring STM32CubeIDE.

| Component | Upstream | Pinned revision |
|---|---|---|
| STM32CubeH7 package | https://github.com/STMicroelectronics/STM32CubeH7 | `5abb9764b32e11a6557b90bf39531528019b5761` (`v1.13.0`) |
| CMSIS device support for STM32H7 | https://github.com/STMicroelectronics/cmsis_device_h7 | `8f922cdc7cc6de2344e75ddd657889f4ff761790` |
| STM32H7 HAL driver | https://github.com/STMicroelectronics/stm32h7xx_hal_driver | `a1996eed9172b59887bafaaa0ea1816ea14d48b5` |

The original license files are retained beside the vendored sources. The
project-specific application code remains separate under `include/` and
`src/`.
