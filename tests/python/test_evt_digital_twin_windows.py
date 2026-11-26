import math
import socket
import tempfile
from pathlib import Path

from tools.evt_digital_twin.model import Scenario, TargetConfig, TwinEngine, default_scenario
from tools.evt_digital_twin.server import TwinTcpServer
from tools.hil_host.targetstate import PACKET_SIZE, decode_targetstate_v1


def test_default_scenario_has_configurable_rcs_and_speed():
    scenario = default_scenario()

    assert len(scenario.targets) == 3
    assert [target.rcs_m2 for target in scenario.targets] == [0.01, 0.10, 1.00]
    assert [target.speed_kmh for target in scenario.targets] == [130.0, 160.0, 190.0]


def test_engine_emits_valid_targetstate_for_every_enabled_target():
    scenario = default_scenario()
    samples = TwinEngine(scenario).step()

    assert len(samples) == 3
    assert {sample.track_id for sample in samples} == {1, 2, 3}
    for sample in samples:
        assert len(sample.packet) == PACKET_SIZE
        state = decode_targetstate_v1(sample.packet)
        assert state["track_id"] == sample.track_id
        speed_kmh = math.sqrt(sum(value * value for value in state["velocity_m_s"])) * 3.6
        configured = next(target.speed_kmh for target in scenario.targets if target.track_id == sample.track_id)
        assert math.isclose(speed_kmh, configured, rel_tol=1.0e-5)


def test_rcs_gain_is_ten_db_per_decade():
    assert math.isclose(TwinEngine.rcs_gain_db(0.01), 0.0, abs_tol=1.0e-12)
    assert math.isclose(TwinEngine.rcs_gain_db(0.10), 10.0, abs_tol=1.0e-12)
    assert math.isclose(TwinEngine.rcs_gain_db(1.00), 20.0, abs_tol=1.0e-12)


def test_larger_rcs_increases_snr_at_equal_range():
    scenario = Scenario(
        range_noise_m=0.0,
        angle_noise_deg=0.0,
        snr_noise_db=0.0,
        targets=[
            TargetConfig(1, "small", rcs_m2=0.01, speed_kmh=100.0, initial_range_m=300.0, course_deg=90.0),
            TargetConfig(2, "large", rcs_m2=1.00, speed_kmh=100.0, initial_range_m=300.0, course_deg=90.0),
        ],
    )
    samples = TwinEngine(scenario).step(0.001)

    assert math.isclose(samples[1].snr_db - samples[0].snr_db, 20.0, abs_tol=1.0e-6)


def test_scenario_json_round_trip():
    scenario = default_scenario()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "scenario.json"
        scenario.save(path)
        loaded = Scenario.load(path)

    assert loaded.to_dict() == scenario.to_dict()


def test_tcp_server_streams_raw_targetstate_packets():
    scenario = Scenario(
        update_hz=20.0,
        targets=[TargetConfig(11, "tcp", rcs_m2=0.1, speed_kmh=150.0, initial_range_m=250.0)],
    )
    server = TwinTcpServer(scenario, port=0)
    server.start()
    assert server.ready_event.wait(2.0)
    assert server.bound_port is not None
    data = bytearray()
    try:
        with socket.create_connection(("127.0.0.1", server.bound_port), timeout=2.0) as connection:
            connection.settimeout(2.0)
            while len(data) < PACKET_SIZE:
                data.extend(connection.recv(PACKET_SIZE - len(data)))
    finally:
        server.stop()
        server.join(timeout=2.0)

    state = decode_targetstate_v1(bytes(data[:PACKET_SIZE]))
    assert state["track_id"] == 11
