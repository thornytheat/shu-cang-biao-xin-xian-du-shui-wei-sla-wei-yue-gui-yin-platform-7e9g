-- 0002：违约台账误违约作废（补采迟到对账）
-- 背景：补采（就绪事件采集）偶尔迟到，先按旧延迟判了违约；实际就绪时间补录后重算，
--       已不违约的记录需要作废标记（未处置的直接删除，已认领/复盘的保留处置痕迹并标作废）。
-- 运行时由 SQLAlchemy create_all 建表；本文件是与 src/models/sla_breach.py 同步的 DDL 快照。

ALTER TABLE sla_breaches
  ADD COLUMN voided_at   DATETIME     NULL COMMENT '作废时间（补采迟到重算后判定为误违约）' AFTER root_note,
  ADD COLUMN void_reason VARCHAR(255) NULL COMMENT '作废原因' AFTER voided_at;
