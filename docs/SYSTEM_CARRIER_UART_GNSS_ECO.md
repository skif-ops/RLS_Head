# System Carrier UART and external GNSS ECO

| Параметр | Значение |
| --- | --- |
| Дата | 2026-10-28 |
| Плата | EVT_SYS_CARRIER Rev A |
| Статус | ECO_IN_PROGRESS |
| Production authority | NOT_AUTHORIZED |

## Причина изменения

Требуемый внешний интерфейс системы: обычный UART 3,3 В. Ethernet не входит
в актуальное техническое задание. GNSS не должен быть жёсткой зависимостью
системы, так как прибор должен сохранять работу при отсутствии или подмене
сигналов GNSS.

## Удаляемые узлы

- LAN8742A, RMII и ETH_NRST;
- генератор Ethernet 50 МГц;
- MagJack и MDI-цепи;
- встроенный NEO-M9N;
- U.FL, бортовой GNSS RF-тракт и bias-T.

## Два host UART

J6 остаётся шестиконтактным Molex Micro-Fit 3.0 `43045-0600`:

| Контакт | Сигнал | Назначение |
| --- | --- | --- |
| 1 | GND | Возврат UART1 |
| 2 | HOST_UART1_TX | USART2 TX, PD5, вывод 147 |
| 3 | HOST_UART1_RX | USART2 RX, PD6, вывод 150 |
| 4 | GND | Возврат UART2 |
| 5 | HOST_UART2_TX | USART1 TX, PA9, вывод 120 |
| 6 | HOST_UART2_RX | USART1 RX, PA10, вывод 121 |

Все четыре сигнальные линии имеют резисторы 33 Ом и защиту
TPD4E05U06DQAR. Входы RX имеют подтяжку 10 кОм к 3V3. J6 не выдаёт питание.

## Внешний GNSS без пайки

Приёмник: simpleRTK3B Pro на базе Septentrio mosaic-X5. Он подключается к
System Carrier готовым кабелем через JST-GH. Монтаж, демонтаж и замена
приёмника не требуют пайки.

Разъём платы J8:

- производитель: JST;
- MPN: `SM06B-GHS-TB(LF)(SN)`;
- исполнение: угловое SMT, 1x6, шаг 1,25 мм;
- посадочное место: `Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal`.

| Контакт | Сигнал | Назначение |
| --- | --- | --- |
| 1 | 5V_GNSS | Питание внешнего приёмника |
| 2 | GNSS_RX_EXT | USART3 TX платы к RX приёмника |
| 3 | GNSS_TX_EXT | TX приёмника к USART3 RX платы |
| 4 | GNSS_PPS | PPS приёмника к PA0/TIM2_CH1 |
| 5 | NC | Event приёмника не используется |
| 6 | GND | Силовой и сигнальный возврат |

UART и PPS защищены TPD4E05U06DQAR. Для приёмника добавляется фиксированный
преобразователь 5 В TPS62133RGTR с дросселем XFL4020-222MEC. В power budget
зарезервировано 0,50 А.

## Политика доверия GNSS

- GNSS не является условием загрузки или продолжения измерений.
- Данные UART и PPS имеют состояние UNTRUSTED до проверки целостности.
- При spoofing, jamming, аномалии PPS или рассогласовании данных приёмник
  переводится в карантин.
- Радар, CAN-FD, оба host UART, IMU и локальное журналирование продолжают
  работу без GNSS.
- При отсутствии доверенного GNSS система не заявляет доверенное абсолютное
  время или абсолютное положение.
- Группы созвездий и их участие в PVT задаются конфигурацией приёмника и
  политикой STM32.

## Проверенные первичные источники

- [STM32H753 datasheet](https://www.st.com/resource/en/datasheet/stm32h753ai.pdf)
- [Septentrio mosaic-X5](https://www.septentrio.com/en/products/gnss-receivers/gnss-receiver-modules/mosaic-x5)
- [Septentrio receiver command reference](https://septentrio.com/rx_refguides/ssrc4/refguide.html)
- [ArduSimple simpleRTK3B Pro guide](https://www.ardusimple.com/user-guide-simplertk3b-pro/)
- [TPS62133RGTR product data](https://www.ti.com/product/TPS62133/part-details/TPS62133RGTR)

## Условия закрытия ECO

1. Восемь листов схемы сохранены как native Altium SchDoc.
2. PcbDoc не содержит Ethernet и встроенного GNSS.
3. J6, J8, U9, D3, D8 и связанные цепи совпадают с BOM и netlist.
4. Native compile, hierarchy, BOM, netlist, no-mmWave и DRC проходят.
5. ALTIUM_EQUIVALENCE_GATE сообщает PASS для текущих хэшей SchDoc и PcbDoc.
6. Производственные PDF и выходные файлы сформированы Altium OutJob.
