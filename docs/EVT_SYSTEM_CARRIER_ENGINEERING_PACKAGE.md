# Инженерный комплект EVT System Carrier Rev A

| Параметр | Значение |
| --- | --- |
| Срез комплекта | 2026-10-27 |
| Аппаратная ревизия | A |
| Основная CAD-система | Altium Designer |
| Production authority | NOT_AUTHORIZED |

## Назначение комплекта

Комплект связывает требования, электрические контракты, native Altium CAD,
проверки трассировки и будущие производственные материалы. При расхождении
между описательным текстом и машинно-проверяемым CSV/JSON-контрактом
приоритет имеет контракт и результат соответствующего gate.

## Основные документы

| Документ | Назначение |
| --- | --- |
| docs/EVT_SYSTEM_CARRIER_PROJECT_DESCRIPTION.md | Архитектура, назначение и текущее состояние |
| docs/EVT_SYSTEM_CARRIER_TECHNICAL_SPECIFICATION.md | Формальное техническое задание и критерии приёмки |
| docs/EVT_SYSTEM_CARRIER_REZONIT_REQUEST.md | Данные для согласования стека и DFM с «Резонитом» |
| docs/SYSTEM_CARRIER_SCHEMATIC_CONTRACT.md | Электрические требования к схеме |
| docs/SYSTEM_CARRIER_PCB_LAYOUT_CONTRACT.md | Ограничения размещения и трассировки |
| docs/ALTIUM_NATIVE_HANDOFF.md | Процесс native import, equivalence и release |

## Электрические контракты

| Файл | Содержание |
| --- | --- |
| hardware/system_carrier/BOM_SYS_CARRIER_LAYOUT_004.csv | 92 физических позиции и PCB-only элементы |
| hardware/system_carrier/NETLIST_SYS_001.csv | Электрическая база соединений |
| hardware/system_carrier/PINMAP_SYS_001.csv | Назначения выводов MCU |
| hardware/system_carrier/CONNECTOR_PINOUT_SYS_001.csv | Внешние разъёмы |
| hardware/system_carrier/POWER_TREE_SYS_001.csv | Структура питания |
| hardware/system_carrier/POWER_BUDGET_SYS_001.csv | Распределение токов |
| hardware/system_carrier/CLOCK_TREE_SYS_001.csv | Тактирование и временные входы |
| hardware/system_carrier/FIRMWARE_IO_CONTRACT_SYS_001.csv | Обязанности firmware |
| hardware/system_carrier/RADAR_INTERFACE_SYS_001.csv | Интерфейс AWR2944PEVM |

## CAD и производственные контракты

| Файл | Содержание |
| --- | --- |
| hardware/system_carrier/altium/native/EVT_SYS_CARRIER.SchDoc | Каноническая native-схема |
| hardware/system_carrier/altium/native/EVT_SYS_CARRIER.PcbDoc | Каноническая native-плата |
| hardware/system_carrier/altium/ALTIUM_BOARD_MECHANICAL_SYS_001.csv | Габарит, отверстия и keepout |
| hardware/system_carrier/altium/ALTIUM_EVT_STACKUP_SYS_002.csv | Предварительный EVT-стек |
| hardware/system_carrier/altium/ALTIUM_RULE_QUERY_SYS_001.csv | Native rule scopes |
| hardware/system_carrier/altium/ALTIUM_DFM_PROFILE_SYS_001.csv | Производственные DFM-пункты |
| hardware/system_carrier/altium/ALTIUM_OUTJOB_CONTRACT_SYS_001.csv | Обязательные выходные файлы |

## Подтверждённые результаты

| Проверка | Результат |
| --- | --- |
| KiCad ERC | PASS, 0 ошибок, 0 предупреждений |
| Native Altium import | PASS |
| Source binding | PASS |
| Native compile | PASS, 0 ошибок, 0 предупреждений |
| BOM/designator/MPN | PASS, 92 позиции |
| Footprint equivalence | PASS |
| Pinmap и connector pinout | PASS |
| Netlist и hierarchy | PASS |
| No-mmWave review | PASS |
| ALTIUM_EQUIVALENCE_GATE | PASS |
| Signal connection audit | PASS |
| Target signal disconnected nets | 0 |
| Copper outside board | 0 |
| Unrouted/topology/antennae | 0 |
| Layout authority gate | READY_FOR_ROUTING |
| EVT signal routing implementation | PASS |
| Production authority | NOT_AUTHORIZED |

Зафиксированный результат аудита трассировки привязан к `PcbDoc` с SHA-256
`fc3404b281f3ca76123a8dd68b6076a4e50f5d867ed9fc9582fb6f6ef248ba44`.

## Незакрытые производственные работы

- Согласовать с «Резонитом» стек 1,60 мм, 35 мкм и допуски.
- Получить расчёт 50 Ом GNSS_RF и 100 Ом Ethernet MDI.
- Исправить или формально закрыть 75 production DRC markers.
- Выполнить return-path и SI review.
- Спроектировать компактный корпус и проверить STEP-сборку.
- Выполнить DFM и электрический контроль производственного пакета.
- Создать полный Altium OutJob и проверить каждый обязательный выход.
- Провести стендовые испытания питания и интерфейсов.
- Подтвердить источник RADAR_REF на AWR2944PEVM.

## Управление изменениями

Изменения делятся на три класса:

- Электрический ECO: изменение SchDoc, netlist, pinmap или BOM. Требует нового
  equivalence gate.
- PCB ECO: изменение PcbDoc без изменения электрической схемы. Требует нового
  native audit, connection integrity, DRC и обновления evidence.
- Производственный ECO: изменение стека, импеданса, корпуса, DFM или OutJob.
  Требует обновления release evidence и повторной production readiness.

Файлы с состоянием PROVISIONAL, PENDING или OPEN не являются разрешением на
изготовление. Production authority выдаётся только отдельным
ALTIUM_PRODUCTION_RELEASE_GATE PASS.
