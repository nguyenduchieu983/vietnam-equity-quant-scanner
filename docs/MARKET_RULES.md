# Market rules — unresolved, not implemented as production truth

The spec's board lot 100, normal price bands, T+2 settlement, fee/tax/slippage and capital caps are research assumptions requiring effective-date configuration and tests in M3/M4.

M0 does not submit, preview or simulate any order. There are no live trading credentials, broker write APIs, margin, derivatives or short selling.

Discovery:
- [DNSE post-KRX reference, April 2025](https://cdn.dnse.com.vn/dnse-news/2023/10/DNSE_Cap-nhat-quy-dinh-giao-dich-sau-KRX_2025.pdf) was accessible. It is a dated broker reference; it is not proof that every rule remains effective for the requested history.
- [TCSC reference supplied by spec](https://tcsc.vn/uploads/san-pham-dich-vu/guiding-customer-to-trade-hose-hnx-upcom-may-09-2025_1.pdf) could not be retrieved by the research tool. No content inferred.

Blockers before fill fidelity: current exchange notices; historical rule validity intervals; tick grids; exception bands; official holidays/settlement days; exact sellable time; cash availability; corporate-action handling; odd-lot venue support. No rule is marked verified merely because it appears in the spec.
