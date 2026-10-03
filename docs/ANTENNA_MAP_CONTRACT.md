# D1 antenna map contract for RAD-LB-006 Rev.B

The Rev.B interface consumes machine-readable antenna simulation outputs without encoding or freezing production Tx/Rx physical coordinates.

## CSV fields

```csv
case_id,frequency_hz,az_deg,el_deg,gain_tx_delta_db,gain_rx_delta_db,sigma_az_deg,sigma_el_deg,ambiguity_flag,track_usable,high_acc_usable
```

`gain_tx_delta_db` and `gain_rx_delta_db` are deltas relative to the declared Rev.A/reference antenna basis. They are added in dB bookkeeping to obtain the two-way antenna contribution.

`ambiguity_flag=1` always makes the cell unusable for TRACK projection, even if the link margin is positive.

`track_usable` and `high_acc_usable` remain separate so that gain does not silently override angle-quality limits.

## Rev.B CLI

```bash
python -m tools.rad_lb006_revb \
  --reva RAD_LB_006_REVA.json \
  --antenna D1_ANTENNA_MAP.csv \
  --case-id NOMINAL \
  --frequency-hz 78500000000 \
  --output RAD_LB_006_REVB.json
```

Rev.B is still projected evidence. Physical antenna measurement and field-range tests remain separate gates.
