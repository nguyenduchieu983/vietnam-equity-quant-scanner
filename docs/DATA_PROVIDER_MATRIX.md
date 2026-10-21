# Provider discovery — checked 2026-10-20

No live account, credentials, entitlement proof or license grant was supplied. **BLOCKED: PROVIDER_CREDENTIALS**. Do not equate public documentation with permission to retrieve or redistribute data.

| Provider | Version/evidence | Coverage/depth | Adjustment/index | Quotas/cost/rights | Implementation |
|---|---|---|---|---|---|
| Fixture | Local fixture-v1 | 3 invented stocks, 2 exchanges, 1 session | Synthetic VNINDEX; no actions/factors | Project test data; no market claim | Implemented, DEMO only |
| SSI | FastConnect V3; release notes show v3.3.1 dated 2026-10-14 | FAQ describes daily OHLC since instrument trading began; account coverage untested | Corporate Actions API added in v3.3.1; history completeness untested | Entitlement, limits, pricing, redistribution and retention require account review | Not connected |
| DNSE | Public market-data documentation opened | Actual permitted universe and depth untested | Adjustment/index coverage unverified | Requires entitlement and rate-limit confirmation | Not connected |
| vnstock | Public repository opened; package not installed | Source-dependent; history not tested | Must inspect selected adapter and action provenance | Do not assume code license grants market-data rights; personal research only pending terms review | Not connected |

Sources:
- [SSI overview](https://developers.ssi.com.vn/docs/getting-started/overview)
- [SSI historical-data FAQ](https://developers.ssi.com.vn/docs/faq/market-data)
- [SSI release notes](https://developers.ssi.com.vn/docs/api-reference/release-notes)
- [DNSE market data](https://developers.dnse.com.vn/docs/dnse/market-data/)
- [vnstock repository](https://github.com/thinh-vu/vnstock)

Before M1 real ingestion: capture authorization, API version, verified request/response samples, units, timezone, finality signal, revision policy, delisted coverage, missing-bar behavior, retry-after semantics, numeric rate/concurrency cap and legal retention. Never silently mix providers or adjusted/raw histories.

PrimeVue verification: [installation](https://primevue.dev/installation/) and [styled themes](https://primevue.dev/theming/styled/) checked before implementation. Latest v5 displayed an invalid-license banner during visual QA. Final selection is **PrimeVue 4.5.5 + themes 2.0.3**, both declaring MIT in registry metadata and using the same `@primeuix/styled` 0.7.4 generation. Configuration follows [the v4 styled-mode documentation](https://v4.primevue.org/theming/styled/). No competing component library or license bypass is used.

Local M1 history adapter: synthetic-history-v2, 8 invented stocks + synthetic
VNINDEX, weekday sessions 2022-01-03..2026-10-19, delayed listing and delisting.
Deterministic content hash and immutable quality snapshot; all labels DEMO.
This is test data generated locally, not an additional market data provider.

2026-10-21: separate offline real research adapter successfully fetched VNDIRECT
public finfo daily raw/adjusted prices, VNINDEX and corporate actions for a
frozen 100-stock cohort, plus current Vietcap sector metadata. This is local
personal research with provisional quality, not a production entitlement or
redistribution claim. Raw snapshots remain ignored. See
[real S1 report](REAL_S1_BACKTEST_2026-10-21.md) for evidence and limitations.
