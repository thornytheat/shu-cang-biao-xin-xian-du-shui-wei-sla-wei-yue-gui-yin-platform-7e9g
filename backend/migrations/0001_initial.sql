-- freshsla 初始结构（MySQL 8.0）
-- 运行时由 SQLAlchemy 2.0 Base.metadata.create_all 建表；本文件是同一结构的 DDL 快照，
-- 用于 code review / 手工核查，不参与容器启动。字段与 src/models/*.py 一一对应。

CREATE TABLE IF NOT EXISTS users (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  email           VARCHAR(160) NOT NULL UNIQUE,
  password_hash   VARCHAR(255) NOT NULL,
  display_name    VARCHAR(80)  NOT NULL,
  role            VARCHAR(16)  NOT NULL COMMENT 'admin/ops/viewer',
  team            VARCHAR(64)  NOT NULL DEFAULT '数据平台运营组',
  last_login_at   DATETIME NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS table_assets (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  code                  VARCHAR(80) NOT NULL UNIQUE COMMENT '如 dwd.loan_repay',
  name                  VARCHAR(80) NOT NULL,
  layer                 VARCHAR(8)  NOT NULL COMMENT 'ods/dwd/dws/ads',
  tier                  VARCHAR(4)  NOT NULL COMMENT 'P0/P1/P2',
  schedule_cron         VARCHAR(48) NOT NULL,
  expected_ready_clock  VARCHAR(5)  NOT NULL COMMENT 'HH:MM',
  upstream_code         VARCHAR(80) NULL,
  report_count          INT NOT NULL DEFAULT 0,
  owner_team            VARCHAR(64) NOT NULL DEFAULT '数据平台运营组',
  size_gb               FLOAT NOT NULL DEFAULT 0,
  owner_note            TEXT NULL,
  is_active             TINYINT(1) NOT NULL DEFAULT 1,
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_assets_layer (layer),
  KEY idx_assets_tier (tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS freshness_probes (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  table_id            INT NOT NULL,
  probe_date          DATE NOT NULL,
  partition_dt        VARCHAR(16) NOT NULL,
  expected_ready_at   DATETIME NOT NULL,
  actual_ready_at     DATETIME NULL,
  delay_seconds       INT NULL COMMENT '负值截 0',
  raw_offset_seconds  INT NULL COMMENT '未截断原始偏移',
  is_early            TINYINT(1) NOT NULL DEFAULT 0,
  status              VARCHAR(12) NOT NULL COMMENT 'ok/late/early/missing',
  source              VARCHAR(12) NOT NULL DEFAULT 'probe' COMMENT 'seed/probe/fixture',
  note                VARCHAR(255) NULL,
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_probe_table_date (table_id, probe_date),
  KEY idx_probe_date (probe_date),
  CONSTRAINT fk_probe_table FOREIGN KEY (table_id) REFERENCES table_assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sla_policies (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  tier                VARCHAR(4) NOT NULL UNIQUE,
  tolerance_minutes   INT NOT NULL,
  escalate_after      INT NOT NULL DEFAULT 3,
  calibrate_days      INT NOT NULL DEFAULT 30,
  report_owner_note   TEXT NULL,
  updated_by          VARCHAR(160) NULL,
  updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sla_breaches (
  id                     INT AUTO_INCREMENT PRIMARY KEY,
  table_id               INT NOT NULL,
  probe_id               INT NULL,
  breach_date            DATE NOT NULL,
  delay_seconds          INT NOT NULL DEFAULT 0,
  tolerance_minutes      INT NOT NULL DEFAULT 60,
  ratio                  FLOAT NOT NULL DEFAULT 0,
  severity               VARCHAR(12) NOT NULL COMMENT 'warning/severe/escalated',
  consecutive_count      INT NOT NULL DEFAULT 1,
  primary_cause          VARCHAR(80) NOT NULL DEFAULT 'undetermined',
  cause_contribution_pct FLOAT NOT NULL DEFAULT 0,
  impacted_reports       INT NOT NULL DEFAULT 0,
  impact_score           FLOAT NOT NULL DEFAULT 0,
  suggested_action       VARCHAR(255) NOT NULL DEFAULT '',
  attribution_detail     JSON NULL,
  handling_status        VARCHAR(12) NOT NULL DEFAULT 'open',
  claimed_by             VARCHAR(160) NULL,
  claimed_at             DATETIME NULL,
  resolved_at            DATETIME NULL,
  root_note              TEXT NULL,
  created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_breach_table_date (table_id, breach_date),
  KEY idx_breach_status (handling_status),
  KEY idx_breach_severity (severity),
  CONSTRAINT fk_breach_table FOREIGN KEY (table_id) REFERENCES table_assets(id) ON DELETE CASCADE,
  CONSTRAINT fk_breach_probe FOREIGN KEY (probe_id) REFERENCES freshness_probes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS probe_runs (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  run_date        DATE NOT NULL UNIQUE,
  triggered_by    VARCHAR(160) NOT NULL,
  trigger_source  VARCHAR(16) NOT NULL DEFAULT 'api',
  created_count   INT NOT NULL DEFAULT 0,
  missing_count   INT NOT NULL DEFAULT 0,
  unknown_count   INT NOT NULL DEFAULT 0,
  late_count      INT NOT NULL DEFAULT 0,
  red_tables      JSON NULL,
  duration_ms     INT NOT NULL DEFAULT 0,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  actor_email   VARCHAR(160) NOT NULL,
  actor_role    VARCHAR(16) NOT NULL,
  action        VARCHAR(64) NOT NULL,
  entity        VARCHAR(48) NOT NULL,
  entity_id     VARCHAR(80) NULL,
  layer         VARCHAR(16) NOT NULL DEFAULT 'domain',
  detail        JSON NULL,
  ip            VARCHAR(64) NULL,
  message       TEXT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_audit_actor (actor_email),
  KEY idx_audit_action (action),
  KEY idx_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
