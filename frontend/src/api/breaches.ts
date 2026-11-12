import { api, requestBlob, saveBlob } from './client';
import type { AuditEntry, Breach, BreachList, BreachSeverity, HandlingStatus, Tier } from '../types/models';

export interface BreachFilters {
  severity?: BreachSeverity | '';
  status?: HandlingStatus | '';
  tier?: Tier | '';
  q?: string;
  includeVoided?: boolean;
}

function toQuery(filters: BreachFilters, limit?: number): string {
  const search = new URLSearchParams();
  if (filters.severity) search.set('severity', filters.severity);
  if (filters.status) search.set('status', filters.status);
  if (filters.tier) search.set('tier', filters.tier);
  if (filters.q) search.set('q', filters.q);
  if (filters.includeVoided) search.set('include_voided', 'true');
  if (limit) search.set('limit', String(limit));
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export const breachesApi = {
  list: (filters: BreachFilters = {}) => api.get<BreachList>(`/api/breaches${toQuery(filters, 200)}`),
  detail: (id: number) => api.get<Breach>(`/api/breaches/${id}`),
  summary: () =>
    api.get<{
      total: number;
      by_severity: Record<string, number>;
      by_status: Record<string, number>;
      severe_total: number;
      voided: number;
      top_impact: string | null;
    }>('/api/breaches/summary'),
  detect: (days = 30, includePlanned = false) =>
    api.post<{
      scanned: number;
      created: number;
      updated: number;
      voided: number;
      deleted: number;
      revived: number;
      total: number;
    }>('/api/breaches/detect', {
      days,
      include_planned: includePlanned,
    }),
  claim: (id: number, note?: string) =>
    api.post<Breach>(`/api/breaches/${id}/claim`, note ? { note } : undefined),
  resolve: (id: number, note: string) => api.post<Breach>(`/api/breaches/${id}/resolve`, { note }),
  recompute: (id: number) => api.post<Breach>(`/api/breaches/${id}/attribution`),
  exportCsv: async (filters: BreachFilters = {}) => {
    const { blob, filename } = await requestBlob(`/api/exports/breaches.csv${toQuery(filters)}`);
    saveBlob(blob, filename);
    return filename;
  },
  exportMarkdown: async () => {
    const { blob, filename } = await requestBlob('/api/exports/review.md');
    saveBlob(blob, filename);
    return filename;
  },
  audit: (limit = 20) => api.get<{ items: AuditEntry[]; total: number }>(`/api/audit?limit=${limit}`),
};
