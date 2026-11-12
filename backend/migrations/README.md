# migrations

当前版本用 SQLAlchemy `Base.metadata.create_all()` 在 backend 启动时建表（小型项目，无需迁移框架）。

- `0001_initial.sql`：与 `src/models/*.py` 一致的 MySQL 8.0 DDL 快照，供 review 与手工核查使用，**不参与启动**。
- 结构变更流程（约定）：改 `src/models/` → 同步改本目录新增 `000N_*.sql` → 在 PR 说明里写清影响面。
