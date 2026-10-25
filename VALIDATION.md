# Verification performed

- 14 deterministic tests pass: real-yield direction, nominal-yield outage independence, no latest-price leakage into regression fit, COT percentile tails and stale/history gates, dollar divergence, agreement confidence, missing weights, holdings parsing, density changes, strict LLM label validation, last-good snapshot persistence and all four API routes.
- Updated Expo iOS and Android JavaScript bundles export successfully. This is not a native install or physical-device UI test.
- Live FRED DGS10 / DFII10 retrieved through the public CSV fallback; authenticated FRED API path not exercised without a key.
- Live CFTC disaggregated COMEX Gold endpoint returned 180 records with current managed-money fields; the 156-prior-report percentile calculation executed.
- Current GLD issuer XLSX endpoint retrieved and parsed 31 latest daily holdings changes. The legacy CSV URL returned a PDF and is not used. No issuer data is included in this source package.
- IAU holdings import and WGC quarterly inputs require verified user-provided data. The unit tests cover standardized ETF CSV calculations.
- Live paid LLM calls were not performed: no model or API key configured. Topic schema and density logic were tested with fixtures; real classification quality remains unverified.
- Publisher RSS access remains dependent on host/network and feed changes. Missing topics are not replaced with sentiment heuristics.
- No hosted deployment, broker connection, trade execution, historical profitability test or claim of predictive accuracy.

## Version 2 upgrade verification

- 23 deterministic tests pass, including the original 14 plus probability normalization, confidence caps, conflict response, point-in-time rejection, missing-model abstention, synthetic training/inference end-to-end, six-horizon report persistence, /intelligence endpoint and quote freshness/closed-market gates.
- Synthetic training data exists only within a test. No market model artifact, probabilities, synthetic market history or credentials are bundled.
- Updated Expo iOS and Android JavaScript bundles export successfully. No physical-device install or visual QA was performed.
- New extended FRED driver adapters and authenticated Fed/quote/intraday imports were not live-verified in this upgrade. Existing real-yield/CFTC/GLD live checks described above belong to the earlier build, not proof of all new integrations.
- No historical gold calibration, return forecast accuracy, profitability, actual fund-decision estimation or improvement over the old model has been demonstrated.
- The current default is NO TRADE with unavailable class probabilities until the documented data/model gates pass.

## v2.1 application completion checks

- 24 backend tests pass; two Node connection tests pass.
- Full local HTTP smoke test against a running uvicorn process succeeded: /health, /regime, /positioning, /narratives, /divergences, /intelligence and /capabilities all returned HTTP 200. The live snapshot contained five factors, ten driver states and six horizons; real yields, COT positioning and dollar context were available. Flow/narrative gaps were exposed; final decision correctly remained NO TRADE. No paid classification was invoked by the smoke test.
- Expo SDK-compatible AsyncStorage installed; mobile iOS/Android exports succeed. Server URL is saved on phone; a new server is health-tested before saving. React Native physical-device installation and interaction were not performed.
- Windows/macOS launchers, Docker configuration and Expo EAS profiles included. Docker/EAS execution, signed native binaries, public hosting, user account connection and on-device testing remain external setup steps, not claimed complete.
- Improved reconnect cancellation avoids the prior shared busy flag preventing a new request after server changes. Stale display warning is independent of request-error text. Server publishes a snapshot only after its intelligence report is built.
