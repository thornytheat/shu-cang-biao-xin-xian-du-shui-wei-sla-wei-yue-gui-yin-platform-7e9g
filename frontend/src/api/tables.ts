import { api } from './client';
import type { BackfillResult, Board, TableSeries } from '../types/models';

export interface TableSummary {
  code: string;
  name: string;
  layer: string;
  tier: string;
  schedule_cron: string;
  expected_ready_clock: string;
  upstream_code: string | null;
  report_count: number;
  owner_team: string;
  size_gb: number;
  owner_note: string | null;
  tolerance_minutes: number;
}

export const tablesApi = {
  board: (params: { layer?: string; q?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.layer) search.set('layer', params.layer);
    if (params.q) search.set('q', params.q);
    const qs = search.toString();
    return api.get<Board>(`/api/dashboard/health${qs ? `?${qs}` : ''}`);
  },
  list: (params: { layer?: string; tier?: string; q?: string } = {}) => {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) search.set(key, value);
    });
    const qs = search.toString();
    return api.get<{ items: TableSummary[]; total: number }>(`/api/tables${qs ? `?${qs}` : ''}`);
  },
  series: (code: string, days = 30) =>
    api.get<TableSeries>(`/api/tables/${encodeURIComponent(code)}/freshness?days=${days}`),
  update: (code: string, payload: Record<string, unknown>) =>
    api.patch<TableSeries>(`/api/tables/${encodeURIComponent(code)}`, payload),
  backfill: (code: string, payload: { probe_date: string; actual_ready_at: string; note?: string }) =>
    api.post<BackfillResult>(`/api/tables/${encodeURIComponent(code)}/backfill`, payload),
};
