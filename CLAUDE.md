# AI Interview Coach — 项目指南

AI 面试教练平台：学习 → 练习 → 模拟面试 → 自动评分 → 复盘 → 个性化学习计划的完整闭环。
产品与技术设计见 `docs/`（01 产品架构 → 06 开发计划，按序号读）。

## 仓库结构

- `apps/web` — Next.js 14 前端（App Router + TypeScript + Tailwind + Monaco）
- `services/api` — FastAPI 后端（SQLAlchemy 2 + Pydantic v2）
  - `app/agents/` — 7 个职责单一的 Agent（interviewer / scorer / review_tasks /
    planner / learning_planner / quiz_gen / coach），全部经 `agents/llm.py` 调用 LLM，
    输出用 Pydantic schema 强校验；prompt 权威版本在 `agents/prompts.py`
  - `app/services/sandbox.py` — 多语言代码沙箱（python/javascript/go/java/cpp）
  - `app/routers/` → `app/services/` → `app/models.py`（16 张表）分层
- `infra/sandbox/` — 各语言沙箱镜像，`build.sh` 一键构建
- `database/` — Postgres DDL（init.sql）+ Alembic 脚手架

## 本地启动

```bash
# 后端（默认 SQLite；LOCAL_MODE=true 免登录单机模式；MOCK_AI=true 无需任何 API key）
# 需要 Python ≥3.10。macOS 系统自带 /usr/bin/python3 是 3.9 不能用；
# 建 venv 显式指定版本（brew install python@3.12），命令走 .venv/bin/ 全路径最稳。
cd services/api && python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt && .venv/bin/python -m app.seed
LOCAL_MODE=true SANDBOX_MODE=subprocess .venv/bin/uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd apps/web && npm install && npm run dev   # http://localhost:3000
```

真实 AI：`LLM_PROVIDER=openai|deepseek|kimi|anthropic LLM_API_KEY=... MOCK_AI=false`。
安全代码沙箱：装 Docker 后跑 `infra/sandbox/build.sh`，去掉 `SANDBOX_MODE=subprocess`。

## 测试与验证

```bash
cd services/api && .venv/bin/python -m pytest tests -q   # 全部测试须通过
cd apps/web && npx tsc --noEmit && npm run build          # 前端类型检查 + 构建
```

测试跑在 mock AI + SQLite + subprocess 沙箱下，无外部依赖。改动 Agent 输出
schema 时同步更新 `agents/agent_schemas.py` 的 Pydantic 模型和相关 mock。

## 关键约定

- **所有 LLM 输出必须过 Pydantic 校验**；每个 Agent 必须提供确定性 mock
  （`MOCK_AI=true` 时全链路可离线运行——测试依赖这一点）
- `interview_messages.internal_observation` 永不出现在任何 API 响应中
- 评分只由 Scoring Agent 做，绝不让 Interviewer 自评
- 密钥只走环境变量（`.env.example` 为模板），仓库零硬编码
- 前端 `lib/types.ts` 与后端 `app/schemas.py` 手工保持同步
- 面试状态机 12 阶段定义在 `agents/interviewer.py` 的 `STAGES`
