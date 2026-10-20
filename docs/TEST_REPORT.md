# M0 test report — 2026-10-20

This report is not an M0–M4 acceptance certificate.

## Passed

| Check | Command / evidence |
|---|---|
| NestJS + Vue production build | `npm run build`; Vite 6.4.4; final PrimeVue 4.5.5 + Aura 2.0.3; largest JS chunk ~429 kB before compression |
| TS typecheck | `npm run typecheck`; API tsc and web vue-tsc |
| API unit tests | `npm test`; 2 passed (sort allowlist, invalid mode fail-closed) |
| Python lint | `.venv/Scripts/ruff.exe check apps/quant-worker/quant apps/quant-worker/tests`; all checks passed |
| Python types | `.venv/Scripts/mypy.exe apps/quant-worker/quant`; 5 source files passed |
| Python + DB integration | Linux Python 3.12.13; `QUANT_INTEGRATION=1 python -m unittest discover -s apps/quant-worker/tests -v`; 8 passed |
| Migrations | `python -m quant migrate` on native PostgreSQL 18.6; repeat invocation checksum validated |
| Native API/worker smoke | `QUANT_TEST_NODE=$PWD/.runtime/node-v22.19.0-linux-x64/bin/node QUANT_TEST_PYTHON=$PWD/.runtime/linux-venv/bin/python bash infra/scripts/test-native-slice.sh`; PASS |
| Dependency audit | Final `npm install --ignore-scripts` after tool updates: 324 packages, 0 vulnerabilities |
| TypeScript ESLint | `npm run lint`; passed (Vue templates are not linted by this configuration) |

Native smoke asserts: unauthenticated 401; login; DB-backed DEMO count; worker
heartbeat; bad pagination 400; duplicate ingestion request returns same job ID;
worker completes; scans empty; regime UNKNOWN. It never asserts fabricated rankings.

Python tests assert Decimal/provenance, invalid OHLC, nonfinite/fractional/negative
values, legitimate zero volume, missing benchmark/symbols, non-final bars,
fixture label, repeated ingestion with zero new bars and retained raw provenance.

## Resolved failures / environment boundaries

- Initial sandbox build could not create `dist/assets` (EPERM); rerunning the exact
  build with approved filesystem access passed.
- LibreOffice's Python could not create a venv; used independent Python 3.12 runtime.
- Windows localhost PostgreSQL was not the WSL database; authentication failed.
  Migrations/integration were moved entirely into WSL, then passed.
- npm audit initially found high severity older dependencies; updated NestJS,
  Swagger, Vue, Vite and js-yaml. No forced major update was used.
- WSL reports user-session startup warnings. Native processes ran; this does not
  establish PM2/systemd user service or reboot recovery.

## Not yet verified

Clean supported-host provisioning, production deployment, Nginx/TLS, PM2 startup,
systemd worker recovery, backup restore, reboot, real provider failures/retries,
feature goldens, strategies, paper accounting, backtest realism, walk-forward,
performance and complete acceptance criteria AC01–AC17.

Python production/development transitive locks with hashes are included.
`uv pip sync --require-hashes` passed in Linux; shell syntax checks passed for all
`infra/scripts/*.sh`, executable bits set in WSL, Python lint/types passed again.

## Browser and Windows-local verification

- `BROWSER_CHANNEL=msedge node tests/e2e/m0-browser.mjs`: PASS with final
  PrimeVue 4.5.5/Aura 2.0.3. Headless Edge checked login, DB-backed DEMO overview,
  theme setting, empty scanner, pending lab and operations; no uncaught page
  errors and no invalid-license banner.
- Dark/light screenshots inspected locally under ignored `.runtime/`.
- `dev-start-windows.ps1 -SkipBuild`: PASS, frontend proxy readiness UP at
  `http://127.0.0.1:5173`.
- Windows launcher uses a hidden persistent WSL client: this machine closed
  background user processes when the last WSL client exited. Quoting the distro
  name in Start-Process also caused WSL_E_DISTRO_NOT_FOUND; passing the validated
  name without embedded quotes fixed it.
- `dev-stop-windows.ps1` stopped only project processes and preserved shared
  PostgreSQL/Redis. Final restart passed proxy readiness; application left running.

This verifies the current machine's local development flow, not clean Windows
installation, production Linux service supervision, or reboot acceptance.
