# Gold Regime Terminal

**Start here:** [START_HERE.md](START_HERE.md) walks through the finished connection screen, one-command launchers, Expo Go and hosted deployment.

**Version 2:** Read [UPGRADE_V2.md](UPGRADE_V2.md) first for the new ten-engine, six-horizon probability research pipeline, decision gates and training instructions. The original five-factor monitor below remains supporting context; it does not supply calibrated trade probabilities.

A new five-factor FastAPI backend and four-screen React Native / Expo terminal.
This replaces the previous sentiment-led architecture. No FinBERT, no headline
sentiment scoring, no broker APIs and no trade execution. News topic labels
feed an aggregate density model; they never become individual trade signals.

**Decision support only.** These are proposed heuristics, not validated causal
estimates, price predictions, profitable signals or institutional research.
A professional-looking interface does not establish an edge. Positioning and
flows may lead, coincide with or lag price; COT and WGC have reporting delays.
The build does not claim to replicate any named fund's process.

## Start with the 60% core

`backend/real_yield_engine.py`: 35% weight. Fetches DGS10 and DFII10 using the
FRED API when FRED_API_KEY is set; otherwise public FRED CSV, explicitly labelled.
Signal = clip(-(latest real yield − five-observation-earlier real yield)/0.15,
-1,+1), where .15 percentage points = 15 basis points. Momentum and acceleration
are reported. Nominal-yield outage does not invalidate available real yields.

GC=F gold futures daily closes provide a separate 252-pair log-price / real-yield
regression reference. Train ends before the test observation. Its deviation and
residual z-score are diagnostics, **not intrinsic fair value**, and do not enter
the directional score. Levels regressions can be spurious; slope sign, stability,
residual stationarity, structural breaks and futures rolls need validation.
This is a conditional reference, not a validated gold valuation model.

`backend/positioning_engine.py`: 25% weight. CFTC Socrata dataset `72hh-3qpy`,
contract `088691`, disaggregated futures-only, fields
`m_money_positions_long_all`, `m_money_positions_short_all`, `open_interest_all`.
Net = longs minus shorts, in contracts. Latest observation percentile uses 156
prior reports, with ties receiving half credit. Latest report is excluded from
its own reference history. >85 maps linearly from 0 to -1; <15 maps linearly
from +1 to 0; 15–85 is zero. At least 157 weekly observations required. Gaps are
rejected instead of silently calling a shorter sample a 156-week history.
Crowding can persist; extreme longs do not imply an imminent reversal.

Official references:
- https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- https://fred.stlouisfed.org/series/DFII10
- https://publicreporting.cftc.gov/stories/s/Disaggregated-Futures-Only/ubmb-6exi/
- https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm

## Remaining factors

| Factor | Weight | Implementation |
|---|---:|---|
| Real yields | 35% | Five-session DFII10 change; nominal yield / conditional valuation context |
| Positioning | 25% | 156-prior-report managed-money net percentile |
| Flows | 20% | Two-quarter WGC direction + GLD/IAU holdings changes |
| Dollar | 10% | DXY breakout/breakdown only when USD and real-yield directions diverge |
| Narratives | 10% | Structured LLM topic classification → density / density shift |

Your explicit formula takes precedence over the prose ordering that placed
positioning and flows ahead of macro. Real yields remain the largest individual
factor, with positioning + flows totaling 45%. The separate prior Earth model
and earlier news scanner are not part of this new project's calculations.

Flow factor: central-bank sign is +1 for two positive reported quarters, -1 for
two negative quarters, otherwise 0. ETF sign = clip(combined GLD/IAU
20-observation holdings change in tonnes / 20, -1,+1). Flow = half each. Both
ETF series and WGC data must be fresh before the 20% factor is scored; otherwise
it is unavailable. Central-bank buying versus ETF outflows is shown separately.
Holdings changes are a proxy for flows, not exact subscriptions; fees affect
physical holdings. This is not a claim that a floor exists.

Dollar: latest daily DXY close versus the previous 20 daily closes, excluding
latest. Five-observation USD return must have opposite sign to the five-session
real-yield change, with minimum .1% USD and 1bp yield moves. Otherwise factor
is zero. CNH=X is requested as USD/CNH context and separately labelled if missing;
it does not gate DXY. Daily close breakout is not an intraday breakout.

## Install and run backend

Python 3.11+; 3.12 recommended. From the extracted project:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Set environment variables; .env.example is a reference and is NOT auto-loaded.
export FRED_API_KEY=your_fred_key
export DATA_DIR=data
# Optional narrative integration:
export OPENAI_API_KEY=your_api_key
export OPENAI_MODEL=your_supported_public_model_id
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Windows environment syntax: `$env:FRED_API_KEY="your_key"`, etc.
`/docs` lists the API; `/health` confirms process readiness. The initial regime
may take time while sources load. No credentials have been configured by this
build, and no paid inference has been performed.

Routes: GET `/regime`, `/positioning`, `/narratives`, `/divergences`, `/health`.
All data routes share the same five-minute snapshot. A background task polls
while the process runs. No scan button. The phone refreshes while foregrounded,
and when it resumes. A sleeping free host will not collect news while asleep.
Use a non-sleeping service for continuous narrative history.

## Data imports and lineage

All factor results include source, fetched_at, observed_at where supplied, and
warnings. Article rows preserve publication time and first_seen. Model labels
preserve model ID, classification timestamp, confidence and reason. COT and daily
Yahoo/FRED data do not reliably supply actual release timestamps: published_at
is null rather than pretending observation date is publication date. This is
adequate to inspect current source freshness, **not** a point-in-time backtest.

Freshness: five calendar days for daily yields/prices/holdings; ten days for
COT report date; 150 days for quarterly WGC period end. Actual release delays
can violate these tolerances and correctly flag data as stale. Last-good raw
snapshots persist in SQLite. Fetch failure returns stale data for inspection,
with signal null. Missing/stale weights are never reassigned to other factors.

Put verified manual files in DATA_DIR, following the empty templates:

- `gld_holdings.csv`, `iau_holdings.csv`: `date,tonnes` in ISO date format,
  at least 22 daily observations. Manual data takes precedence over URLs.
- `wgc_quarterly.csv`: `period_end,net_tonnes,published_at,source_url`, at least
  two reported quarters. Publication timestamps require timezone. Rows not yet
  published, or future periods, are excluded. Use comparable, aggregate official
  sector net purchases, not a mixture of country reserve levels and global flows.

WGC source: https://www.gold.org/goldhub/data/gold-reserves-by-country .
IAU issuer: https://www.ishares.com/us/products/239561/ishares-gold-trust-fund .
The current GLD issuer XLSX archive is parsed automatically (openpyxl); its dated holdings are converted to the same internal format. No issuer dataset is bundled with this source project. Check the issuer archive usage terms before redistributing data. The default GLD issuer fetch is attempted automatically. IAU requires a verified
CSV import or IAU_HOLDINGS_URL; GLD_HOLDINGS_URL can override the default.
No ETF price or trading volume is substituted for holdings.

Respect source access/licensing terms. Free public endpoints can change or block
requests. The templates are deliberately empty: no invented market inputs.

## LLM narrative engine

An OpenAI-compatible structured-output integration uses the public OpenAI Chat
Completions endpoint with strict JSON schema. Set an actual model ID that supports
this API in your account. Internal product names such as “GPT-5.6 Sol” are not
assumed to be public API model IDs. A model is not selected or billed by default.
This build implements this one provider; Gemini is not implemented.

Ten allowed regime labels are those in your spec. `null` means irrelevant or
ambiguous: the model is never forced to invent a matching regime. Schema:
`{regime, confidence, reason}` per input, with validated membership and certainty
0–1. Certainty describes topic classification, not directional reliability.
No tool execution, arbitrary URL retrieval or instructions from headlines are
allowed in the classification prompt. Invalid/refused outputs make the narrative
factor unavailable. There is no FinBERT or keyword-classification fallback.

Publishers: Reuters, CNBC, ForexLive and Investing RSS, with allowlisted source
IDs and configurable `RSS_*_URL` overrides. Feeds may fail; source status is
reported. A bounded sample is used (250 entries/feed, 200 deduplicated stories per
refresh). This is not exhaustive world-news coverage. Near-duplicate syndication
is reduced within fetches and across the recent archive. Related but differently
worded articles can still overlap and distort density; source count and volume
must be audited before interpreting a cluster as independent consensus.

Labels persist in SQLite. Default budget per five-minute refresh is at most 40
previously unlabelled articles in batches of 20. Set MAX_CLASSIFICATIONS_PER_REFRESH
lower, including zero, to control calls. This is a per-refresh cap, **not a daily
spend limit**: configure provider billing limits and monitor usage. Keep keys on
the backend. Existing labels retain their model provenance; changing the model
does not silently relabel history. Version/isolate archives before comparing
classifiers. Without a configured model, the clusters are visibly unclassified.

Densities use all deduplicated relevant articles in the window as denominator;
unknown/low-certainty (<.6) labels remain in denominator but in no cluster.
6/12/24h windows are reported, and 24 three-hour bins form the 72h stacked area
chart. Empty bins are unobserved, not evidence of a neutral narrative. Initial
RSS backfill has publication dates but was only observed at first_seen.

Narrative signal requires >=20 articles in both latest 24h and previous disjoint
24h, >=60% classified in each, and >=2 healthy publisher feeds. FED_HAWKISH >30%
and increasing by >5 percentage points contributes bearish pressure; FED_DOVISH
uses the symmetric condition. GEOPOLITICAL_RISK and DEBT_DEBASEMENT each >=15%
produce the requested bullish combination hypothesis. Not all ten topic labels
have automatic directional mappings; their density remains visible. No assertion
is made that this combination explains a specific historical gold rally.
A historical narrative percentile is not computed from a 72h archive; alerts do
not invent a “90th percentile” label without a proper long baseline.

## Aggregation, confidence and divergence

Final = .35 real + .25 positioning + .20 flows + .10 dollar + .10 narrative.
Bias thresholds: >.15 bullish, <-.15 bearish, otherwise neutral. Missing inputs
contribute zero with unchanged weights. Directional output requires fresh real
yields AND positioning, plus >=60% available weight. A score under missingness
must always be read alongside coverage; absence is not neutral evidence.

Confidence = absolute difference between counts of positive and negative active
factors divided by count of active factors, multiplied by available total weight.
Active means |signal|>.05. Thus 3 aligned vs 2 opposed gives 20% with full coverage;
all five aligned reaches the legacy cap of 85% (v2 confidence policy). Neutral factors do not vote. This requested agreement
measure can be high for small aligned signals; it is not calibrated win probability.

If |real|>.7 and |narrative|>.5 and signs conflict, label Divergent / Stand Aside
and return a macro-vs-narrative alert with lineage. A weighted total that opposes
a strong real factor also suppresses directional bias as Divergent. News alone
cannot flip the strong real-yield desk label. If other factors dominate together,
that disagreement is surfaced rather than hidden. Dollar only fires under the
specified divergence filter to reduce, not eliminate, correlated double-counting.

Other alerts: real yields rising with reported central-bank buying; central-bank
buying vs ETF outflows; bearish narrative with COT percentile below 15. These are
research hypotheses, not demonstrated alpha, trade commands or profit guarantees.

## Run on your phone

The included project targets Expo SDK 58, React 19.3 and React Native 0.88, with
matching react-native-svg and react-native-chart-kit. Use compatible Expo Go or
a development build. If Expo Go requires a different SDK, create a current blank
Expo project, copy App.js, screens/ and theme.js, and install compatible chart
packages with Expo; do not mix React Native versions between SDKs.

```bash
cd mobile
npm ci
npx expo install --fix
npx expo start --lan
```

Open the QR code with compatible Expo Go on iOS/Android. Tap Server in the app
and enter `http://YOUR_COMPUTER_LAN_IP:8000`. Use the computer's LAN address, not
localhost; phone and computer need the same Wi-Fi, and port 8000 must be allowed
through the firewall. For HTTPS across networks, run `ngrok http 8000` and use
its HTTPS backend URL. Expo's JS-server tunnel is separate from this API tunnel.
If iOS blocks cleartext local traffic, use HTTPS. Native transport configuration
in app.json applies to native builds, not the installed Expo Go binary.

For a persistent default, set EXPO_PUBLIC_BACKEND_URL before starting Expo.
No API keys belong in EXPO_PUBLIC variables. Server input is tested and saved on the phone with AsyncStorage in v2.1.
If a refresh fails, previous results stay visible with a red stale-warning banner
and their original timestamps. A server change clears data from the old host.

Screens:
1. Regime Dashboard: auto-updated label, bias, coverage, agreement confidence,
   weighted factor bars and tap-to-expand lineage. No BUY/SELL buttons.
2. Positioning & Flows: net contracts history, current percentile with 15/85 band,
   GLD/IAU holdings-change charts and published quarterly purchase pace.
3. Narrative Clusters: SVG stacked area (ten topics; chart-kit is used for desk
   line charts), density legend and tap-through article evidence. Unknown articles
   leave unfilled area. Publisher errors remain in the API.
4. Divergence Alerts: current conditions with contributing sources and timestamps.

## Deploy backend

No hosting account, public deployment, native install or API credential setup is
performed automatically by this source build.

Render: connect your repository as a Python Web Service, root directory `backend`,
build `pip install -r requirements.txt`, start
`uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`, health path `/health`.
A root `render.yaml` provides these settings. Select the free instance if your
account currently offers it. Add FRED_API_KEY and optional LLM keys/model as host
secrets. Put verified CSV data in the deployed DATA_DIR, respecting licenses.
Point the phone at the resulting HTTPS URL.

Render free services sleep after inactivity and use ephemeral storage. They
cannot provide reliable 72-hour continuous sampling or durable SQLite state.
For production, use persistent disk / managed database and an always-on process,
and change DATA_DIR to the mounted persistent path. Do not assume free means
24/7 collection. See https://render.com/docs/free .

Railway: connect the repository, set root `backend`, use the same build/start
commands, set secrets, mount persistent storage and generate an HTTPS domain.
Railway has trial / usage-based plans; verify cost and storage terms rather than
assuming permanent free hosting: https://railway.com/pricing .

Run one worker: SQLite archives and the in-process snapshot/refresh lock are not
a multi-worker job coordinator. At larger scale use a separate ingestion worker,
central database and job locking. Public endpoints are unauthenticated; before
sharing widely, use gateway rate limits/private access and appropriate TLS.
CORS is not authentication. Health readiness indicates process state, not source
completeness. The terminal displays coverage separately.

## Backtest framework specification: prove the regime labels matter

The current unit tests establish implementation behavior, **not forecasting
performance**. Backtesting must precede claims of alpha or live EA filtering.

1. **Point-in-time event store.** Persist each raw provider payload with source,
   observation period, actual publication timestamp, first ingestion timestamp,
   revision/vintage, hash, transformation version and factor values. Replay only
   information published AND ingested by each decision timestamp. Use ALFRED/FRED
   vintages and release timestamps; do not replay today's revised history as if
   known earlier. COT Tuesday positions cannot enter Tuesday's prediction: use
   actual release times, including shutdowns/holiday delays, not assumed Fridays.
   WGC quarters enter on actual publication, not quarter-end. ETF holdings enter
   after issuer publication, not daily candle start. Record source outages too.
2. **Targets before tuning.** Pre-register next 24h, 5-session and 20-session
   executable gold returns (with instrument/timezone/session definitions). Define
   range labels by a volatility-scaled deadband estimated only on prior data.
   Separate regime classification from expected returns and trade execution.
   Gold spot and rolled futures need separate datasets and roll/carry treatment.
3. **Walk-forward design.** Fit any regression and select thresholds only in
   rolling training windows; reserve calibration and untouched chronological test
   windows. Purge/embargo overlapping targets. Cover QE/taper, COVID liquidation,
   inflation/rate shocks, dollar squeezes and accumulation regimes when data is
   available. Do not label missing eras with future classifications. Report each
   regime separately as well as aggregate results.
4. **Narrative replay.** Use a timestamped historical news archive with stable
   deduplication, full 72h warm-up, source coverage and model/prompt version. A
   contemporary LLM can know subsequent outcomes; test potential temporal leakage
   and compare to a frozen classifier trained only on prior text. LLM reasons and
   confidence are not target probabilities. Keep publisher mix and missingness
   explicit so a new feed does not masquerade as a narrative regime shift.
5. **Baselines and ablations.** Compare to unconditional gold returns, always-flat,
   simple five-session real-yield direction, USD-only, each factor alone and the
   no-narrative blend. Test contribution of positioning/flows after controlling
   real yields/USD. Compare dollar divergence filter versus unfiltered DXY.
   Compare strong-real narrative conflicts versus non-conflicts; test the
   “fade narrative” hypothesis, not assume it. Use a separate baseline for
   central-bank/ETF divergence and persistence of COT extremes.
6. **Evaluation.** Directional balanced accuracy and confusion matrices, sample
   count, average/median forward returns, drawdown if translated into a strategy,
   turnover, cost sensitivity and block-bootstrap confidence intervals. For
   fitted bull/bear/range probabilities report Brier score, log loss, reliability
   diagrams and calibration drift. Agreement confidence is not a probability and
   must not be evaluated or advertised as a calibrated probability without a
   separate mapping fitted in training data. Correct for multiple tested rules.
7. **Instrument and timing realism.** No same-close execution from after-close
   holdings/yield updates. Use next available tradable observation, spreads,
   slippage, financing and futures rolls where relevant. No broker matching or
   EA V8 performance is established by this app. Publish source-level delays,
   stale exclusions, available-weight distribution and abstention frequency.
8. **Go/no-go.** Predefine minimum samples per regime, maximum calibration error,
   stable improvement over simple real-yield baseline after costs, and acceptable
   drawdown/coverage degradation. Reject or simplify the model if labels do not
   precede meaningful out-of-sample differences. Run prospective paper monitoring
   before changing any live strategy. Freeze weights before the final test.

## Local checks

```bash
cd backend
python -m unittest discover -s tests -v
python -m compileall -q .
cd ../mobile
npx expo export --platform android --platform ios
```

See VALIDATION.md for the checks actually performed and remaining integration gaps.
