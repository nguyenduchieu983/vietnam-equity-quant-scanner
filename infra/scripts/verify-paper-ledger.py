"""Verify an existing smoke replay against one uninterrupted engine run."""
import json
from pathlib import Path
import psycopg
from quant.db import connect
from quant.backtest import simulate
from quant.features import feature_book

state = json.loads(Path('.runtime/paper-smoke-state.json').read_text())
with connect() as c:
    payload = c.execute('SELECT payload_json FROM paper_market_snapshots WHERE id=%s', (state['snapshot'],)).fetchone()[0]
    book = feature_book(payload)
    accounts = c.execute('SELECT id,code,config_json,state_json,summary_json FROM paper_accounts WHERE pair_id=%s ORDER BY code', (state['REPLAY'],)).fetchall()
    summaries = []
    for account_id, code, config, checkpoint, summary in accounts:
        records = [r[0] for r in c.execute("SELECT payload_json - 'decision' FROM paper_sessions WHERE account_id=%s ORDER BY session_date", (account_id,)).fetchall()]
        full = simulate(payload, config, '2026-09-03', '2026-10-20', book, checkpoint=True)
        for key in ('orders', 'trades', 'cash_events'):
            observed = [x for r in records for x in r[key]]
            # JSONB canonicalizes position-key order; independent same-session exits can reorder.
            canonical = lambda rows: sorted(json.dumps(row, sort_keys=True) for row in rows)
            assert canonical(observed) == canonical(full[key]), (code, key)
        actual = [x for r in records for x in r['equity']]
        for a, b in zip(actual, full['equity'], strict=True):
            assert {k:v for k,v in a.items() if k != 'benchmark'} == {k:v for k,v in b.items() if k != 'benchmark'}, code
        for key in ('cash', 'pending', 'positions', 'peak'):
            assert checkpoint[key] == full['checkpoint'][key], (code, key)
        summaries.append({'code':code,'sessions':len(actual),'nav':actual[-1]['nav'],**{k:summary[k] for k in ('closed','wins','winRate','return','drawdown')}})
    for table, column in [('paper_sessions','result_hash'),('paper_approvals','expected_cursor'),('paper_market_snapshots','content_hash')]:
        for operation in [f'UPDATE {table} SET {column}={column}', f'DELETE FROM {table}']:
            c.execute('SAVEPOINT immutable_check')
            try:
                c.execute(operation)
            except psycopg.errors.RaiseException:
                c.execute('ROLLBACK TO SAVEPOINT immutable_check')
            else:
                c.execute('ROLLBACK TO SAVEPOINT immutable_check')
                raise AssertionError(f'{table} allowed mutation')
    c.rollback()
report = {'source':'VNDIRECT_PUBLIC_REAL','mode':'REPLAY_NOT_FORWARD','period':['2026-09-03','2026-10-20'],
          'checks':['restart persistence','approval idempotency','NAV identity','uninterrupted engine parity excluding benchmark base','immutable snapshots/approvals/sessions'], 'accounts':summaries}
Path('docs/verification/paper-2026-10-21.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report))
