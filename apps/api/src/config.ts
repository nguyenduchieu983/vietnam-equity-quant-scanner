export function required(name: string): string {
  const value = process.env[name];
  if (!value || value.includes('REPLACE_') || value.includes('CHANGE_ME')) throw new Error(`Configure ${name}`);
  return value;
}
export function mode(): 'demo' | 'real' {
  if (!['demo', 'real'].includes(process.env.DATA_MODE ?? '')) throw new Error('DATA_MODE must be demo or real');
  return process.env.DATA_MODE as 'demo' | 'real';
}
export function safeSort(field: string): string {
  const fields: Record<string, string> = { symbol: 'i.symbol', score: 'r.composite_score', exchange: 'i.exchange' };
  return fields[field] ?? 'i.symbol';
}
