# Gold Intelligence v2 — driver-first probability research pipeline

This upgrade adds a training/inference path, ten driver-state adapters, a
contradiction review, six independent horizons, historical analog return
asymmetry, confidence caps and conservative execution gates. It does not make
this system the most accurate gold forecaster. No evidence supports that claim.
It implements an auditable baseline that can be rejected when it fails.

**No trained market models or invented probabilities are bundled.** Until proper
historical data, calibration, held-out validation, current inputs and execution
evidence exist, the final decision remains NO TRADE. Missing probabilities are
null, never a fake 33/33/34 split, and confidence is 0 when a model is unavailable.
A model that fails holdout gates may expose explicitly unvalidated research
probabilities; it cannot qualify a trade. A single successful holdout is not
proof of generalization, profitable execution or causal capital-flow prediction.

## New files

- `backend/driver_engines.py`: ten measured driver states with lineage.
- `backend/probability_model.py`: chronological analog models, calibration,
  held-out metrics, training CLI and inference.
- `backend/decision_engine.py`: adversarial evidence, six horizons, regime
  candidate, conflict severity, asymmetry and NO TRADE gates.
- `backend/tests/test_probability_upgrade.py`: probability and readiness tests.
- `backend/data/*.template.*`: empty input contracts; no fabricated market data.

`GET /intelligence` returns the new report. `/regime` also includes it under
`intelligence`, allowing the updated mobile dashboard to lead with the report.
Previous positioning/flow, narrative and divergence screens remain available.
The earlier five-factor monitor is shown below the new report as supporting
state; its agreement confidence is separate and is not the new forecast confidence.

## Ten engines and remaining scope

| Engine | Connected state / proxy | Limitation |
|---|---|---|
| USD domination | DXY five-observation change | No direct global funding/flow observation |
| Global liquidity | WALCL four-week direction; reserves/M2 context | US proxy; no global aggregate, collateral or swap book |
| Real yield | DFII10, DGS10, conditional gold regression | Daily observations, not intraday yields |
| Bond market | DGS10 momentum and DGS2 context | No actual Treasury fund-flow feed |
| Fed expectations | Verified `fed_path.json` import | Futures-derived distribution must be supplied |
| Risk sentiment | VIX and high-yield credit-spread changes | Stress can cause gold liquidation |
| Inflation | T10YIE breakeven change | No live inflation swaps/consensus surprises |
| Recession | UNRATE and INDPRO changes | No calibrated recession probability |
| Positioning | Managed-money COT percentile | Weekly/publication delay; not current fund trades |
| Technical | Five-observation gold momentum | ATR, order flow and entry location remain unavailable |

All feature values use a documented gold-support state between -1 and +1. They
are explanatory inputs, not probabilities. A high breakeven is not assigned an
immutable gold effect: the conditional mapping is learned from historical
labels. These proxies cannot directly forecast which named capital pools will
buy gold. Macro fund decision probabilities remain unavailable without an
observable manager-position dataset. The app never claims to know the actions
of the world's twenty largest funds.

Fed file schema: `published_at` (timezone-aware), `meeting_date`, `source_url`,
`probabilities` containing cut/hold/hike fractions totaling 1. A stale/future
publication is rejected. Use an actual authorized futures-derived distribution;
do not substitute an LLM opinion or a FRED policy-rate level. This input is a
market-implied next-meeting distribution, not a separately calibrated objective
probability. Live data sources still require appropriate licenses and keys.

## Forecast drivers before gold — without stacking leakage

Each horizon has its own JSON artifact: `1h.json`, `4h.json`, `24h.json`,
`5d.json`, `20d.json`, `60d.json`, stored in MODEL_DIR (default DATA_DIR/models).
The model is a deliberately transparent nearest-analog baseline, not a claim
of optimal architecture. Ten normalized measured states feed five independent
three-class models for future USD, real yield, Treasury yield, Fed rate and
liquidity direction. These calibrated path distributions feed the gold model,
alongside risk/inflation/recession/positioning/technical states. No horizon is
forced to agree with another.

For driver paths, `bull` means the driver rises, `bear` means it falls, and
`range` means inside a predeclared deadband. Thus a bullish real-yield path is
usually adverse for gold; it is not labelled bullish gold. Fed path up means
rates/path repricing higher. Gold classes describe gold returns.

Segments in chronological decision-time order:

1. First 30%: fit driver analog models.
2. Next 10%: select each driver's probability temperature.
3. Next 20%: fit gold model using forecasts from the already frozen driver models.
4. Next 20%: select the gold probability temperature.
5. Final 20%: evaluate all models against their training-frequency baselines.

Rows whose outcomes would not yet be known by the next segment's first decision
are purged. Each segment requires at least 60 retained rows. This prevents gold
training from using driver predictions fitted on those same gold-training
outcomes. No test-set temperature selection occurs. The training executable
reports test results once: do not repeatedly tune and re-use the same test set.
A proper deployment still requires rolling validation and a further untouched
prospective period per the original README backtest specification.

Analog probabilities use 31 nearest standardized states, inverse-distance weights
and additive smoothing, followed by one calibration temperature selected from a
fixed grid on calibration data. Features are scaled with training data only.
An RMS standardized distance >2 is an out-of-support warning. This is a simple
predeclared gate, not a demonstrated distribution-shift detector.

Eligibility requires every gold/driver final-test model to have >=100 observations,
>=20 examples per class, multiclass Brier better than its training-frequency
baseline by >.01 and top-label ten-bin ECE <=.10. ECE alone is not sufficient
validation; report reliability plots, uncertainty intervals, regime breakdowns
and strategy costs before interpreting a model as deployable. The code's
`validated_holdout` status means these narrowly specified checks passed; it does
not mean independently audited, institutionally approved or profitable.

## Train with actual point-in-time data

`backend/data/training.template.csv` lists the required columns. Provide a
separate file per horizon; at least 1200 rows each, strictly chronological and
unique decision timestamps. Do not fill it with synthetic data to obtain live
model status. Synthetic data is used only by a unit test, never saved as a model.

- timestamp: timezone-aware decision time.
- features_known_at: latest publication/ingestion time of every feature in row;
  must be <= decision time. The feature values must use the same transformations
  and source-cadence semantics as live `driver_engines.py`.
- outcomes_known_at: when every forward target outcome was observable; must be
  after decision, no later than now, and must respect the horizon/session calendar.
- horizon: exactly one supported horizon throughout the file.
- source_manifest: path/identifier of immutable raw inputs, release/vintage data,
  feature versions, target definitions, deadbands and cost assumptions.
- regime: historical point-in-time candidate regime, never retrospectively
  relabelled with future outcomes.
- gold_return: forward tradable gold fractional return for that horizon.
- ten state columns: real_yield, usd, liquidity, bond, fed, risk, inflation,
  recession, positioning, technical, finite values in [-1,1].
- six labels: usd_label, real_yield_label, treasury_label, fed_label,
  liquidity_label, gold_label; each is bear/range/bull under pre-registered,
  horizon-specific deadbands estimated only from preceding data.

The loader can validate timestamp ordering and feature ranges. It cannot prove
that a supplied manifest is truthful or that labels correspond to their stated
horizon. Audit those semantics, intraday session calendars, COT release dates,
FRED vintages, outcomes and target deadbands separately. No automatic download
of revised history is presented as a point-in-time training dataset.

Example, from backend:

```bash
python probability_model.py /absolute/path/actual_24h_history.csv \
  --horizon 24h --output data/models/24h.json
```

Repeat for all horizons. The artifact stores data hash, calibration parameters,
training states, model version, test metrics, class counts and historical regime/
USD-real-yield-Fed conflict-pattern evidence. Artifacts older than 90 days are
rejected. Parameter retraining policy and prospective drift review still require
research decisions; age is not a substitute for drift detection.

## Contradiction and confidence

Both strongest cases are constructed from opposing measured, source-linked
states. Relative evidence weights are real .30, USD .25, Fed .15, bonds .10,
liquidity .08, risk .03, inflation .03, recession .02, positioning .03 and
technical .01. These weights rank arguments and measure conflicts; they do not
produce fake class probabilities. Conflict severity = twice the smaller signed
evidence mass / total absolute evidence mass, from zero to one. It is not an
event probability.

Core Fed/USD/debt-fiscal topic evidence is retrieved from the verified narrative
archive for review; geopolitical-only noise does not enter the new direction
model. This engine retrieves contradictions among connected data, not every
potential disconfirming fact on Earth. The report exposes source gaps. Surviving
an argument does not earn an arbitrary numerical probability bonus.

Confidence = the larger directional gold probability × (1 − conflict severity)
× coverage, capped at 95. It cannot exceed 85 unless the predicted USD, real-yield
and Fed paths all support the selected gold direction by >.10 net up/down
probability difference. All ten drivers must be available to produce model
estimates, so live coverage is one at that stage. Confidence is a conservative
policy score distinct from the displayed calibrated class probabilities.

Held-out regime and USD/real-yield/Fed sign-pattern tables can describe which
side historically won; fewer than 30 matching test observations returns
insufficient evidence. Those tables are descriptive frequencies, not causal
proof. No rule assumes that real yields always win through crises.

## Execution and abstention gates

Immediate decision uses the 1h model only. A 5d buy can coexist with a 1h sell;
long-term views never fill an intraday data gap. Every horizon retains an
independent research distribution, but trade action is withheld if any gate fails:

- Missing/stale drivers, model absent/expired/schema mismatch, or failed holdout
  calibration/baseline checks.
- Current features outside analog support.
- Directional probability <.60 or lead over the runner-up class <.15.
- Conflict severity >.50 or conflict-adjusted confidence <55.
- Directional analog mean return <= a fixed conservative 10bp cost hurdle.
- Strong observed real-yield factor (absolute >.7) opposes the proposed trade.
- No verified open-market XAUUSD quote <=60 seconds old with spread <=5bp.
- 1h/4h require all ten current features to have an authorized intraday update
  <=15 minutes old, using the documented `intraday_features.json` schema. The
  default daily/weekly source stack never passes these intraday readiness gates.

`market_quote.json` is an authorized data-feed import, NOT a broker API. Required:
symbol=XAUUSD, timestamp, source_url, market_open boolean, positive bid <= ask.
The app does not fabricate a session or trust a stale website quote. Importer
accuracy, clock synchronization, market-open truth and data licensing must be
verified. Templates are empty and deliberately cannot pass gates.

Intraday overrides must use the same features as the corresponding training
model, not relabel old COT/monthly data as new observations. Carry-forward of
slow data requires a documented training-compatible convention; otherwise
leave unavailable. Each override includes engine, gold_support, known_at,
source_url and reason. No paid intraday feed is configured by this build.

Asymmetry displays empirical 10th/median/90th forward returns from nearest
historical gold-training analogs, plus upside/downside ratio and mean. These are
unweighted descriptive analog quantiles; they are not guaranteed stops/targets
or a calibrated predictive interval. The fixed cost hurdle is a conservative
policy default and not broker-specific execution modelling. Trade location is
unavailable until an entry-location model and intraday structure are connected.

## Persistence, UI and limitations

Reports are stored in SQLite with full source-linked states for prospective
audits. The mobile dashboard shows six horizons, both adversarial cases,
conflict severity, driver path distributions, analog asymmetry, counterevidence
and invalidation. The server continues refreshing connected inputs on its
existing five-minute schedule while running. A sleeping free host cannot build
continuous evidence, and ephemeral storage loses the audit history.

Do not confuse successful unit tests with market validation. This upgrade does
not include trained historical gold models, a verified live Fed futures path,
paid intraday feeds, an official forward calendar, quantified named-fund
position/decision probabilities, optimized entry location, calibrated recession/
regime probabilities or demonstrated improvement over the earlier system.
There are no orders or broker connections. Protecting capital means reporting
these absences and withholding a trade, not manufacturing certainty.
