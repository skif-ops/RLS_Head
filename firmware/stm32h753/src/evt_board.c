#include "evt_board.h"

#include <string.h>

TIM_HandleTypeDef htim2;
SPI_HandleTypeDef hspi2;
FDCAN_HandleTypeDef hfdcan1;
UART_HandleTypeDef huart1;
UART_HandleTypeDef huart2;
UART_HandleTypeDef huart3;
IWDG_HandleTypeDef hiwdg1;
DMA_HandleTypeDef hdma_usart1_tx;
DMA_HandleTypeDef hdma_usart2_tx;
DMA_HandleTypeDef hdma_usart3_rx;
DMA_HandleTypeDef hdma_spi2_rx;
DMA_HandleTypeDef hdma_spi2_tx;

enum {
    CAN_QUEUE_DEPTH = 8,
    GNSS_RING_SIZE = 1024,
    GNSS_DMA_SIZE = 256,
    HOST_PACKET_CAPACITY = 256,
};

typedef struct {
    uint8_t data[64];
} can_frame_t;

static can_frame_t can_rx_queue[CAN_QUEUE_DEPTH];
static volatile uint8_t can_rx_head;
static volatile uint8_t can_rx_tail;
static volatile uint32_t can_bus_off_count;
static volatile bool can_restart_pending;

static uint8_t gnss_dma_buffer[GNSS_DMA_SIZE]
    __attribute__((section(".dma_rx"), aligned(32)));
static uint8_t gnss_ring[GNSS_RING_SIZE];
static volatile uint16_t gnss_head;
static volatile uint16_t gnss_tail;
static volatile uint32_t gnss_overflow_count;

static uint8_t host1_tx_buffer[HOST_PACKET_CAPACITY]
    __attribute__((section(".dma_tx"), aligned(32)));
static uint8_t host2_tx_buffer[HOST_PACKET_CAPACITY]
    __attribute__((section(".dma_tx"), aligned(32)));
static volatile bool host1_tx_busy;
static volatile bool host2_tx_busy;
static volatile uint32_t host_drop_count[2];

static uint8_t imu_tx_buffer[15]
    __attribute__((section(".dma_tx"), aligned(32)));
static uint8_t imu_rx_buffer[15]
    __attribute__((section(".dma_rx"), aligned(32)));
static volatile bool imu_transfer_active;
static volatile bool imu_transfer_complete;
static volatile bool imu_transfer_success;

static volatile uint32_t timer_overflow_high;
static volatile uint64_t capture_timestamp[EVT_CAPTURE_COUNT];
static volatile uint32_t capture_sequence[EVT_CAPTURE_COUNT];
static volatile uint32_t power_fault_flags;

static bool system_clock_config(void)
{
    RCC_OscInitTypeDef oscillator = {0};
    RCC_ClkInitTypeDef clocks = {0};
    RCC_PeriphCLKInitTypeDef peripheral = {0};

    if (HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY) != HAL_OK) {
        return false;
    }
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);
    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {
    }

    oscillator.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    oscillator.HSEState = RCC_HSE_ON;
    oscillator.PLL.PLLState = RCC_PLL_ON;
    oscillator.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    oscillator.PLL.PLLM = 5u;
    oscillator.PLL.PLLN = 160u;
    oscillator.PLL.PLLP = 2u;
    oscillator.PLL.PLLQ = 4u;
    oscillator.PLL.PLLR = 2u;
    oscillator.PLL.PLLRGE = RCC_PLL1VCIRANGE_2;
    oscillator.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    oscillator.PLL.PLLFRACN = 0u;
    if (HAL_RCC_OscConfig(&oscillator) != HAL_OK) {
        return false;
    }

    clocks.ClockType = RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK
        | RCC_CLOCKTYPE_D1PCLK1 | RCC_CLOCKTYPE_PCLK1
        | RCC_CLOCKTYPE_PCLK2 | RCC_CLOCKTYPE_D3PCLK1;
    clocks.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clocks.SYSCLKDivider = RCC_SYSCLK_DIV1;
    clocks.AHBCLKDivider = RCC_HCLK_DIV2;
    clocks.APB3CLKDivider = RCC_APB3_DIV2;
    clocks.APB1CLKDivider = RCC_APB1_DIV2;
    clocks.APB2CLKDivider = RCC_APB2_DIV2;
    clocks.APB4CLKDivider = RCC_APB4_DIV2;
    if (HAL_RCC_ClockConfig(&clocks, FLASH_LATENCY_4) != HAL_OK) {
        return false;
    }

    peripheral.PeriphClockSelection = RCC_PERIPHCLK_FDCAN
        | RCC_PERIPHCLK_SPI2 | RCC_PERIPHCLK_USART1
        | RCC_PERIPHCLK_USART2 | RCC_PERIPHCLK_USART3;
    peripheral.FdcanClockSelection = RCC_FDCANCLKSOURCE_HSE;
    peripheral.Spi123ClockSelection = RCC_SPI123CLKSOURCE_PLL;
    peripheral.Usart16ClockSelection = RCC_USART16CLKSOURCE_D2PCLK2;
    peripheral.Usart234578ClockSelection = RCC_USART234578CLKSOURCE_D2PCLK1;
    return HAL_RCCEx_PeriphCLKConfig(&peripheral) == HAL_OK;
}

static void gpio_init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;

    gpio.Pin = GPIO_PIN_0;
    gpio.Alternate = GPIO_AF1_TIM2;
    HAL_GPIO_Init(GPIOA, &gpio);

    gpio.Pin = GPIO_PIN_10 | GPIO_PIN_11;
    gpio.Alternate = GPIO_AF1_TIM2;
    HAL_GPIO_Init(GPIOB, &gpio);

    gpio.Pin = GPIO_PIN_13 | GPIO_PIN_14 | GPIO_PIN_15;
    gpio.Alternate = GPIO_AF5_SPI2;
    HAL_GPIO_Init(GPIOB, &gpio);

    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
    gpio.Pin = GPIO_PIN_12;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOB, &gpio);

    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pin = GPIO_PIN_0 | GPIO_PIN_1;
    gpio.Alternate = GPIO_AF9_FDCAN1;
    HAL_GPIO_Init(GPIOD, &gpio);

    gpio.Pin = GPIO_PIN_5 | GPIO_PIN_6 | GPIO_PIN_8 | GPIO_PIN_9;
    gpio.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(GPIOD, &gpio);
    gpio.Pin = GPIO_PIN_8 | GPIO_PIN_9;
    gpio.Alternate = GPIO_AF7_USART3;
    HAL_GPIO_Init(GPIOD, &gpio);

    gpio.Pin = GPIO_PIN_9 | GPIO_PIN_10;
    gpio.Alternate = GPIO_AF7_USART1;
    HAL_GPIO_Init(GPIOA, &gpio);

    gpio.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    gpio.Mode = GPIO_MODE_IT_FALLING;
    gpio.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOE, &gpio);

    HAL_NVIC_SetPriority(EXTI2_IRQn, 5u, 0u);
    HAL_NVIC_EnableIRQ(EXTI2_IRQn);
    HAL_NVIC_SetPriority(EXTI3_IRQn, 5u, 0u);
    HAL_NVIC_EnableIRQ(EXTI3_IRQn);
}

static void dma_channel_init(
    DMA_HandleTypeDef *handle,
    DMA_Stream_TypeDef *instance,
    uint32_t request,
    uint32_t direction,
    uint32_t priority)
{
    handle->Instance = instance;
    handle->Init.Request = request;
    handle->Init.Direction = direction;
    handle->Init.PeriphInc = DMA_PINC_DISABLE;
    handle->Init.MemInc = DMA_MINC_ENABLE;
    handle->Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
    handle->Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
    handle->Init.Mode = DMA_NORMAL;
    handle->Init.Priority = priority;
    handle->Init.FIFOMode = DMA_FIFOMODE_DISABLE;
    (void)HAL_DMA_Init(handle);
}

static bool dma_init(void)
{
    __HAL_RCC_D2SRAM1_CLK_ENABLE();
    __HAL_RCC_D2SRAM2_CLK_ENABLE();
    __HAL_RCC_DMA1_CLK_ENABLE();
    dma_channel_init(&hdma_usart1_tx, DMA1_Stream0, DMA_REQUEST_USART1_TX,
        DMA_MEMORY_TO_PERIPH, DMA_PRIORITY_MEDIUM);
    dma_channel_init(&hdma_usart2_tx, DMA1_Stream1, DMA_REQUEST_USART2_TX,
        DMA_MEMORY_TO_PERIPH, DMA_PRIORITY_MEDIUM);
    dma_channel_init(&hdma_usart3_rx, DMA1_Stream2, DMA_REQUEST_USART3_RX,
        DMA_PERIPH_TO_MEMORY, DMA_PRIORITY_HIGH);
    dma_channel_init(&hdma_spi2_rx, DMA1_Stream3, DMA_REQUEST_SPI2_RX,
        DMA_PERIPH_TO_MEMORY, DMA_PRIORITY_VERY_HIGH);
    dma_channel_init(&hdma_spi2_tx, DMA1_Stream4, DMA_REQUEST_SPI2_TX,
        DMA_MEMORY_TO_PERIPH, DMA_PRIORITY_VERY_HIGH);

    HAL_NVIC_SetPriority(DMA1_Stream0_IRQn, 6u, 0u);
    HAL_NVIC_EnableIRQ(DMA1_Stream0_IRQn);
    HAL_NVIC_SetPriority(DMA1_Stream1_IRQn, 6u, 0u);
    HAL_NVIC_EnableIRQ(DMA1_Stream1_IRQn);
    HAL_NVIC_SetPriority(DMA1_Stream2_IRQn, 5u, 0u);
    HAL_NVIC_EnableIRQ(DMA1_Stream2_IRQn);
    HAL_NVIC_SetPriority(DMA1_Stream3_IRQn, 4u, 0u);
    HAL_NVIC_EnableIRQ(DMA1_Stream3_IRQn);
    HAL_NVIC_SetPriority(DMA1_Stream4_IRQn, 4u, 0u);
    HAL_NVIC_EnableIRQ(DMA1_Stream4_IRQn);
    return true;
}

static bool timer_init(void)
{
    __HAL_RCC_TIM2_CLK_ENABLE();
    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 199u;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = UINT32_MAX;
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_IC_Init(&htim2) != HAL_OK) {
        return false;
    }

    TIM_IC_InitTypeDef capture = {0};
    capture.ICPolarity = TIM_INPUTCHANNELPOLARITY_RISING;
    capture.ICSelection = TIM_ICSELECTION_DIRECTTI;
    capture.ICPrescaler = TIM_ICPSC_DIV1;
    capture.ICFilter = 2u;
    if (HAL_TIM_IC_ConfigChannel(&htim2, &capture, TIM_CHANNEL_1) != HAL_OK
        || HAL_TIM_IC_ConfigChannel(&htim2, &capture, TIM_CHANNEL_3) != HAL_OK
        || HAL_TIM_IC_ConfigChannel(&htim2, &capture, TIM_CHANNEL_4) != HAL_OK) {
        return false;
    }

    HAL_NVIC_SetPriority(TIM2_IRQn, 2u, 0u);
    HAL_NVIC_EnableIRQ(TIM2_IRQn);
    return HAL_TIM_Base_Start_IT(&htim2) == HAL_OK
        && HAL_TIM_IC_Start_IT(&htim2, TIM_CHANNEL_1) == HAL_OK
        && HAL_TIM_IC_Start_IT(&htim2, TIM_CHANNEL_3) == HAL_OK
        && HAL_TIM_IC_Start_IT(&htim2, TIM_CHANNEL_4) == HAL_OK;
}

static void uart_common(UART_HandleTypeDef *uart, USART_TypeDef *instance, uint32_t baud)
{
    uart->Instance = instance;
    uart->Init.BaudRate = baud;
    uart->Init.WordLength = UART_WORDLENGTH_8B;
    uart->Init.StopBits = UART_STOPBITS_1;
    uart->Init.Parity = UART_PARITY_NONE;
    uart->Init.Mode = UART_MODE_TX_RX;
    uart->Init.HwFlowCtl = UART_HWCONTROL_NONE;
    uart->Init.OverSampling = UART_OVERSAMPLING_16;
    uart->Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    uart->Init.ClockPrescaler = UART_PRESCALER_DIV1;
}

static bool uart_init(void)
{
    __HAL_RCC_USART1_CLK_ENABLE();
    __HAL_RCC_USART2_CLK_ENABLE();
    __HAL_RCC_USART3_CLK_ENABLE();

    uart_common(&huart1, USART1, EVT_HOST_BAUD_RATE);
    uart_common(&huart2, USART2, EVT_HOST_BAUD_RATE);
    uart_common(&huart3, USART3, EVT_GNSS_BAUD_RATE);

    __HAL_LINKDMA(&huart1, hdmatx, hdma_usart1_tx);
    __HAL_LINKDMA(&huart2, hdmatx, hdma_usart2_tx);
    __HAL_LINKDMA(&huart3, hdmarx, hdma_usart3_rx);

    if (HAL_UART_Init(&huart1) != HAL_OK
        || HAL_UART_Init(&huart2) != HAL_OK
        || HAL_UART_Init(&huart3) != HAL_OK) {
        return false;
    }
    if (HAL_UARTEx_SetTxFifoThreshold(&huart1, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK
        || HAL_UARTEx_SetTxFifoThreshold(&huart2, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK
        || HAL_UARTEx_SetRxFifoThreshold(&huart3, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK) {
        return false;
    }
    (void)HAL_UARTEx_DisableFifoMode(&huart1);
    (void)HAL_UARTEx_DisableFifoMode(&huart2);
    (void)HAL_UARTEx_DisableFifoMode(&huart3);

    HAL_NVIC_SetPriority(USART1_IRQn, 6u, 0u);
    HAL_NVIC_EnableIRQ(USART1_IRQn);
    HAL_NVIC_SetPriority(USART2_IRQn, 6u, 0u);
    HAL_NVIC_EnableIRQ(USART2_IRQn);
    HAL_NVIC_SetPriority(USART3_IRQn, 5u, 0u);
    HAL_NVIC_EnableIRQ(USART3_IRQn);

    if (HAL_UARTEx_ReceiveToIdle_DMA(&huart3, gnss_dma_buffer, sizeof(gnss_dma_buffer)) != HAL_OK) {
        return false;
    }
    __HAL_DMA_DISABLE_IT(&hdma_usart3_rx, DMA_IT_HT);
    return true;
}

static bool spi_init(void)
{
    __HAL_RCC_SPI2_CLK_ENABLE();
    hspi2.Instance = SPI2;
    hspi2.Init.Mode = SPI_MODE_MASTER;
    hspi2.Init.Direction = SPI_DIRECTION_2LINES;
    hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi2.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi2.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi2.Init.NSS = SPI_NSS_SOFT;
    hspi2.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_32;
    hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi2.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi2.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    hspi2.Init.CRCPolynomial = 7u;
    hspi2.Init.NSSPMode = SPI_NSS_PULSE_DISABLE;
    hspi2.Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
    hspi2.Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
    hspi2.Init.TxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
    hspi2.Init.RxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
    hspi2.Init.MasterSSIdleness = SPI_MASTER_SS_IDLENESS_00CYCLE;
    hspi2.Init.MasterInterDataIdleness = SPI_MASTER_INTERDATA_IDLENESS_00CYCLE;
    hspi2.Init.MasterReceiverAutoSusp = SPI_MASTER_RX_AUTOSUSP_DISABLE;
    hspi2.Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_ENABLE;
    hspi2.Init.IOSwap = SPI_IO_SWAP_DISABLE;
    __HAL_LINKDMA(&hspi2, hdmarx, hdma_spi2_rx);
    __HAL_LINKDMA(&hspi2, hdmatx, hdma_spi2_tx);
    return HAL_SPI_Init(&hspi2) == HAL_OK;
}

static bool fdcan_init(void)
{
    __HAL_RCC_FDCAN_CLK_ENABLE();
    hfdcan1.Instance = FDCAN1;
    hfdcan1.Init.FrameFormat = FDCAN_FRAME_FD_BRS;
    hfdcan1.Init.Mode = FDCAN_MODE_NORMAL;
    hfdcan1.Init.AutoRetransmission = ENABLE;
    hfdcan1.Init.TransmitPause = ENABLE;
    hfdcan1.Init.ProtocolException = DISABLE;
    hfdcan1.Init.NominalPrescaler = 5u;
    hfdcan1.Init.NominalSyncJumpWidth = 1u;
    hfdcan1.Init.NominalTimeSeg1 = 7u;
    hfdcan1.Init.NominalTimeSeg2 = 2u;
    hfdcan1.Init.DataPrescaler = 1u;
    hfdcan1.Init.DataSyncJumpWidth = 1u;
    hfdcan1.Init.DataTimeSeg1 = 7u;
    hfdcan1.Init.DataTimeSeg2 = 2u;
    hfdcan1.Init.MessageRAMOffset = 0u;
    hfdcan1.Init.StdFiltersNbr = 1u;
    hfdcan1.Init.ExtFiltersNbr = 0u;
    hfdcan1.Init.RxFifo0ElmtsNbr = 8u;
    hfdcan1.Init.RxFifo0ElmtSize = FDCAN_DATA_BYTES_64;
    hfdcan1.Init.RxFifo1ElmtsNbr = 0u;
    hfdcan1.Init.RxBuffersNbr = 0u;
    hfdcan1.Init.TxEventsNbr = 0u;
    hfdcan1.Init.TxBuffersNbr = 0u;
    hfdcan1.Init.TxFifoQueueElmtsNbr = 8u;
    hfdcan1.Init.TxFifoQueueMode = FDCAN_TX_FIFO_OPERATION;
    hfdcan1.Init.TxElmtSize = FDCAN_DATA_BYTES_64;
    if (HAL_FDCAN_Init(&hfdcan1) != HAL_OK) {
        return false;
    }

    FDCAN_FilterTypeDef filter = {0};
    filter.IdType = FDCAN_STANDARD_ID;
    filter.FilterIndex = 0u;
    filter.FilterType = FDCAN_FILTER_MASK;
    filter.FilterConfig = FDCAN_FILTER_TO_RXFIFO0;
    filter.FilterID1 = EVT_RADAR_CAN_RX_ID;
    filter.FilterID2 = 0x7ffu;
    if (HAL_FDCAN_ConfigFilter(&hfdcan1, &filter) != HAL_OK
        || HAL_FDCAN_ConfigGlobalFilter(&hfdcan1,
            FDCAN_REJECT, FDCAN_REJECT,
            FDCAN_REJECT_REMOTE, FDCAN_REJECT_REMOTE) != HAL_OK
        || HAL_FDCAN_ActivateNotification(&hfdcan1,
            FDCAN_IT_RX_FIFO0_NEW_MESSAGE | FDCAN_IT_BUS_OFF, 0u) != HAL_OK
        || HAL_FDCAN_Start(&hfdcan1) != HAL_OK) {
        return false;
    }

    HAL_NVIC_SetPriority(FDCAN1_IT0_IRQn, 4u, 0u);
    HAL_NVIC_EnableIRQ(FDCAN1_IT0_IRQn);
    return true;
}

static bool watchdog_init(void)
{
    hiwdg1.Instance = IWDG1;
    hiwdg1.Init.Prescaler = IWDG_PRESCALER_64;
    hiwdg1.Init.Window = IWDG_WINDOW_DISABLE;
    hiwdg1.Init.Reload = 1000u;
    return HAL_IWDG_Init(&hiwdg1) == HAL_OK;
}

uint32_t evt_board_initialize(void)
{
    SCB_EnableICache();
    HAL_Init();
    uint32_t errors = 0u;
    if (!system_clock_config()) {
        errors |= EVT_INIT_CLOCK;
        return errors;
    }

    gpio_init();
    if (!dma_init()) {
        errors |= EVT_INIT_DMA;
    }
    if (!timer_init()) {
        errors |= EVT_INIT_TIMER;
    }
    if (!uart_init()) {
        errors |= EVT_INIT_UART;
    }
    if (!spi_init()) {
        errors |= EVT_INIT_SPI;
    }
    if (!fdcan_init()) {
        errors |= EVT_INIT_FDCAN;
    }
    if (!watchdog_init()) {
        errors |= EVT_INIT_WATCHDOG;
    }
    return errors;
}

void evt_board_service(void)
{
    if (can_restart_pending) {
        can_restart_pending = false;
        (void)HAL_FDCAN_Stop(&hfdcan1);
        (void)HAL_FDCAN_Start(&hfdcan1);
    }
}

void evt_board_watchdog_refresh(void)
{
    (void)HAL_IWDG_Refresh(&hiwdg1);
}

uint64_t evt_board_time_us(void)
{
    uint32_t high1;
    uint32_t high2;
    uint32_t low;
    bool overflow_pending;
    do {
        high1 = timer_overflow_high;
        low = __HAL_TIM_GET_COUNTER(&htim2);
        overflow_pending = __HAL_TIM_GET_FLAG(&htim2, TIM_FLAG_UPDATE) != RESET;
        high2 = timer_overflow_high;
    } while (high1 != high2);
    if (overflow_pending) {
        high1++;
    }
    return ((uint64_t)high1 << 32) | low;
}

void evt_board_capture_snapshot(evt_capture_snapshot_t *snapshot)
{
    if (snapshot == NULL) {
        return;
    }
    __disable_irq();
    for (unsigned i = 0u; i < EVT_CAPTURE_COUNT; ++i) {
        snapshot->timestamp_us[i] = capture_timestamp[i];
        snapshot->sequence[i] = capture_sequence[i];
    }
    __enable_irq();
}

uint32_t evt_board_power_fault_flags(void)
{
    return power_fault_flags;
}

bool evt_board_can_receive(uint8_t frame[64])
{
    if (frame == NULL || can_rx_tail == can_rx_head) {
        return false;
    }
    memcpy(frame, can_rx_queue[can_rx_tail].data, 64u);
    can_rx_tail = (uint8_t)((can_rx_tail + 1u) % CAN_QUEUE_DEPTH);
    return true;
}

bool evt_board_can_transmit(const uint8_t frame[64])
{
    if (frame == NULL) {
        return false;
    }
    FDCAN_TxHeaderTypeDef header = {0};
    header.Identifier = EVT_RADAR_CAN_TX_ID;
    header.IdType = FDCAN_STANDARD_ID;
    header.TxFrameType = FDCAN_DATA_FRAME;
    header.DataLength = FDCAN_DLC_BYTES_64;
    header.ErrorStateIndicator = FDCAN_ESI_ACTIVE;
    header.BitRateSwitch = FDCAN_BRS_ON;
    header.FDFormat = FDCAN_FD_CAN;
    header.TxEventFifoControl = FDCAN_NO_TX_EVENTS;
    return HAL_FDCAN_AddMessageToTxFifoQ(
        &hfdcan1, &header, (uint8_t *)frame) == HAL_OK;
}

uint32_t evt_board_can_bus_off_count(void)
{
    return can_bus_off_count;
}

size_t evt_board_gnss_read(uint8_t *destination, size_t capacity)
{
    if (destination == NULL) {
        return 0u;
    }
    size_t count = 0u;
    while (count < capacity && gnss_tail != gnss_head) {
        destination[count++] = gnss_ring[gnss_tail];
        gnss_tail = (uint16_t)((gnss_tail + 1u) % GNSS_RING_SIZE);
    }
    return count;
}

uint32_t evt_board_gnss_overflow_count(void)
{
    return gnss_overflow_count;
}

static bool uart_publish(
    UART_HandleTypeDef *uart,
    uint8_t *buffer,
    volatile bool *busy,
    volatile uint32_t *drops,
    const uint8_t *packet,
    size_t length)
{
    if (packet == NULL || length == 0u || length > HOST_PACKET_CAPACITY || *busy) {
        (*drops)++;
        return false;
    }
    memcpy(buffer, packet, length);
    *busy = true;
    if (HAL_UART_Transmit_DMA(uart, buffer, (uint16_t)length) != HAL_OK) {
        *busy = false;
        (*drops)++;
        return false;
    }
    return true;
}

bool evt_board_host_publish(const uint8_t *packet, size_t length)
{
    const bool first = uart_publish(&huart2, host1_tx_buffer,
        &host1_tx_busy, &host_drop_count[0], packet, length);
    const bool second = uart_publish(&huart1, host2_tx_buffer,
        &host2_tx_busy, &host_drop_count[1], packet, length);
    return first || second;
}

uint32_t evt_board_host_drop_count(unsigned channel)
{
    return channel < 2u ? host_drop_count[channel] : 0u;
}

static bool imu_exchange(uint8_t first, uint8_t *second)
{
    uint8_t tx[2] = {first, 0u};
    uint8_t rx[2] = {0u, 0u};
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
    const HAL_StatusTypeDef status = HAL_SPI_TransmitReceive(&hspi2, tx, rx, 2u, 10u);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
    if (status != HAL_OK) {
        return false;
    }
    if (second != NULL) {
        *second = rx[1];
    }
    return true;
}

bool evt_board_imu_read_register(uint8_t reg, uint8_t *value)
{
    return value != NULL && imu_exchange((uint8_t)(reg | 0x80u), value);
}

bool evt_board_imu_write_register(uint8_t reg, uint8_t value)
{
    uint8_t tx[2] = {(uint8_t)(reg & 0x7fu), value};
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
    const HAL_StatusTypeDef status = HAL_SPI_Transmit(&hspi2, tx, 2u, 10u);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
    return status == HAL_OK;
}

bool evt_board_imu_start_burst(void)
{
    if (imu_transfer_active || imu_transfer_complete) {
        return false;
    }
    memset(imu_tx_buffer, 0, sizeof(imu_tx_buffer));
    imu_tx_buffer[0] = 0x1du | 0x80u;
    imu_transfer_active = true;
    imu_transfer_success = false;
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET);
    if (HAL_SPI_TransmitReceive_DMA(
            &hspi2, imu_tx_buffer, imu_rx_buffer, sizeof(imu_tx_buffer)) != HAL_OK) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
        imu_transfer_active = false;
        return false;
    }
    return true;
}

bool evt_board_imu_take_burst(uint8_t burst[14], bool *success)
{
    if (burst == NULL || success == NULL || !imu_transfer_complete) {
        return false;
    }
    memcpy(burst, &imu_rx_buffer[1], 14u);
    *success = imu_transfer_success;
    imu_transfer_complete = false;
    return true;
}

void evt_board_fatal(uint32_t code)
{
    (void)code;
    __disable_irq();
    for (;;) {
    }
}

static uint64_t extend_capture(uint32_t captured)
{
    uint32_t high = timer_overflow_high;
    const uint32_t now = __HAL_TIM_GET_COUNTER(&htim2);
    if (captured <= now && (__HAL_TIM_GET_FLAG(&htim2, TIM_FLAG_UPDATE) != RESET)) {
        high++;
    }
    return ((uint64_t)high << 32) | captured;
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *timer)
{
    if (timer->Instance == TIM2) {
        timer_overflow_high++;
    }
}

void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *timer)
{
    if (timer->Instance != TIM2) {
        return;
    }
    unsigned index;
    uint32_t channel;
    if (timer->Channel == HAL_TIM_ACTIVE_CHANNEL_1) {
        index = EVT_CAPTURE_GNSS_PPS;
        channel = TIM_CHANNEL_1;
    } else if (timer->Channel == HAL_TIM_ACTIVE_CHANNEL_3) {
        index = EVT_CAPTURE_RADAR_REF;
        channel = TIM_CHANNEL_3;
    } else if (timer->Channel == HAL_TIM_ACTIVE_CHANNEL_4) {
        index = EVT_CAPTURE_IMU_DRDY;
        channel = TIM_CHANNEL_4;
    } else {
        return;
    }
    capture_timestamp[index] = extend_capture(HAL_TIM_ReadCapturedValue(timer, channel));
    capture_sequence[index]++;
}

void HAL_GPIO_EXTI_Callback(uint16_t pin)
{
    if (pin == GPIO_PIN_2) {
        power_fault_flags |= 1u;
    } else if (pin == GPIO_PIN_3) {
        power_fault_flags |= 2u;
    }
}

void HAL_FDCAN_RxFifo0Callback(FDCAN_HandleTypeDef *fdcan, uint32_t flags)
{
    if (fdcan->Instance != FDCAN1 || (flags & FDCAN_IT_RX_FIFO0_NEW_MESSAGE) == 0u) {
        return;
    }
    while (HAL_FDCAN_GetRxFifoFillLevel(fdcan, FDCAN_RX_FIFO0) > 0u) {
        FDCAN_RxHeaderTypeDef header;
        uint8_t frame[64];
        if (HAL_FDCAN_GetRxMessage(fdcan, FDCAN_RX_FIFO0, &header, frame) != HAL_OK) {
            break;
        }
        if (header.Identifier != EVT_RADAR_CAN_RX_ID
            || header.DataLength != FDCAN_DLC_BYTES_64) {
            continue;
        }
        const uint8_t next = (uint8_t)((can_rx_head + 1u) % CAN_QUEUE_DEPTH);
        if (next == can_rx_tail) {
            continue;
        }
        memcpy(can_rx_queue[can_rx_head].data, frame, sizeof(frame));
        can_rx_head = next;
    }
}

void HAL_FDCAN_ErrorStatusCallback(FDCAN_HandleTypeDef *fdcan, uint32_t flags)
{
    if (fdcan->Instance == FDCAN1 && (flags & FDCAN_IT_BUS_OFF) != 0u) {
        can_bus_off_count++;
        can_restart_pending = true;
    }
}

void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *uart, uint16_t size)
{
    if (uart->Instance != USART3) {
        return;
    }
    for (uint16_t i = 0u; i < size; ++i) {
        const uint16_t next = (uint16_t)((gnss_head + 1u) % GNSS_RING_SIZE);
        if (next == gnss_tail) {
            gnss_overflow_count++;
            break;
        }
        gnss_ring[gnss_head] = gnss_dma_buffer[i];
        gnss_head = next;
    }
    (void)HAL_UARTEx_ReceiveToIdle_DMA(&huart3, gnss_dma_buffer, sizeof(gnss_dma_buffer));
    __HAL_DMA_DISABLE_IT(&hdma_usart3_rx, DMA_IT_HT);
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *uart)
{
    if (uart->Instance == USART1) {
        host2_tx_busy = false;
    } else if (uart->Instance == USART2) {
        host1_tx_busy = false;
    }
}

void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *spi)
{
    if (spi->Instance == SPI2) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
        imu_transfer_active = false;
        imu_transfer_success = true;
        imu_transfer_complete = true;
    }
}

void HAL_SPI_ErrorCallback(SPI_HandleTypeDef *spi)
{
    if (spi->Instance == SPI2) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
        imu_transfer_active = false;
        imu_transfer_success = false;
        imu_transfer_complete = true;
    }
}
