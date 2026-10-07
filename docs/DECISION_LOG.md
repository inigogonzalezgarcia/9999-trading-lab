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

## 2026-10-07 — Record Strategy V1 deterministic baseline

- **Decision:** Add `strategy_v1.yaml` as a new version, retaining `strategy_v0_1.yaml` unchanged. Translate the supplied rules into a fully ordered causal sequence, explicit timeouts, state transitions, invalidation reasons, and baseline execution/risk assumptions.
- **Decision:** Keep the runtime status `IMPLEMENTATION_PENDING` until the complete signal/execution engine is implemented and its automated tests pass. Do not label the implementation fully specified prematurely.
- **Decision:** Observation windows use half-open `[start, end)` intervals, per the latest edge-case rules. Window configuration rejects overlaps; event times at the end boundary are excluded.
- **Decision:** Resolve repeated Madrid local observation times to the first occurrence (earlier UTC instant), per user selection. Nonexistent times are recorded as `DST_NONEXISTENT_SKIPPED`.
- **Decision:** Prefer historical provider `spread_pips`; otherwise use only an explicitly configured fixed spread. If neither exists, retain the candidate as `SPREAD_DATA_UNAVAILABLE`, report `NO_SPREAD_DATA`, and block execution. Never invent a spread.
- **Decision:** Emit `DST_AMBIGUOUS_EARLY` with local, UTC, offset, and New York values for repeated local times; emit `DST_NONEXISTENT_SKIPPED` for nonexistent ones. Record the IANA timezone database version for reproducibility.
- **Decision:** Enable TWO_LEG_V1 as the baseline confirmation requirement; equal-high/low levels remain experimental and disabled.
- **Decision:** Do not change prior strategy runs/configuration when introducing V1.
- **Status:** Baseline rules and machine-readable configuration recorded; implementation and causal backtest validation remain pending.

## 2026-10-07 — Apply final edge-case rules

- **Decision:** Use half-open `[start, end)` windows and reject overlapping intervals at configuration load. Evaluate membership using timezone-aware instants converted to Madrid.
- **Decision:** Prefer historical spread, then explicitly configured fixed spread, else preserve the candidate with `SPREAD_DATA_UNAVAILABLE` and report `NO_SPREAD_DATA` without execution.
- **Decision:** Emit `DST_AMBIGUOUS_EARLY` and `DST_NONEXISTENT_SKIPPED`, recording local time, resolved UTC time, offset, and New York time. Include the IANA timezone database release in API output.
- **Status:** Edge-case rules and helper tests added; full V1 state machine remains implementation-pending.
