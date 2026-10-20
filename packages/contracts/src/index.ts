export type ScanStatus = 'COMPLETE' | 'PARTIAL' | 'STALE' | 'FAILED';
export interface Envelope<T> {
  data: T;
  meta: { asOf: string | null; source: string; runId: string | null; freshness: string; isDemo: boolean };
  error: { code: string; message: string; requestId: string } | null;
}
export interface ScanRun {
  id: string; session_date: string; status: ScanStatus; freshness_json: Record<string, unknown>;
}
export interface ScanResult {
  symbol: string; exchange: string; composite_score: string | null;
  excluded: boolean; exclusion_codes_json: string[];
}
export interface SystemStatus {
  database: boolean; redis: boolean; worker: boolean; isDemo: boolean;
  bars: number; instruments: number; lastIngest: string | null; latestSession: string | null;
  milestone: string;
}
