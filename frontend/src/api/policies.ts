import { api } from './client';
import type { Policy, PolicyPreview, Tier } from '../types/models';

export const policiesApi = {
  list: () =>
    api.get<{ items: Policy[]; can_edit: boolean; can_preview: boolean }>('/api/policies'),
  update: (tier: Tier, payload: Partial<Pick<Policy, 'tolerance_minutes' | 'escalate_after' | 'calibrate_days' | 'report_owner_note'>>) =>
    api.patch<Policy>(`/api/policies/${tier}`, payload),
  preview: (payload: {
    p0_tolerance: number;
    p1_tolerance: number;
    p2_tolerance: number;
    escalate_after: number | null;
  }) => api.post<PolicyPreview>('/api/policies/preview', payload),
};
