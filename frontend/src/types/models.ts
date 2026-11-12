export type Role = 'admin' | 'ops' | 'viewer';
export type Tier = 'P0' | 'P1' | 'P2';
export type Layer = 'ods' | 'dwd' | 'dws' | 'ads';
export type Grade = 'green' | 'yellow' | 'red' | 'unknown';
export type ProbeStatus = 'ok' | 'late' | 'early' | 'missing';
export type BreachSeverity = 'warning' | 'severe' | 'escalated';
export type HandlingStatus = 'open' | 'claimed' | 'resolved';

export interface User {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  role_label: string;
  team: string;
  permissions: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Percentiles {
  p50: number | null;
  p90: number | null;
  p95: number | null;
}

export interface LatestProbe {
  probe_date: string;
  partition_dt: string;
  expected_ready_at: string;
  actual_ready_at: string | null;
  delay_seconds: number | null;
  delay_minutes: number | null;
  ratio: number | null;
  status: ProbeStatus;
  is_early: boolean;
  is_missing: boolean;
}

export interface Evaluation {
  latest: LatestProbe | null;
  grade: Grade;
  grade_reason: string;
  percentiles: Percentiles;
  baseline_days: number;
  missing_in_window: number;
  tolerance_minutes: number;
  water_pct: number;
  on_time_rate: number | null;
}

export interface BoardRow {
  code: string;
  name: string;
  layer: Layer;
  tier: Tier;
  schedule_cron: string;
  expected_ready_clock: string;
  upstream_code: string | null;
  report_count: number;
  owner_team: string;
  size_gb: number;
  owner_note: string | null;
  tolerance_minutes: number;
  grade: Grade;
  grade_reason: string;
  delay_minutes: number | null;
  delay_seconds: number | null;
  ratio: number | null;
  probe_date: string | null;
  status: ProbeStatus | null;
  is_early: boolean;
  water_pct: number;
  percentiles: Percentiles;
  baseline_days: number;
  missing_in_window: number;
  on_time_rate: number | null;
}

export interface BoardTier {
  tier: Tier;
  tolerance_minutes: number;
  total: number;
  counters: Record<Grade, number>;
  red_tables: string[];
  rows: BoardRow[];
}

export interface Board {
  tiers: Record<Tier, BoardTier>;
  totals: { tables: number; red: number; yellow: number; green: number; unknown: number };
  waterline: string | null;
  calibration_days: number;
}

export interface ProbePoint {
  probe_date: string;
  partition_dt: string;
  delay_minutes: number | null;
  status: ProbeStatus;
  is_early: boolean;
  is_missing: boolean;
  is_breach: boolean;
  expected_ready_at: string;
  actual_ready_at: string | null;
}

export interface ChainNode {
  code: string;
  name: string;
  layer: Layer;
  tier: Tier;
  report_count: number;
  delay_minutes: number | null;
  status: string;
  contribution_pct?: number | null;
  basis?: string | null;
}

export interface TableSeries {
  table: {
    code: string;
    name: string;
    layer: Layer;
    tier: Tier;
    schedule_cron: string;
    expected_ready_clock: string;
    upstream_code: string | null;
    report_count: number;
    owner_team: string;
    size_gb: number;
    owner_note: string | null;
  };
  evaluation: Evaluation;
  points: ProbePoint[];
  stats: {
    avg_minutes: number | null;
    max_minutes: number | null;
    median_minutes: number | null;
    samples: number;
    missing: number;
    breach_days: number;
  };
  chain: {
    nodes: ChainNode[];
    downstream: { code: string; name: string; tier: Tier }[];
    tolerance_minutes: number;
    probe_date: string | null;
  };
}

export interface Policy {
  id: number;
  tier: Tier;
  label: string;
  tolerance_minutes: number;
  escalate_after: number;
  calibrate_days: number;
  report_owner_note: string | null;
  updated_by: string | null;
  updated_at: string | null;
}

export interface PolicyPreview {
  params: { tolerances: Record<Tier, number>; escalate_after: number | null };
  tiers: {
    tier: Tier;
    label: string;
    tolerance_minutes: number;
    breaches: number;
    severe: number;
    tables: string[];
  }[];
  totals: { breaches: number; severe: number; warning: number; affected_tables: number };
  sample: {
    table_code: string;
    breach_date: string;
    tier: Tier;
    delay_minutes: number;
    tolerance_minutes: number;
    ratio: number;
    consecutive: number;
    severity: BreachSeverity;
  }[];
  baseline: { probe_rows: number; window_days: number; critical_ratio: number };
}

export interface Breach {
  id: number;
  table_code: string;
  table_name: string;
  tier: Tier;
  layer: Layer;
  breach_date: string;
  delay_seconds: number;
  delay_minutes: number;
  tolerance_minutes: number;
  ratio: number;
  severity: BreachSeverity;
  severity_label: string;
  consecutive_count: number;
  primary_cause: string;
  cause_contribution_pct: number;
  impacted_reports: number;
  impact_score: number;
  suggested_action: string;
  attribution_detail: {
    chain?: {
      code: string;
      name: string;
      layer: Layer;
      tier: Tier;
      report_count: number;
      delay_minutes: number | null;
      contribution_pct: number;
      basis: string;
    }[];
    basis?: string;
    impact?: {
      contribution_pct: number;
      reports: number;
      ratio: number;
      score: number;
      weights: Record<string, number>;
    };
  } | null;
  handling_status: HandlingStatus;
  claimed_by: string | null;
  claimed_at: string | null;
  resolved_at: string | null;
  root_note: string | null;
  report_count: number;
  expected_ready_clock: string;
}

export interface BreachList {
  items: Breach[];
  summary: {
    total: number;
    by_severity: Record<BreachSeverity, number>;
    by_status: Record<HandlingStatus, number>;
    severe_total: number;
    top_impact: string | null;
  };
  filters: Record<string, string | null>;
}

export interface ProbeRunResult {
  run_date: string;
  created: number;
  updated: number;
  total: number;
  missing: number;
  unknown: number;
  late: number;
  early: number;
  ok: number;
  red_tables: string[];
  red_count: number;
  duration_ms: number;
  waterline: string;
  breaches: {
    scanned: number;
    created: number;
    updated: number;
    total: number;
    budget: { warning: number; severe: number; escalated: number };
    window_days: number;
    summary: Record<string, unknown>;
  } | null;
}

export interface ProbeStatusPayload {
  today: string;
  probed_today: boolean;
  run: {
    run_date: string;
    triggered_by: string;
    created_count: number;
    missing_count: number;
    late_count: number;
    red_tables: string[];
    duration_ms: number;
    created_at: string | null;
  } | null;
  latest: Record<string, unknown> | null;
}

export interface AuditEntry {
  id: number;
  actor_email: string;
  actor_role: string;
  action: string;
  entity: string;
  entity_id: string | null;
  layer: string;
  message: string | null;
  created_at: string | null;
}
