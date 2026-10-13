# Carrier IMU service

`imu_service` is the deterministic handoff state machine between the
hardware IMU data-ready capture and the SPI/DMA transfer layer.

It records the hardware DRDY timestamp before transfer, allocates a
monotonic per-sample sequence, tracks pending/active transfer state, and
counts overruns and failed transfers.

The service intentionally does not perform attitude estimation, navigation,
target tracking or control. Sensor data interpretation remains outside this
small acquisition/health layer.

The measurement/evidence stack can use the report to reject or flag sessions
with stale IMU data, transfer failures or DRDY overruns.
