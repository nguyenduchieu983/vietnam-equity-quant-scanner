import test from 'node:test';
import assert from 'node:assert/strict';
import { safeSort, mode } from '../src/config';
test('sort fields are allowlisted', () => {
  assert.equal(safeSort('score'), 'r.composite_score');
  assert.equal(safeSort('score; DROP TABLE rankings'), 'i.symbol');
});
test('unknown data mode fails closed', () => {
  process.env.DATA_MODE = 'anything';
  assert.throws(mode);
  process.env.DATA_MODE = 'demo';
  assert.equal(mode(), 'demo');
});
