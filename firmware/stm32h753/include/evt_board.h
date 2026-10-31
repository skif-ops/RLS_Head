#ifndef EVT_BOARD_H
#define EVT_BOARD_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "stm32h7xx_hal.h"

#define EVT_RADAR_CAN_RX_ID 0x320u
#define EVT_RADAR_CAN_TX_ID 0x321u
#define EVT_HOST_BAUD_RATE 921600u
#define EVT_GNSS_BAUD_RATE 115200u

enum {
    EVT_CAPTURE_GNSS_PPS = 0,
    EVT_CAPTURE_RADAR_REF = 1,
    EVT_CAPTURE_IMU_DRDY = 2,
    EVT_CAPTURE_COUNT = 3,
};

enum {
    EVT_INIT_CLOCK = 1u << 0,
    EVT_INIT_GPIO = 1u << 1,
    EVT_INIT_DMA = 1u << 2,
    EVT_INIT_TIMER = 1u << 3,
    EVT_INIT_UART = 1u << 4,
    EVT_INIT_SPI = 1u << 5,
    EVT_INIT_FDCAN = 1u << 6,
    EVT_INIT_WATCHDOG = 1u << 7,
};

typedef struct {
    uint64_t timestamp_us[EVT_CAPTURE_COUNT];
    uint32_t sequence[EVT_CAPTURE_COUNT];
} evt_capture_snapshot_t;

extern TIM_HandleTypeDef htim2;
extern SPI_HandleTypeDef hspi2;
extern FDCAN_HandleTypeDef hfdcan1;
extern UART_HandleTypeDef huart1;
extern UART_HandleTypeDef huart2;
extern UART_HandleTypeDef huart3;
extern DMA_HandleTypeDef hdma_usart1_tx;
extern DMA_HandleTypeDef hdma_usart2_tx;
extern DMA_HandleTypeDef hdma_usart3_rx;
extern DMA_HandleTypeDef hdma_spi2_rx;
extern DMA_HandleTypeDef hdma_spi2_tx;

uint32_t evt_board_initialize(void);
void evt_board_service(void);
void evt_board_watchdog_refresh(void);
uint64_t evt_board_time_us(void);
void evt_board_capture_snapshot(evt_capture_snapshot_t *snapshot);
uint32_t evt_board_power_fault_flags(void);

bool evt_board_can_receive(uint8_t frame[64]);
bool evt_board_can_transmit(const uint8_t frame[64]);
uint32_t evt_board_can_bus_off_count(void);

size_t evt_board_gnss_read(uint8_t *destination, size_t capacity);
uint32_t evt_board_gnss_overflow_count(void);

bool evt_board_host_publish(const uint8_t *packet, size_t length);
uint32_t evt_board_host_drop_count(unsigned channel);

bool evt_board_imu_read_register(uint8_t reg, uint8_t *value);
bool evt_board_imu_write_register(uint8_t reg, uint8_t value);
bool evt_board_imu_start_burst(void);
bool evt_board_imu_take_burst(uint8_t burst[14], bool *success);

void evt_board_fatal(uint32_t code);

#endif
