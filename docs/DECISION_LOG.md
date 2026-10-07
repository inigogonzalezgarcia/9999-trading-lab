# Decision log

## 2026-10-07 — Keep strategy status partial

- **Decision:** Strategy and execution remain disabled while any required rule is TBD.
- **Reason:** The discretionary method still leaves pullback, zone boundaries, two-leg thresholds, and fill details unresolved. Inventing these would produce evidence about a different strategy.
- **Status:** Adopted.

## 2026-10-07 — Store internal timestamps at candle close

- **Decision:** Internal candle `timestamp` and `available_at` represent the close/availability time. Source timestamps are converted according to `config/data.yaml`.
- **Reason:** A strategy event must not consume a candle before it is complete. Source files commonly label bar opens; their close availability is one interval later.
- **Status:** Adopted; source-label convention remains configurable and is recorded per import.

## 2026-10-07 — Reject duplicate normalized timestamps

- **Decision:** Reject duplicate candle timestamps after timezone normalization; do not keep an arbitrary row.
- **Reason:** Silently choosing one duplicate can alter price history and reproducibility.
- **Status:** Adopted.

## 2026-10-07 — Research hypotheses are not facts

- **Decision:** Record proposed 2/2 fractals, pullback context, ATR displacement, sweep reclaim, and two-leg protocol with explicit labels.
- **Reason:** These are measurable hypotheses from the prompt and require independent testing; several details remain TBD.
- **Status:** Adopted; dependent signals remain disabled.
