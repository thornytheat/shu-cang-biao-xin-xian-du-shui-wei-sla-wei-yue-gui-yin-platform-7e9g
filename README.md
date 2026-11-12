# freshsla · 数仓表新鲜度水位与 SLA 违约归因台

> 一块值班挂板讲清三件事：**谁延迟、延迟多久、影响哪些下游报表**。

澜河银行 · 数据平台运营组维护 380 张表，其中 40 张核心表。过去值班工程师每天 07:00-08:30 逐张
`select max(dt)` 确认就绪，晚了在群里追问上游；月末出报表才发现某张表晚到 3 小时，违约没有台账，
复盘全靠回忆。freshsla 用「探测 → 分位判级 → 违约检测 → 上游归因 → 认领复盘 → 导出」把这段工作流接管。

- 上游输入：调度系统就绪事件 + 每日探测任务（本项目用确定性 fixture 模拟）
- 本系统替代：人工 SQL 巡检 + 群里追问 + Excel 记账
- 下游消费：值班日报、月度 SLA 复盘会、报表 owner 通知

## 主要功能

| 模块 | 页面 | 说明 |
| --- | --- | --- |
| 新鲜度看板 | `/board` | 40 张表按 P0/P1/P2 分栏，三色灯 + 条带水位条；一键运行今日探测 |
| 表详情 | `/tables/:code` | 近 30 天延迟曲线（SVG 手绘）、P50/P90/P95、上游链逐跳延迟、该表违约记录；按分区补录实际就绪时间（补采迟到对账） |
| SLA 策略 | `/policies` | 三档容忍分钟 / 连续升级阈值 / 通知口径；近 30 天真实回放试算 |
| 违约台账 | `/breaches` | 筛选、上游归因（主因表 + 贡献%）、认领、复盘、导出复盘 CSV / Markdown；误违约作废留痕 |
| 登录 | `/login` | 三角色，低权角色调高权接口返回真实 403 |

### 两个后端真算算法（前端只展示，不硬编码）

**算法 1 · 延迟分位与三色灯判级**（`backend/src/services/freshness_service.py`）

```
delay = 实际就绪 − 期望就绪（秒）；负值截 0 并标 early
基线   = 最近一次探测之前、连续 30 天内的非缺失探测
分位   = 基线延迟的线性插值分位（等价 Excel PERCENTILE.INC）
判级   = green  delay ≤ P50
         yellow P50 < delay ≤ P90
         red    delay > P90
         探测缺失 / 无基线 → unknown（不参与分位与判级）
```

**算法 2 · 违约检测与上游归因**（`backend/src/services/breach_service.py`）

```
ratio = 延迟 / (容忍分钟 × 60)
ratio > 1.0 → 违约(warning)；ratio > 2.0 → 严重(severe)
连续违约：同一张表按自然日连续命中，第 n 天 consecutive = n
          consecutive > escalate_after（默认 3）时升级一级：warning → severe → escalated
归因：沿上游链逐跳取当日延迟，contribution = 上游延迟 / 本表延迟（上限 100%），取最大者为 primary_cause
      无上游登记 → self；全链路无就绪事件 → undetermined
影响分 = 0.45×贡献% + 0.35×min(100, 影响报表数×10) + 0.20×min(100, ratio/2×100)
        示例：贡献 62.0% / 7 张报表 / ratio 1.6 → 68.4
```

**补采迟到对账**（`POST /api/tables/{code}/backfill` + 重跑检测）

```
补采（就绪事件采集）偶尔迟到：先按旧延迟判了违约，实际就绪事件随后才到。
补录 = 按分区写回实际就绪时间（source=backfill，延迟同口径归一，巡检不覆盖），
随后自动重跑检测，该日及后续连续天数全量重算：
  仍是候选   → 正常 upsert；已作废的复活（revive）
  不再是候选 → 误违约：未处置(open) 删除（从待办消失）；
              已认领/已复盘 标作废（voided_at + void_reason，保留处置痕迹）
幂等：重复运行不新增记录、不重复作废、不重复升级（连续次数由扫描全量重算）。
口径：看板 / 详情 / 汇总 / 导出只计有效违约；作废记录仅台账「含已作废」可见。
```

## 快速启动

```bash
cp .env.example .env

docker compose config --quiet        # 语法自检
docker compose up -d --build         # 5 个服务：frontend/backend/worker/db/redis

docker compose exec backend python -m scripts.seed_demo   # 手动跑一次 seed（SEED_DEMO=true 时启动已自动跑）
docker compose ps                    # 5/5 healthy
```

访问：

| 入口 | 地址 |
| --- | --- |
| 前端 | http://localhost:18254 |
| 后端 OpenAPI | http://localhost:19254/docs |
| 健康检查 | http://localhost:19254/api/health |
| MySQL | 127.0.0.1:17754（库 `freshsla`） |

seed 结束会打印一行契约（多次执行逐字一致）：

```
SEED_SUMMARY brand=freshsla tables=40 probes=1200 policies=3 breaches=9 users=3
```

## 演示账号

| 邮箱 | 密码 | 角色 | 主要页面 | 权限 |
| --- | --- | --- | --- | --- |
| `admin@freshsla.io` | `Demo@2026` | admin 平台负责人 | 全部 | 表/策略/等级/导出全权，可改容忍值与升级阈值 |
| `ops@freshsla.io` | `Demo@2026` | ops 值班工程师 | 看板/详情/台账 | 跑探测、认领违约、写归因、导出；**不能改策略与表** |
| `viewer@freshsla.io` | `Demo@2026` | viewer 报表 owner | 看板/详情/策略/台账（只读） | 只读；跑探测、改策略、导出均返回 **403** |

权限是后端 RBAC 拦的（`require_roles`），不是前端隐藏按钮；前端仍保留按钮，方便直接验证 403。

## 技术栈

| 层 | 选型 |
| --- | --- |
| 前端 | React 18 + TypeScript + Vite 5 + React Router 6；手写 store（useSyncExternalStore）+ SVG 自绘图表 |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2 + PyJWT |
| 异步 | Celery 5.4（worker，beat 心跳 + 每日 08:10 自动巡检） |
| 数据 | MySQL 8.0（utf8mb4，`+08:00` 会话时区）、Redis 7（限流计数 + 心跳） |
| 网关 | Nginx 1.27（`/api/` 反代 backend + SPA 回落） |
| 容器 | Docker Compose，5 服务全 healthcheck |

## 目录

```
gb-581/
├── docker-compose.yml          # 5 服务、命名卷、service_healthy 依赖
├── .env / .env.example
├── backend/
│   ├── Dockerfile  requirements.txt
│   ├── migrations/0001_initial.sql   # 与 models 一致的 DDL 快照
│   ├── scripts/
│   │   ├── demo_config.py      # 40 张表 / 策略 / 账号 / 违约覆写（数据规格）
│   │   ├── seed_demo.py        # 幂等 seed，打印 SEED_SUMMARY
│   │   └── worker_healthcheck.sh
│   └── src/
│       ├── config/   app.py settings.py database.py celery_app.py
│       ├── constants/ enums.py roles.py limits.py error_codes.py
│       ├── models/    table_asset.py freshness_probe.py sla_policy.py sla_breach.py
│       │              user.py audit.py probe_run.py
│       ├── schemas/   auth.py table.py freshness.py policy.py breach.py common.py
│       ├── services/  freshness_service.py breach_service.py probe_service.py
│       │              policy_service.py export_service.py table_service.py
│       │              auth_service.py audit_service.py fixture_source.py
│       ├── controllers/ table/probe/policy/breach/auth/export_controller.py
│       ├── routes/    auth tables probes policies breaches exports health
│       ├── middlewares/ auth.py rbac.py audit_logger.py rate_limit.py error_handler.py
│       └── utils/     percentile.py timeutil.py security.py logger.py errors.py
├── frontend/
│   ├── Dockerfile  nginx.conf  index.html  package.json
│   └── src/
│       ├── api/       client.ts auth tables probes policies breaches
│       ├── stores/    authStore.ts uiStore.ts
│       ├── types/     models.ts
│       ├── constants/ enums.ts roles.ts ui.ts
│       ├── hooks/     useAsync.ts useAuth.ts useToast.ts useClock.ts
│       ├── components/common/ TierLamp WaterBar DelayCurve SeverityTag EmptyState Toasts
│       ├── components/layout/ AppShell.tsx
│       ├── pages/     Login Board TableDetail Policies Breaches
│       ├── router/    index.tsx guards.tsx
│       ├── utils/     format.ts errorMessage.ts storage.ts
│       └── styles/    tokens.css global.css
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `COMPOSE_PROJECT_NAME` | `freshsla` | 容器名前缀 |
| `FRONTEND_PORT` | `18254` | 前端映射端口 |
| `BACKEND_PORT` | `19254` | 后端映射端口 |
| `DB_PORT` | `17754` | MySQL 映射端口 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `freshsla` / `freshsla` / `freshsla_pw_2026` | 业务库 |
| `DB_ROOT_PASSWORD` | `freshsla_root_2026` | root 密码 |
| `JWT_SECRET` | `freshsla-jwt-secret-change-me-2026` | HS256 签名密钥 |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker/backend + 限流 |
| `SEED_DEMO` | `true` | 启动自动 seed（失败只记日志） |
| `RATE_LIMIT_PER_MINUTE` | `600` | 读接口每分钟额度 |
| `RATE_LIMIT_WRITE_PER_MINUTE` | `120` | 写接口（探测/检测/策略/导出）额度 |
| `APP_TIMEZONE_OFFSET_MINUTES` | `480` | 业务时区 UTC+8 |
| `CALIBRATION_DAYS` | `30` | 新鲜度分位基线窗口 |
| `NPM_REGISTRY` | `https://registry.npmmirror.com` | 前端构建 npm 源（Dockerfile ARG） |

## Docker 说明

- 恰好 5 个服务，全部带 `healthcheck`：db `mysqladmin ping`、redis `redis-cli ping`、
  backend `/api/health`、worker 心跳文件 / Celery ping、frontend `wget`。
- `backend` / `worker` 依赖 `db`、`redis` 的 `service_healthy`，`worker` 与 `frontend` 还依赖 `backend` healthy。
- 命名卷：`db_data`（MySQL 数据）、`redis_data`（AOF）。
- 端口：`${FRONTEND_PORT:-18254}:80`、`${BACKEND_PORT:-19254}:8000`、`${DB_PORT:-17754}:3306`。
- 构建：后端 pip 用清华源；前端 npm 用 `registry.npmmirror.com`（可用 `NPM_REGISTRY` 覆盖）。
- 只使用本机已有镜像 tag：`python:3.11-slim` / `node:20-alpine` / `nginx:1.27-alpine` / `mysql:8.0` / `redis:7-alpine`。

## 本地开发

```bash
# 后端（需要本地 MySQL 8 + Redis）
cd backend && python3.11 -m venv .venv && . .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
uvicorn src.main:app --reload --port 8000

# 前端
cd frontend && npm install --registry=https://registry.npmmirror.com
npm run dev          # http://localhost:5173，/api 代理到 19254
```

## 共享枚举出现位置（前后端各一份）

**前端唯一来源**：`frontend/src/constants/enums.ts`；**后端唯一来源**：`backend/src/constants/enums.py`。

| 枚举 | 后端出现位置 | 前端出现位置 |
| --- | --- | --- |
| `Role`（admin/ops/viewer） | `constants/enums.py`、`constants/roles.py`、`middlewares/rbac.py`、`models/user.py`、`services/auth_service.py` | `types/models.ts`、`constants/enums.ts`（`ROLE_LABELS`）、`constants/roles.ts`、`pages/Login.tsx`、`components/layout/AppShell.tsx` |
| `Tier`（P0/P1/P2） | `constants/enums.py`、`models/table_asset.py`、`models/sla_policy.py`、`services/breach_service.py`、`services/policy_service.py` | `types/models.ts`、`constants/enums.ts`（`TIER_LABELS`/`TIER_ORDER`）、`pages/Board.tsx`、`pages/Policies.tsx`、`components/common/SeverityTag.tsx` |
| `Grade`（green/yellow/red/unknown） | `constants/enums.py`、`services/freshness_service.py`、`schemas/freshness.py` | `constants/enums.ts`（`GRADE_LABELS`/`GRADE_HINTS`/`waterWidth`）、`components/common/TierLamp.tsx`、`components/common/WaterBar.tsx` |
| `ProbeStatus`（ok/late/early/missing） | `constants/enums.py`、`models/freshness_probe.py`、`services/fixture_source.py`、`services/freshness_service.py` | `constants/enums.ts`（`PROBE_STATUS_LABELS`）、`pages/TableDetail.tsx` |
| `BreachSeverity`（warning/severe/escalated） | `constants/enums.py`、`services/breach_service.py`、`services/export_service.py` | `constants/enums.ts`（`SEVERITY_LABELS`）、`components/common/SeverityTag.tsx`、`pages/Breaches.tsx` |
| `HandlingStatus`（open/claimed/resolved） | `constants/enums.py`、`models/sla_breach.py`、`services/breach_service.py` | `constants/enums.ts`（`HANDLING_LABELS`）、`pages/Breaches.tsx` |
| `Layer`（ods/dwd/dws/ads） | `constants/enums.py`、`models/table_asset.py`、`services/table_service.py` | `constants/enums.ts`（`LAYER_LABELS`）、`pages/Board.tsx`、`pages/TableDetail.tsx` |

## 接口一览（统一 `/api` 前缀）

```
POST /api/auth/login                  GET  /api/auth/me
GET  /api/tables                      GET  /api/tables/{code}
GET  /api/tables/{code}/freshness     PATCH /api/tables/{code}          (admin)
POST /api/tables/{code}/backfill      (admin/ops，补录就绪时间并重算违约)
GET  /api/dashboard/health
POST /api/probes/run                  (admin/ops)  GET /api/probes/status  GET /api/probes
GET  /api/policies                    PATCH /api/policies/{tier} (admin)
POST /api/policies/preview            (admin/ops)
GET  /api/breaches                    GET  /api/breaches/summary
POST /api/breaches/detect             (admin/ops)
POST /api/breaches/{id}/claim         (admin/ops)
POST /api/breaches/{id}/resolve       (admin/ops)
POST /api/breaches/{id}/attribution   (admin)
GET  /api/exports/breaches.csv        (admin/ops)
GET  /api/exports/review.md           (admin/ops)
GET  /api/audit                       (admin)
GET  /api/health
```

## License

MIT
