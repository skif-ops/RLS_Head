# AWR2944P profiles for the D79 R9 board

`EVT_R9_RANGE_PHASE_CALIBRATION.cfg` is a short-range calibration profile. It enables the TI range-bias and receive-channel phase measurement with a strong reflector at 1.5 m. The generated `compRangeBiasAndRxChanPhase` values must replace the identity placeholder in the operational profile.

`EVT_R9_TRIPRF_TRACKING_CANDIDATE.cfg` is a calculated three-PRF observation profile. Its three chirp periods are 30, 33 and 39 microseconds. The project-owned unwrapping code combines their aliased radial-velocity measurements for the configured interval of plus or minus 60 m/s.

The operational candidate uses all four receive and four transmit channels. The antenna geometry has 16 virtual phase centers. Eight printed patches in each RF channel form one passive series-fed subarray and do not increase the channel count seen by the AWR2944P.

The profile calculation gives about 0.94 m range resolution, 300 m beat frequency of 16 MHz and 350 m beat frequency of 18.67 MHz. These values fit the 20 MHz IF limit only as a calculated starting point. The profile has not been accepted by physical AWR2944P hardware, and memory, timing, spurious-response and detection-margin checks remain mandatory.

Neither profile authorizes production. Full-wave antenna simulation, range and angle calibration, anechoic or outdoor range measurements, thermal testing and EMC testing remain open.
