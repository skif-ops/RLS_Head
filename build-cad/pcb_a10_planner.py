import csv
import heapq
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "hardware/system_carrier/altium/routing/a10_planning_baseline"
STEP = 0.20
BOARD_W = 100.0
BOARD_H = 80.0
EDGE = 0.55
TRACE_WIDTH = 0.20
POWER_TRACE_WIDTH = 0.30
POWER_NECK_WIDTH = 0.15
CLEARANCE = 0.20
VIA_SIZE = 0.60
VIA_HOLE = 0.30
NODE_RADIUS = VIA_SIZE / 2
GRID_GUARD = 0.0
NET_CLEARANCE_GUARD = {"ETH_CT": 0.005}
ROUTING_LAYERS = (0, 1, 2)
L3_ALLOWED = {
    "CAN_TX", "CAN_RX",
    "IMU_MISO", "IMU_MOSI",
    "ETH_TX_EN", "ETH_TXD0", "ETH_TXD1", "ETH_CRS_DV", "ETH_RXD0", "ETH_RXD1",
    "SWDIO", "SWCLK", "SWO", "DEBUG_TX", "DEBUG_RX",
    "NRST", "BOOT0", "ETH_NRST", "ETH_MDIO", "ETH_MDC",
    "NetC60_1", "ETH_CT",
}
LAYER_OPTIONS = {
    "ETH_RXD1": (0, 1, 2),
    "ETH_RXD0": (0, 1, 2),
    "ETH_50M": (0, 1, 2),
    "ETH_MDIO": (0, 1, 2),
    "ETH_MDC": (0, 1, 2),
    "ETH_NRST": (0, 1),
    "ETH_TXD0": (0, 2),
    "IMU_MISO": (0, 1, 2),
    "IMU_MOSI": (0, 1, 2),
    "IMU_NSS": (0, 1, 2),
    "IMU_SCK": (0, 1),
}
FORCED_INTERNAL_LAYER = {
    "ETH_50M": 2,
    "ETH_CRS_DV": 2,
    "ETH_TX_EN": 2,
    "ETH_TXD0": 1,
    "ETH_TXD1": 2,
    "CAN_TX": 2,
    "NRST": 2,
    "IMU_SCK": 1,
    "IMU_MOSI": 2,
    "SWO": 1,
    "SWCLK": 1,
    "SWDIO": 2,
}
FORCED_TOP_ESCAPE_RADIUS = {
    "ETH_TX_EN": 8.0,
    "ETH_TXD0": 0.6,
    "ETH_TXD1": 1.0,
    "CAN_TX": 8.0,
    "NRST": 8.0,
    "ETH_RXD0": 0.6,
    "ETH_RXD1": 0.6,
}
TARGETS = [
    "MCU_HSE_25M", "ETH_50M",
    "RADAR_CANH", "RADAR_CANL", "CAN_TX", "CAN_RX",
    "IMU_SCK", "IMU_NSS", "IMU_MISO", "IMU_MOSI",
    "ETH_MDIO", "ETH_MDC", "ETH_CRS_DV", "ETH_RXD0", "ETH_RXD1",
    "ETH_TX_EN", "ETH_TXD0", "ETH_TXD1", "ETH_NRST",
    "SWDIO", "SWCLK", "SWO", "DEBUG_TX", "DEBUG_RX", "NRST", "BOOT0",
    "NetC60_1", "ETH_CT",
]
ORDER = [
    "MCU_HSE_25M", "SWDIO", "SWCLK", "SWO", "DEBUG_RX", "DEBUG_TX", "ETH_CRS_DV", "ETH_50M", "ETH_NRST", "NetC60_1", "RADAR_CANH", "RADAR_CANL", "ETH_TX_EN", "IMU_MOSI", "IMU_SCK", "ETH_TXD0", "ETH_TXD1", "IMU_NSS", "IMU_MISO", "ETH_RXD0", "ETH_RXD1", "CAN_TX", "ETH_MDIO", "ETH_MDC",
    "ETH_CT", "CAN_RX",
    "NRST", "BOOT0",
]
ENDPOINT_ORDER = {
    "MCU_HSE_25M": [("U1", "29"), ("Y1", "3")],
    "ETH_50M": [("U1", "41"), ("Y2", "3"), ("U3", "5")],
    "RADAR_CANH": [("U4", "7"), ("D4", "1"), ("", "3"), ("R40", "1")],
    "RADAR_CANL": [("U4", "6"), ("D4", "2"), ("", "1"), ("R40", "2")],
    "ETH_NRST": [("U3", "15"), ("R605", "1"), ("U1", "3")],
    "NRST": [("U1", "31"), ("C115", "1"), ("", "1")],
    "BOOT0": [("U1", "166"), ("R10", "1"), ("R70", "1")],
}
ESCAPE_DIRECTION = {
    ("D4", "1"): (1, 0),
    ("D4", "2"): (1, 0),
}
NET_ESCAPE_DIRECTION = {
    ("RADAR_CANH", "", "3"): (1, 0),
    ("RADAR_CANL", "", "1"): (1, 0),
}
MANUAL_LEADS = {
    ("C60", "1"): [(67.40, 56.20)],
    ("C63", "1"): [(83.40, 56.20)],
    ("R601", "2"): [(78.20, 56.60), (79.60, 56.60), (79.60, 59.00)],
    ("R602", "2"): [(78.20, 58.60), (79.00, 58.60), (79.00, 59.40)],
    ("R605", "1"): [(77.40, 50.80), (76.40, 50.80), (76.40, 56.40)],
    ("", "5"): [(88.40, 60.00), (88.40, 61.40), (85.40, 61.40), (85.40, 60.00)],
    ("U3", "6"): [(69.40, 56.40), (68.40, 56.40)],
    ("D4", "1"): [(87.20, 31.00), (90.40, 31.00)],
    ("D4", "2"): [(87.20, 27.60), (88.00, 27.60)],
    ("U1", "41"): [(38.60, 30.75), (37.80, 30.40), (36.80, 30.40)],
    ("U1", "42"): [(38.60, 30.25), (38.10, 30.00), (37.20, 29.60), (37.00, 29.40)],
    ("U1", "33"): [(38.20, 34.75), (38.00, 34.00)],
    ("U1", "53"): [(45.25, 26.20), (44.20, 26.20), (44.20, 25.40)],
    ("U1", "54"): [(45.75, 26.20), (45.20, 25.60), (45.20, 24.80), (44.60, 24.80), (44.60, 23.00), (42.00, 23.00), (42.00, 25.60)],
    ("U1", "55"): [(46.25, 26.20), (46.80, 25.60), (47.40, 25.60)],
    ("U1", "31"): [(38.80, 35.75), (36.80, 35.80)],
    ("U1", "154"): [(52.25, 53.75), (53.00, 54.20), (53.20, 54.20)],
    ("U1", "156"): [(51.25, 53.75), (52.00, 54.20), (52.20, 54.80)],
    ("U1", "157"): [(50.75, 53.75), (50.75, 54.40), (51.20, 55.00), (51.20, 55.20)],
    ("U1", "150"): [(54.25, 53.75), (54.00, 54.00)],
    ("U1", "142"): [(58.25, 53.75), (59.00, 54.50)],
    ("U1", "143"): [(57.75, 53.75), (57.00, 54.50)],
    ("U1", "147"): [(55.75, 53.75), (56.25, 54.25)],
    ("U1", "92"): [(66.00, 30.75), (68.60, 30.75)],
    ("U1", "93"): [(66.00, 31.25), (68.00, 31.25)],
    ("U1", "94"): [(66.00, 31.75), (66.80, 31.80)],
    ("U1", "95"): [(66.00, 32.25), (67.60, 32.80)],
    ("U2", "12"): [(53.00, 56.20), (54.40, 56.60)],
    ("U2", "13"): [(52.00, 55.75), (52.00, 55.50)],
    ("U2", "1"): [(50.00, 57.25), (49.50, 56.00)],
    ("U2", "14"): [(50.80, 56.60)],
    ("U3", "7"): [(70.75, 55.20), (70.20, 54.60), (69.00, 53.60)],
    ("U3", "8"): [(71.25, 55.20), (71.00, 54.60), (71.00, 53.60)],
    ("U3", "11"): [(72.90, 55.20), (72.90, 54.40), (73.40, 53.60)],
    ("U3", "12"): [(73.25, 55.20), (74.20, 54.40), (74.20, 53.60)],
    ("U3", "13"): [(74.65, 56.75), (75.40, 56.00), (76.00, 55.40)],
    ("U3", "15"): [(74.65, 57.75), (75.00, 57.20)],
    ("U3", "16"): [(74.65, 58.25), (75.50, 57.90), (76.40, 57.60)],
    ("U3", "17"): [(74.65, 58.75), (75.40, 58.60), (76.20, 58.40), (76.80, 59.00), (76.80, 60.00), (77.20, 60.20)],
    ("U3", "18"): [(74.40, 59.25), (74.40, 62.40)],
    ("Y2", "3"): [(67.93, 51.60), (75.00, 51.60), (75.00, 52.40)],
    ("J10", "2"): [(47.50, 3.73)],
    ("J10", "4"): [(47.50, 5.00)],
    ("J10", "6"): [(47.50, 6.27)],
}
GNSS_PPS_REROUTE = [
    ((29.60, 66.80), (29.75, 66.75)),
    ((29.75, 66.75), (30.00, 66.75)),
    ((30.00, 66.75), (30.50, 67.25)),
    ((30.50, 67.25), (31.50, 67.25)),
    ((31.50, 67.25), (34.00, 64.75)),
    ((34.00, 64.75), (34.00, 37.30)),
    ((34.00, 37.30), (33.50, 36.60)),
    ((33.50, 36.60), (33.50, 32.00)),
    ((33.50, 32.00), (34.00, 31.30)),
    ((34.00, 31.30), (39.325, 31.25)),
]
PLACEMENT_SHIFT = {
    "D4": (-0.65, -0.50),
    "C107": (3.00, 0.0),
    "C111": (3.00, 0.0),
    "C113": (-2.00, 0.0),
    "C115": (-1.75, 0.0),
    "C102": (-3.00, 0.0),
    "C64": (-2.00, 0.0),
    "C60": (-2.00, 0.0),
    "R601": (1.50, 0.0),
    "R602": (1.50, 0.0),
    "C63": (2.50, 0.0),
    "R605": (8.00, 0.0),
}
POWER_STITCH_NETS = {"3V3", "GND"}
POWER_CONNECTION_TARGETS = {
    ("R601", "2"): ("U3", "19"),
    ("R602", "2"): ("R601", "2"),
    ("C60", "2"): ("U3", "25"),
    ("C64", "2"): ("U3", "25"),
    ("C64", "1"): ("R601", "2"),
    ("R605", "2"): ("U3", "25"),
    ("C63", "2"): ("U3", "25"),
    ("C107", "2"): ("U1", "90"),
    ("C107", "1"): ("U1", "91"),
    ("C102", "2"): ("U1", "37"),
    ("C102", "1"): ("U1", "36"),
    ("C111", "2"): ("U1", "135"),
    ("C111", "1"): ("U1", "136"),
    ("C113", "2"): ("U1", "158"),
    ("C113", "1"): ("U1", "159"),
    ("C115", "2"): ("C102", "2"),
}
POWER_ROUTE_BRANCHES = {}
POWER_PLANNING_OBSTACLE_OVERRIDES = {}
POWER_EXTRA_NECKS = {
    ("R601", "2"): {7, 8, 9, 10},
}
POWER_ROUTE_OVERRIDES = {
    ("R601", "2"): [
        (0, 77.5000004, 56.5099962),
        (0, 78.20, 56.60),
        (2, 78.20, 56.60),
        (2, 74.20, 56.60),
        (2, 74.20, 65.00),
        (2, 73.60, 65.00),
        (2, 73.60, 61.40),
        (0, 73.60, 61.40),
        (0, 73.40, 61.60),
        (0, 73.40, 61.00),
        (0, 73.20, 60.80),
        (0, 73.2499932, 59.9374976),
    ],
    ("R602", "2"): [
        (0, 77.5000004, 58.5099922),
        (0, 77.50, 59.40),
        (1, 77.50, 59.40),
        (1, 76.20, 59.40),
        (1, 76.20, 56.50),
        (1, 77.5000004, 56.5099962),
        (0, 77.5000004, 56.5099962),
    ],
    ("C60", "2"): [
        (0, 66.49999, 57.7749924),
        (1, 66.49999, 57.7749924),
        (1, 71.20, 58.80),
        (0, 71.20, 58.80),
    ],
    ("C64", "2"): [
        (0, 67.999987, 55.4800008),
        (1, 67.999987, 55.4800008),
        (1, 72.00, 57.20),
        (0, 72.00, 57.20),
    ],
    ("C64", "1"): [
        (0, 67.999987, 54.5200078),
        (2, 67.999987, 54.5200078),
        (2, 68.00, 51.00),
        (2, 78.20, 51.00),
        (2, 78.20, 56.60),
        (0, 78.20, 56.60),
    ],
    ("R605", "2"): [
        (0, 77.499988, 53.3249886),
        (1, 77.499988, 53.3249886),
        (1, 79.80, 54.20),
        (1, 79.80, 62.40),
        (1, 72.00, 62.40),
        (1, 72.00, 58.00),
        (0, 72.00, 58.00),
    ],
    ("C63", "2"): [
        (0, 82.4999924, 57.7749924),
        (0, 81.40, 57.00),
        (1, 81.40, 57.00),
        (1, 79.80, 57.00),
    ],
    ("C107", "1"): [
        (0, 69.499994, 30.520005),
        (0, 69.40, 29.80),
        (1, 69.40, 29.80),
        (1, 69.40, 28.00),
        (1, 67.60, 28.00),
        (1, 67.60, 29.40),
        (0, 67.60, 29.40),
        (0, 67.60, 30.25),
        (0, 64.675004, 30.250003),
    ],
    ("C107", "2"): [
        (0, 69.499994, 31.479998),
        (0, 69.40, 32.20),
        (2, 69.40, 32.20),
        (2, 70.20, 31.40),
        (2, 70.20, 28.40),
        (2, 66.60, 28.40),
        (0, 66.60, 28.40),
        (0, 66.60, 29.75),
        (0, 64.675004, 29.750004),
    ],
    ("C102", "2"): [
        (0, 34.5000012, 35.47999),
        (0, 34.60, 36.20),
        (2, 34.60, 36.20),
        (2, 33.80, 35.40),
        (2, 33.80, 32.00),
        (2, 37.00, 32.00),
        (2, 37.00, 32.75),
        (0, 37.00, 32.75),
        (0, 39.3249912, 32.749998),
    ],
    ("C102", "1"): [
        (0, 34.5000012, 34.519997),
        (0, 34.60, 33.80),
        (0, 35.20, 33.20),
        (1, 35.20, 33.20),
        (1, 35.20, 34.00),
        (1, 36.40, 34.00),
        (1, 36.40, 33.40),
        (0, 36.40, 33.40),
        (0, 39.3249912, 33.249997),
    ],
    ("C111", "2"): [
        (0, 64.000005, 54.9800018),
        (0, 64.00, 55.80),
        (2, 64.00, 55.80),
        (2, 62.40, 54.00),
        (0, 62.40, 54.00),
        (0, 61.75, 54.00),
        (0, 61.7499908, 52.6750026),
    ],
    ("C111", "1"): [
        (0, 64.000005, 54.0200088),
        (0, 64.00, 53.20),
        (1, 64.00, 53.20),
        (1, 64.80, 52.40),
        (1, 61.25, 52.40),
        (1, 61.25, 55.00),
        (0, 61.25, 55.00),
        (0, 61.2499918, 52.6750026),
    ],
    ("C113", "2"): [
        (0, 47.0000036, 54.9800018),
        (0, 47.80, 55.40),
        (0, 48.80, 56.00),
        (1, 48.80, 56.00),
        (1, 49.60, 56.00),
        (1, 49.60, 54.50),
        (0, 49.60, 54.50),
        (0, 50.25, 54.50),
        (0, 50.2500138, 52.6750026),
    ],
    ("C113", "1"): [
        (0, 47.0000036, 54.0200088),
        (0, 48.00, 54.02),
        (0, 48.00, 54.60),
        (2, 48.00, 54.60),
        (2, 48.80, 55.00),
        (0, 48.80, 55.00),
        (0, 49.75, 55.00),
        (0, 49.7499894, 52.6750026),
    ],
    ("C115", "2"): [
        (0, 35.7500012, 37.9800104),
        (0, 35.80, 38.80),
        (1, 35.80, 38.80),
        (1, 34.60, 36.20),
        (0, 34.60, 36.20),
        (0, 34.5000012, 35.47999),
    ],
}
POWER_FINAL_ROUTE_OVERRIDES = {
    ("C113", "2"): [
        (0, 47.0000036, 54.9800018),
        (0, 47.80, 55.40),
        (0, 48.80, 56.00),
        (1, 48.80, 56.00),
        (1, 49.40, 56.00),
        (1, 49.40, 56.40),
        (0, 49.40, 56.40),
        (0, 50.25, 56.40),
        (0, 50.2500138, 52.6750026),
    ],
}
SIGNAL_ROUTE_OVERRIDES = {
    ("IMU_MOSI", 1): [
        (0, 64.675004, 32.249999),
        (0, 66.00, 32.25),
        (0, 67.60, 32.80),
        (0, 67.60, 33.20),
        (2, 67.60, 33.20),
        (2, 84.60, 50.20),
        (2, 84.60, 62.60),
        (2, 86.60, 64.60),
        (2, 86.60, 68.20),
        (2, 86.40, 68.40),
        (2, 62.80, 68.40),
        (2, 50.80, 56.40),
        (2, 51.00, 56.20),
        (0, 51.00, 56.20),
        (0, 51.00, 56.60),
        (0, 51.4999986, 56.737504),
    ],
    ("IMU_MISO", 1): [
        (0, 64.675004, 31.75),
        (0, 66.00, 31.75),
        (0, 66.80, 31.80),
        (0, 67.20, 31.80),
        (0, 68.40, 33.00),
        (0, 68.40, 33.40),
        (0, 68.00, 33.80),
        (0, 67.60, 33.80),
        (0, 67.60, 36.80),
        (0, 66.00, 38.40),
        (1, 66.00, 38.40),
        (1, 60.40, 44.00),
        (2, 60.40, 44.00),
        (2, 59.20, 45.20),
        (1, 59.20, 45.20),
        (1, 55.20, 49.20),
        (1, 55.20, 49.80),
        (2, 55.20, 49.80),
        (2, 50.40, 54.60),
        (2, 50.40, 55.40),
        (2, 50.40, 57.20),
        (2, 47.80, 57.20),
        (2, 47.80, 56.40),
        (0, 47.80, 56.40),
        (0, 47.80, 57.25),
        (0, 50.9875028, 57.2499998),
    ],
    ("ETH_TXD0", 1): [
        (0, 51.2499864, 52.6750026),
        (0, 51.25, 53.75),
        (0, 52.00, 54.20),
        (0, 52.20, 54.80),
        (1, 52.20, 54.80),
        (1, 52.00, 55.00),
        (1, 52.00, 56.00),
        (1, 52.20, 56.20),
        (1, 62.60, 56.20),
        (1, 65.00, 53.80),
        (1, 70.20, 53.80),
        (1, 75.65, 59.20),
        (1, 75.65, 59.80),
        (1, 76.40, 60.40),
        (1, 77.20, 60.40),
        (0, 77.20, 60.40),
        (0, 77.20, 60.20),
        (0, 76.80, 60.00),
        (0, 76.80, 59.00),
        (0, 76.20, 58.40),
        (0, 75.40, 58.60),
        (0, 74.65, 58.75),
        (0, 73.937495, 58.7499968),
    ],
    ("ETH_CT", 1): [
        (0, 89.670001, 60.000007),
        (0, 88.40, 60.00),
        (0, 88.40, 61.40),
        (0, 85.40, 61.40),
        (0, 85.40, 59.40),
        (1, 85.40, 59.40),
        (1, 84.60, 58.60),
        (1, 84.40, 56.20),
        (1, 84.80, 55.80),
        (1, 85.40, 55.80),
        (0, 85.40, 55.80),
        (0, 83.60, 55.80),
        (0, 83.20, 56.20),
        (0, 82.4999924, 56.2250082),
    ],
    ("ETH_CT", 2): [
        (0, 93.480001, 57.460007),
        (0, 92.40, 57.40),
        (0, 92.40, 56.20),
        (0, 92.00, 55.80),
        (0, 85.40, 55.80),
        (1, 85.40, 55.80),
        (1, 84.80, 55.80),
        (1, 84.40, 56.20),
        (1, 84.60, 58.60),
        (1, 85.40, 59.40),
        (0, 85.40, 59.40),
        (0, 85.40, 60.80),
        (0, 86.00, 61.40),
        (0, 88.40, 61.40),
    ],
    ("NRST", 1): [
        (0, 35.7500012, 37.019992),
        (0, 35.80, 36.20),
        (0, 36.20, 35.80),
        (0, 36.80, 35.80),
        (0, 38.80, 35.75),
        (0, 39.3249912, 35.749992),
    ],
    ("ETH_50M", 2): [
        (0, 70.0624964, 57.2499998),
        (0, 69.20, 57.20),
        (0, 69.00, 57.20),
        (2, 69.00, 57.20),
        (2, 70.80, 56.80),
    ],
}
FINAL_ONLY_SIGNAL_ROUTES = {
    ("IMU_MOSI", 1),
    ("IMU_MISO", 1),
    ("ETH_TXD0", 1),
    ("ETH_CT", 1),
    ("ETH_CT", 2),
}
LEGACY_POWER_STITCH_LEADS = {
    ("R601", "2"): [],
    ("C60", "2"): [],
    ("C64", "2"): [],
    ("C64", "1"): [],
    ("R605", "2"): [],
    ("R602", "2"): [],
    ("C63", "2"): [(81.40, 57.00)],
    ("C107", "2"): [],
    ("C107", "1"): [],
    ("C102", "2"): [(34.60, 36.20), (34.60, 36.40)],
    ("C102", "1"): [(34.60, 33.80), (34.60, 33.60)],
    ("C111", "2"): [],
    ("C111", "1"): [],
    ("C113", "2"): [],
    ("C113", "1"): [],
    ("C115", "2"): [],
}
MDI_REPLACED_SEGMENTS = {
    "ETH_TXP": {
        tuple(sorted(((76.00, 55.49), (75.00, 55.49)))),
        tuple(sorted(((75.00, 55.49), (84.00, 55.49)))),
        tuple(sorted(((84.00, 55.49), (84.00, 61.50)))),
        tuple(sorted(((84.00, 61.50), (82.40, 61.50)))),
    },
    "ETH_TXN": {
        tuple(sorted(((76.00, 57.49), (77.00, 57.49)))),
        tuple(sorted(((77.00, 57.49), (77.00, 64.54)))),
    },
}
MDI_REPLACEMENT_TRACKS = [
    ("ETH_TXP", 0, (77.50, 55.49), (79.00, 55.49)),
    ("ETH_TXN", 0, (77.50, 57.49), (78.50, 57.49)),
]


def rows(name):
    with (AUDIT / name).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def mm(value):
    return float(value) * 0.0254


def row_point(row):
    shift = PLACEMENT_SHIFT.get(row["designator"], (0.0, 0.0))
    return mm(row["x_mil"]) + shift[0], mm(row["y_mil"]) + shift[1]


def row_rect(row):
    shift = PLACEMENT_SHIFT.get(row["designator"], (0.0, 0.0))
    left, bottom, right, top = (mm(row[key]) for key in ("left_mil", "bottom_mil", "right_mil", "top_mil"))
    return left + shift[0], bottom + shift[1], right + shift[0], top + shift[1]


def moved_power_connections():
    pads = rows("pad_geometry.csv")
    by_key = {(row["designator"], row["pad_name"]): row for row in pads}
    connections = []
    for key, target_key in POWER_CONNECTION_TARGETS.items():
        source = by_key.get(key)
        target = by_key.get(target_key)
        if source is None or target is None:
            raise RuntimeError(f"missing power connection endpoint: {key} -> {target_key}")
        if source["net_name"] not in POWER_STITCH_NETS or target["net_name"] != source["net_name"]:
            raise RuntimeError(f"power connection net mismatch: {key} -> {target_key}")
        connections.append((source["net_name"], source, target))
    expected = {
        (row["designator"], row["pad_name"])
        for row in pads
        if row["designator"] in PLACEMENT_SHIFT and row["net_name"] in POWER_STITCH_NETS
    }
    missing = expected - set(POWER_CONNECTION_TARGETS)
    if missing:
        raise RuntimeError(f"missing power connection targets: {sorted(missing)}")
    return connections


def legacy_power_stitches():
    result = []
    for row in rows("pad_geometry.csv"):
        key = row["designator"], row["pad_name"]
        if key not in LEGACY_POWER_STITCH_LEADS:
            continue
        result.append((row["net_name"], [row_point(row), *LEGACY_POWER_STITCH_LEADS[key]], *key))
    return result


def snap(point):
    return round(point[0] / STEP), round(point[1] / STEP)


def unsnap(node):
    return node[0] * STEP, node[1] * STEP


def point_segment_distance(point, first, second):
    px, py = point
    ax, ay = first
    bx, by = second
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    ratio = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    ratio = max(0.0, min(1.0, ratio))
    return math.hypot(px - ax - ratio * dx, py - ay - ratio * dy)


def raster_rect(blocked, layer, rect, inflate):
    left, bottom, right, top = rect
    left -= inflate
    bottom -= inflate
    right += inflate
    top += inflate
    ix0 = max(0, math.floor(left / STEP))
    ix1 = min(round(BOARD_W / STEP), math.ceil(right / STEP))
    iy0 = max(0, math.floor(bottom / STEP))
    iy1 = min(round(BOARD_H / STEP), math.ceil(top / STEP))
    for ix in range(ix0, ix1 + 1):
        x = ix * STEP
        for iy in range(iy0, iy1 + 1):
            y = iy * STEP
            if left <= x <= right and bottom <= y <= top:
                blocked[layer].add((ix, iy))


def raster_circle(blocked, layers, center, radius):
    cx, cy = center
    ix0 = max(0, math.floor((cx - radius) / STEP))
    ix1 = min(round(BOARD_W / STEP), math.ceil((cx + radius) / STEP))
    iy0 = max(0, math.floor((cy - radius) / STEP))
    iy1 = min(round(BOARD_H / STEP), math.ceil((cy + radius) / STEP))
    for ix in range(ix0, ix1 + 1):
        for iy in range(iy0, iy1 + 1):
            if math.hypot(ix * STEP - cx, iy * STEP - cy) <= radius:
                for layer in layers:
                    blocked[layer].add((ix, iy))


def raster_segment(blocked, layer, first, second, radius):
    left = min(first[0], second[0]) - radius
    right = max(first[0], second[0]) + radius
    bottom = min(first[1], second[1]) - radius
    top = max(first[1], second[1]) + radius
    ix0 = max(0, math.floor(left / STEP))
    ix1 = min(round(BOARD_W / STEP), math.ceil(right / STEP))
    iy0 = max(0, math.floor(bottom / STEP))
    iy1 = min(round(BOARD_H / STEP), math.ceil(top / STEP))
    for ix in range(ix0, ix1 + 1):
        for iy in range(iy0, iy1 + 1):
            point = ix * STEP, iy * STEP
            if point_segment_distance(point, first, second) <= radius:
                blocked[layer].add((ix, iy))


def build_base(include_legacy_power=True):
    blocked = {layer: set() for layer in ROUTING_LAYERS}
    via_blocked = {layer: set() for layer in ROUTING_LAYERS}
    pad_rows = rows("pad_geometry.csv")
    for row in pad_rows:
        rect = row_rect(row)
        layer = int(row["layer"])
        if float(row["hole_mil"]) > 0 or layer == 74:
            layers = ROUTING_LAYERS
        elif layer == 1:
            layers = (0,)
        elif layer == 32:
            layers = (2,)
        else:
            layers = ()
        for item in layers:
            raster_rect(blocked, item, rect, CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
            raster_rect(via_blocked, item, rect, CLEARANCE + NODE_RADIUS)
    components = {}
    for row in pad_rows:
        if not row["designator"] or int(row["layer"]) not in (1, 74):
            continue
        rect = row_rect(row)
        components.setdefault(row["designator"], []).append(rect)
    for rects in components.values():
        if len(rects) < 2:
            continue
        body = (
            min(rect[0] for rect in rects),
            min(rect[1] for rect in rects),
            max(rect[2] for rect in rects),
            max(rect[3] for rect in rects),
        )
        raster_rect(blocked, 0, body, 0.0)
    for row in rows("track_inventory.csv"):
        layer_number = int(row["layer"])
        if layer_number not in (1, 3, 32):
            continue
        if row["net_name"] == "GNSS_PPS":
            continue
        layer = {1: 0, 3: 1, 32: 2}[layer_number]
        first = mm(row["x1_mil"]), mm(row["y1_mil"])
        second = mm(row["x2_mil"]), mm(row["y2_mil"])
        key = tuple(sorted(((round(first[0], 2), round(first[1], 2)), (round(second[0], 2), round(second[1], 2)))))
        if key in MDI_REPLACED_SEGMENTS.get(row["net_name"], set()):
            continue
        radius = mm(row["width_mil"]) / 2
        raster_segment(blocked, layer, first, second, radius + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
        raster_segment(via_blocked, layer, first, second, radius + CLEARANCE + NODE_RADIUS)
    for first, second in GNSS_PPS_REROUTE:
        raster_segment(blocked, 0, first, second, TRACE_WIDTH / 2 + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
        raster_segment(via_blocked, 0, first, second, TRACE_WIDTH / 2 + CLEARANCE + NODE_RADIUS)
    for _, layer, first, second in MDI_REPLACEMENT_TRACKS:
        raster_segment(blocked, layer, first, second, 0.26 / 2 + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
        raster_segment(via_blocked, layer, first, second, 0.26 / 2 + CLEARANCE + NODE_RADIUS)
    for row in rows("fill_inventory.csv"):
        layer_number = int(row["layer"])
        if layer_number not in (1, 3, 32):
            continue
        layer = {1: 0, 3: 1, 32: 2}[layer_number]
        rect = tuple(mm(row[key]) for key in ("left_mil", "bottom_mil", "right_mil", "top_mil"))
        raster_rect(blocked, layer, rect, CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
        raster_rect(via_blocked, layer, rect, CLEARANCE + NODE_RADIUS)
    for row in rows("via_inventory.csv"):
        center = mm(row["x_mil"]), mm(row["y_mil"])
        if row["net_name"] == "ETH_TXP" and math.hypot(center[0] - 75.0, center[1] - 55.49) < 0.02:
            continue
        radius = mm(row["size_mil"]) / 2
        raster_circle(blocked, ROUTING_LAYERS, center, radius + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
        raster_circle(via_blocked, ROUTING_LAYERS, center, radius + CLEARANCE + NODE_RADIUS)
    if include_legacy_power:
        for _, points, _, _ in legacy_power_stitches():
            for first, second in zip(points, points[1:]):
                raster_segment(blocked, 0, first, second, POWER_TRACE_WIDTH / 2 + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
                raster_segment(via_blocked, 0, first, second, POWER_TRACE_WIDTH / 2 + CLEARANCE + NODE_RADIUS)
            center = points[-1]
            raster_circle(blocked, ROUTING_LAYERS, center, NODE_RADIUS + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
            raster_circle(via_blocked, ROUTING_LAYERS, center, NODE_RADIUS + CLEARANCE + NODE_RADIUS)
    raster_circle(blocked, ROUTING_LAYERS, (79.0, 55.49), VIA_SIZE / 2 + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
    raster_circle(via_blocked, ROUTING_LAYERS, (79.0, 55.49), VIA_SIZE / 2 + CLEARANCE + NODE_RADIUS)
    return blocked, via_blocked


def endpoint_rows():
    pads = rows("pad_geometry.csv")
    result = {}
    for net in TARGETS:
        candidates = [row for row in pads if row["net_name"] == net]
        ordered = []
        used = set()
        for designator, pad_name in ENDPOINT_ORDER.get(net, []):
            matches = [
                (index, row) for index, row in enumerate(candidates)
                if index not in used
                and row["designator"] == designator
                and row["pad_name"] == pad_name
            ]
            if not matches:
                continue
            index, row = matches[0]
            used.add(index)
            ordered.append(row)
        ordered.extend(row for index, row in enumerate(candidates) if index not in used)
        result[net] = ordered
    return result


def component_centers():
    grouped = {}
    for row in rows("pad_geometry.csv"):
        designator = row["designator"]
        if not designator:
            continue
        grouped.setdefault(designator, []).append(row_point(row))
    return {
        designator: (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
        for designator, points in grouped.items()
    }


DIRECTIONS = (
    (1, 0), (1, 1), (0, 1), (-1, 1),
    (-1, 0), (-1, -1), (0, -1), (1, -1),
)


def endpoint_escape(row, toward, centers):
    center = row_point(row)
    left, bottom, right, top = row_rect(row)
    designator = row["designator"]
    component_center = centers.get(designator, center)
    dx = center[0] - component_center[0]
    dy = center[1] - component_center[1]
    override = NET_ESCAPE_DIRECTION.get((row["net_name"], designator, row["pad_name"]))
    if override is None:
        override = ESCAPE_DIRECTION.get((designator, row["pad_name"]))
    if override is not None:
        dx, dy = override
    if override is None and (float(row["hole_mil"]) > 0 or (abs(dx) < 0.05 and abs(dy) < 0.05)):
        dx = toward[0] - center[0]
        dy = toward[1] - center[1]
    margin = CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD
    if abs(dx) >= abs(dy):
        if dx >= 0:
            return math.ceil((right + margin) / STEP) * STEP, round(center[1] / STEP) * STEP
        return math.floor((left - margin) / STEP) * STEP, round(center[1] / STEP) * STEP
    if dy >= 0:
        return round(center[0] / STEP) * STEP, math.ceil((top + margin) / STEP) * STEP
    return round(center[0] / STEP) * STEP, math.floor((bottom - margin) / STEP) * STEP


def endpoint_lead(row, toward, centers):
    center = row_point(row)
    manual = MANUAL_LEADS.get((row["designator"], row["pad_name"]))
    if manual is not None:
        return [center, *manual]
    return [center, endpoint_escape(row, toward, centers)]


def clear_escape(local, first, second):
    first_node = snap(first)
    second_node = snap(second)
    steps = max(abs(second_node[0] - first_node[0]), abs(second_node[1] - first_node[1]))
    if steps == 0:
        local[0].discard(first_node)
        return
    for index in range(steps + 1):
        ratio = index / steps
        node = (
            round(first_node[0] + (second_node[0] - first_node[0]) * ratio),
            round(first_node[1] + (second_node[1] - first_node[1]) * ratio),
        )
        local[0].discard(node)


def clear_own_pad(local, row):
    left, bottom, right, top = row_rect(row)
    margin = CLEARANCE + TRACE_WIDTH / 2
    for ix in range(math.floor((left - margin) / STEP), math.ceil((right + margin) / STEP) + 1):
        for iy in range(math.floor((bottom - margin) / STEP), math.ceil((top + margin) / STEP) + 1):
            x, y = unsnap((ix, iy))
            if left - margin <= x <= right + margin and bottom - margin <= y <= top + margin:
                local[0].discard((ix, iy))


def find_route(net, start_point, goal_point, blocked, via_blocked, own_pads, start_pad=None, goal_pad=None, centers=None):
    original_start = start_point
    original_goal = goal_point
    start_lead = [start_point]
    goal_lead = [goal_point]
    if start_pad is not None:
        start_lead = endpoint_lead(start_pad, goal_point, centers)
        start_point = start_lead[-1]
    if goal_pad is not None:
        goal_lead = endpoint_lead(goal_pad, start_point, centers)
        goal_point = goal_lead[-1]
    start = snap(start_point)
    goal = snap(goal_point)
    local = {layer: set(blocked[layer]) for layer in ROUTING_LAYERS}
    extra_guard = NET_CLEARANCE_GUARD.get(net, 0.0)
    if extra_guard:
        for row in rows("pad_geometry.csv"):
            layer = int(row["layer"])
            if float(row["hole_mil"]) > 0 or layer == 74:
                layers = ROUTING_LAYERS
            elif layer == 1:
                layers = (0,)
            elif layer == 32:
                layers = (2,)
            else:
                layers = ()
            for item in layers:
                raster_rect(local, item, row_rect(row), CLEARANCE + TRACE_WIDTH / 2 + extra_guard)
    local[0].discard(start)
    local[0].discard(goal)

    def unavailable(layer, node):
        x, y = unsnap(node)
        return not (EDGE <= x <= BOARD_W - EDGE and EDGE <= y <= BOARD_H - EDGE) or node in local[layer]

    frontier = []
    initial = (0, start[0], start[1], -1)
    heapq.heappush(frontier, (0.0, 0.0, initial))
    best = {initial: 0.0}
    parent = {}
    final = None
    while frontier:
        _, cost, state = heapq.heappop(frontier)
        if cost != best.get(state):
            continue
        layer, ix, iy, direction = state
        node = ix, iy
        forced_layer = FORCED_INTERNAL_LAYER.get(net)
        if layer == 0 and node == goal:
            final = state
            break
        for next_direction, (dx, dy) in enumerate(DIRECTIONS):
            neighbor = ix + dx, iy + dy
            escape_radius = FORCED_TOP_ESCAPE_RADIUS.get(net, 0.45 if forced_layer is not None else None)
            if escape_radius is not None and layer == 0:
                neighbor_point = unsnap(neighbor)
                near_endpoint = min(
                    math.hypot(neighbor_point[0] - point[0], neighbor_point[1] - point[1])
                    for point in (start_point, goal_point)
                ) <= escape_radius
                if not near_endpoint:
                    continue
            if state == initial and start_pad is not None:
                outward = start_lead[-1][0] - start_lead[-2][0], start_lead[-1][1] - start_lead[-2][1]
                if dx * outward[0] + dy * outward[1] < -1e-9:
                    continue
            if neighbor == goal and goal_pad is not None:
                outward = goal_lead[-1][0] - goal_lead[-2][0], goal_lead[-1][1] - goal_lead[-2][1]
                if dx * outward[0] + dy * outward[1] > 1e-9:
                    continue
            if neighbor != goal and unavailable(layer, neighbor):
                continue
            move = STEP * (math.sqrt(2) if dx and dy else 1.0)
            turn = 0.0 if direction in (-1, next_direction) else 0.12
            layer_penalty = 0.03 if layer == 1 else (0.10 if layer == 2 else 0.0)
            next_cost = cost + move + turn + layer_penalty
            next_state = (layer, neighbor[0], neighbor[1], next_direction)
            if next_cost >= best.get(next_state, float("inf")):
                continue
            best[next_state] = next_cost
            parent[next_state] = state
            heuristic = math.hypot(neighbor[0] - goal[0], neighbor[1] - goal[1]) * STEP
            heapq.heappush(frontier, (next_cost + heuristic, next_cost, next_state))
        allowed_layers = LAYER_OPTIONS.get(net, ROUTING_LAYERS if net in L3_ALLOWED else (0, 2))
        if forced_layer is not None:
            allowed_layers = (0, forced_layer)
        via_clear = all(node not in via_blocked[item] for item in ROUTING_LAYERS)
        if via_clear:
            if min(math.hypot(unsnap(node)[0] - p[0], unsnap(node)[1] - p[1]) for p in (start_point, goal_point)) >= 0.0:
                for other in allowed_layers:
                    if other == layer:
                        continue
                    next_state = (other, ix, iy, -1)
                    next_cost = cost + 7.5
                    if next_cost < best.get(next_state, float("inf")):
                        best[next_state] = next_cost
                        parent[next_state] = state
                        heuristic = math.hypot(ix - goal[0], iy - goal[1]) * STEP
                        heapq.heappush(frontier, (next_cost + heuristic, next_cost, next_state))
    if final is None:
        raise RuntimeError(f"no route for {net}: {start_point} to {goal_point}")
    states = []
    state = final
    while True:
        states.append(state)
        if state == initial:
            break
        state = parent[state]
    states.reverse()
    points = [(0, start_point[0], start_point[1])]
    for layer, ix, iy, _ in states[1:-1]:
        points.append((layer, ix * STEP, iy * STEP))
    points.append((0, goal_point[0], goal_point[1]))
    if start_pad is not None:
        points = [(0, point[0], point[1]) for point in start_lead[:-1]] + points
    if goal_pad is not None:
        points.extend((0, point[0], point[1]) for point in reversed(goal_lead[:-1]))
    simplified = [points[0]]
    for point in points[1:]:
        if len(simplified) < 2:
            simplified.append(point)
            continue
        first, second = simplified[-2], simplified[-1]
        same_layer = first[0] == second[0] == point[0]
        vector_a = round(second[1] - first[1], 6), round(second[2] - first[2], 6)
        vector_b = round(point[1] - second[1], 6), round(point[2] - second[2], 6)
        collinear = abs(vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0]) < 1e-6
        forward = vector_a[0] * vector_b[0] >= 0 and vector_a[1] * vector_b[1] >= 0
        if same_layer and collinear and forward:
            simplified[-1] = point
        elif point != simplified[-1]:
            simplified.append(point)
    return simplified


def add_plan_obstacles(blocked, via_blocked, points, narrow_segments, route_width=TRACE_WIDTH):
    for first, second in zip(points, points[1:]):
        if first[0] != second[0]:
            raster_circle(blocked, ROUTING_LAYERS, (first[1], first[2]), VIA_SIZE / 2 + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD)
            raster_circle(via_blocked, ROUTING_LAYERS, (first[1], first[2]), VIA_SIZE / 2 + CLEARANCE + NODE_RADIUS)
            continue
        key = tuple(sorted(((round(first[1], 6), round(first[2], 6)), (round(second[1], 6), round(second[2], 6)))))
        width = 0.15 if key in narrow_segments else route_width
        raster_segment(
            blocked,
            first[0],
            (first[1], first[2]),
            (second[1], second[2]),
            width / 2 + CLEARANCE + TRACE_WIDTH / 2 + GRID_GUARD,
        )
        raster_segment(via_blocked, first[0], (first[1], first[2]), (second[1], second[2]), width / 2 + CLEARANCE + NODE_RADIUS)


def power_segment_width(route, index, source_key=None):
    first, second = route[index], route[index + 1]
    endpoint_neck = first[0] == second[0] == 0 and index in {0, len(route) - 2}
    if endpoint_neck or index in POWER_EXTRA_NECKS.get(source_key, set()):
        return POWER_NECK_WIDTH
    return POWER_TRACE_WIDTH


def plan_power(blocked, via_blocked, centers):
    power_routes = []
    for net, source, target in moved_power_connections():
        key = source["designator"], source["pad_name"]
        override = POWER_ROUTE_OVERRIDES.get(key)
        branch = POWER_ROUTE_BRANCHES.get(key)
        if override is not None:
            planned = override
        elif branch is not None:
            planned = [(0, *row_point(source)), *((0, x, y) for x, y in branch)]
        else:
            planned = find_route(
                net,
                row_point(source),
                row_point(target),
                blocked,
                via_blocked,
                (source, target),
                source,
                target,
                centers,
            )
        obstacle_route = POWER_PLANNING_OBSTACLE_OVERRIDES.get(key, planned)
        add_plan_obstacles(blocked, via_blocked, obstacle_route, set(), POWER_TRACE_WIDTH)
        power_routes.append({
            "net": net,
            "designator": source["designator"],
            "pad_name": source["pad_name"],
            "target_designator": target["designator"],
            "target_pad_name": target["pad_name"],
            "route": planned,
        })
        segment_count = sum(a[0] == b[0] for a, b in zip(planned, planned[1:]))
        via_count = sum(a[0] != b[0] for a, b in zip(planned, planned[1:]))
        print(
            f"power {source['designator']}-{source['pad_name']} -> "
            f"{target['designator']}-{target['pad_name']}: "
            f"{segment_count} segments, {via_count} vias"
        )
    return power_routes


def apply_final_routes(routes, power_routes):
    for net, index in FINAL_ONLY_SIGNAL_ROUTES:
        routes[net][index - 1] = SIGNAL_ROUTE_OVERRIDES[(net, index)]
    for item in power_routes:
        key = item["designator"], item["pad_name"]
        if key in POWER_FINAL_ROUTE_OVERRIDES:
            item["route"] = POWER_FINAL_ROUTE_OVERRIDES[key]


def finalize_existing():
    routes = json.loads((ROOT / "build-cad/pcb_a10_partial.json").read_text(encoding="utf-8"))
    power_path = ROOT / "build-cad/pcb_a10_power_plan.json"
    power_routes = json.loads(power_path.read_text(encoding="utf-8"))
    for item in power_routes:
        key = item["designator"], item["pad_name"]
        if key in POWER_FINAL_ROUTE_OVERRIDES:
            item["route"] = POWER_ROUTE_OVERRIDES[key]
    apply_final_routes(routes, power_routes)
    power_path.write_text(json.dumps(power_routes, indent=2) + "\n", encoding="utf-8")
    (ROOT / "build-cad/pcb_a10_plan.json").write_text(json.dumps(routes, indent=2) + "\n", encoding="utf-8")


def main():
    blocked, via_blocked = build_base(False)
    endpoints = endpoint_rows()
    centers = component_centers()
    power_routes = plan_power(blocked, via_blocked, centers)
    power_output = ROOT / "build-cad/pcb_a10_power_plan.json"
    routes = {}
    for net in ORDER:
        pads = endpoints[net]
        if len(pads) < 2:
            raise RuntimeError(f"{net} has fewer than two pads")
        net_routes = []
        tree_points = []
        first = row_point(pads[0])
        for index, pad in enumerate(pads[1:], start=1):
            route_key = net, index
            override = None if route_key in FINAL_ONLY_SIGNAL_ROUTES else SIGNAL_ROUTE_OVERRIDES.get(route_key)
            if override is not None:
                net_routes.append(override)
                tree_points.extend(override)
                continue
            start = row_point(pad)
            if not tree_points:
                goal = first
                goal_pad = pads[0]
            elif net in {"BOOT0", "NRST"}:
                goal = row_point(pads[index - 1])
                goal_pad = pads[index - 1]
            else:
                candidates = []
                for point in tree_points:
                    if point[0] != 0:
                        continue
                    node = snap((point[1], point[2]))
                    if node in blocked[0]:
                        continue
                    open_neighbors = sum(
                        (node[0] + dx, node[1] + dy) not in blocked[0]
                        for dx, dy in DIRECTIONS
                    )
                    if open_neighbors >= 4:
                        candidates.append(point)
                if not candidates:
                    raise RuntimeError(f"{net} has no open top-layer branch point")
                if net == "ETH_NRST":
                    goal_point = min(candidates, key=lambda item: (item[2], item[1]))
                else:
                    goal_point = min(candidates, key=lambda item: math.hypot(start[0] - item[1], start[1] - item[2]))
                goal = goal_point[1], goal_point[2]
                goal_pad = None
            route_net = "NRST_TAIL" if net == "NRST" and index == 3 else net
            planned = find_route(route_net, start, goal, blocked, via_blocked, pads, pad, goal_pad, centers)
            net_routes.append(planned)
            tree_points.extend(planned)
        narrow_segments = set()
        for pad in pads:
            manual = MANUAL_LEADS.get((pad["designator"], pad["pad_name"]))
            if manual is None:
                continue
            lead = [row_point(pad), *manual]
            for first_point, second_point in zip(lead, lead[1:]):
                narrow_segments.add(tuple(sorted((
                    (round(first_point[0], 6), round(first_point[1], 6)),
                    (round(second_point[0], 6), round(second_point[1], 6)),
                ))))
        for planned in net_routes:
            add_plan_obstacles(blocked, via_blocked, planned, narrow_segments)
        routes[net] = net_routes
        (ROOT / "build-cad/pcb_a10_partial.json").write_text(json.dumps(routes, indent=2) + "\n", encoding="utf-8")
        segment_count = sum(1 for route in net_routes for a, b in zip(route, route[1:]) if a[0] == b[0])
        via_count = sum(1 for route in net_routes for a, b in zip(route, route[1:]) if a[0] != b[0])
        used_layers = sorted({point[0] for route in net_routes for point in route})
        print(f"{net}: {segment_count} segments, {via_count} vias, layers {used_layers}")
    apply_final_routes(routes, power_routes)
    power_output.write_text(json.dumps(power_routes, indent=2) + "\n", encoding="utf-8")
    output = ROOT / "build-cad/pcb_a10_plan.json"
    output.write_text(json.dumps(routes, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if "--finalize-existing" in sys.argv:
        finalize_existing()
    else:
        main()
