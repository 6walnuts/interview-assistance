# AI Interview Coach

一个面向 SDE / Backend / Infra / AI Infra 候选人的 **AI 面试教练平台**。不是一次性模拟面试工具，而是完整闭环：

```
学习 → 专项练习 → 模拟面试 → 自动评分 → 面试复盘 → 个性化学习计划 → 再次练习
```

候选商业化名称：**Offerloop · Hirely · MockMentor · Interview Forge · SignalPrep**（见 `docs/01-product-architecture.md`）。

## 文档

| 文档 | 内容 |
|---|---|
| `docs/01-product-architecture.md` | 产品定位、用户流程、MVP 范围、页面结构、优先级 |
| `docs/02-tech-architecture.md` | 前端 / 后端 / Agent / 沙箱 / 部署架构 |
| `docs/03-data-model.md` | 全部 16 张表的数据模型（DDL 见 `database/init.sql`） |
| `docs/04-api-design.md` | REST API 设计（Schema / 错误 / 权限） |
| `docs/05-agent-prompts.md` | 4 个核心 Agent System Prompt |
| `docs/06-development-plan.md` | 项目目录说明 + Phase 1-4 开发计划 |

## 仓库结构

```
apps/web        Next.js 14 前端（TypeScript + Tailwind + Monaco）
services/api    FastAPI 后端（SQLAlchemy + 7 个 Agent + Docker 沙箱）
database/       Postgres DDL + Alembic 迁移脚手架
infra/          docker-compose + 沙箱镜像
packages/       预留：共享 TS 类型包
docs/           设计文档
```

## 本地运行

### 0. 环境变量

```bash
cp .env.example services/api/.env
# 不填任何 API key 也能跑：MOCK_AI=true 时所有 Agent 走确定性 mock，
# 整个「面试 → 评分 → 学习任务」闭环离线可用。
```

**支持多家 AI 供应商**，通过 `LLM_PROVIDER` 切换：

| Provider | 配置 | 默认模型 |
|---|---|---|
| OpenAI | `LLM_PROVIDER=openai LLM_API_KEY=sk-...` | gpt-4o-mini |
| DeepSeek | `LLM_PROVIDER=deepseek LLM_API_KEY=sk-...` | deepseek-chat |
| Kimi (Moonshot) | `LLM_PROVIDER=kimi LLM_API_KEY=sk-...` | kimi-latest（海外账号加 `LLM_BASE_URL=https://api.moonshot.ai/v1`） |
| Claude (Anthropic) | `LLM_PROVIDER=anthropic LLM_API_KEY=sk-ant-...` | claude-opus-4-8（省钱可设 `LLM_MODEL=claude-haiku-4-5`） |

DeepSeek/Kimi 走 OpenAI 兼容接口；Claude 走官方 `anthropic` SDK。
任何 OpenAI 兼容的自建网关也可以用 `LLM_BASE_URL` 接入。设置后记得 `MOCK_AI=false`。

### 1. 后端（默认 SQLite，零依赖启动）

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # 建表 + 导入知识点/题库/Quiz
uvicorn app.main:app --reload --port 8000
```

**单机免密码模式**：个人本地使用可跳过注册登录，所有存档记在一个本地账号下：

```bash
LOCAL_MODE=true SANDBOX_MODE=subprocess uvicorn app.main:app --reload --port 8000
```

打开前端会自动跳过登录页直达 Dashboard（导航栏显示 "Local mode"）。
所有数据仍持久化在 `services/api/dev.db`（SQLite），删除该文件即重置存档。
注意：LOCAL_MODE 下任何能访问该端口的人都是同一账号，仅限本机使用。

API 文档：http://localhost:8000/docs

### 2. 前端

```bash
cd apps/web
npm install
npm run dev                 # http://localhost:3000
```

### 3. 代码沙箱（可选，Coding 面试的安全执行）

```bash
docker build -t ai-coach-sandbox:latest infra/sandbox
# services/api/.env 中设置 SANDBOX_MODE=docker（默认）
# 无 Docker 的本地开发可设 SANDBOX_MODE=subprocess（无隔离，仅限开发）
```

沙箱限制：禁网（`--network none`）、CPU/内存上限、`--pids-limit`（防 fork bomb）、只读根文件系统、nobody 用户、不传入任何环境变量、宿主侧超时 kill（防死循环）。

### 4. 全套 Docker（Postgres + Redis + API）

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

### 5. 测试

```bash
cd services/api && .venv/bin/python -m pytest tests -q
```

覆盖：认证、权限隔离、完整面试闭环（创建 → 对话 → 提示 → 跑代码 → 结束 → 报告 → 自动生成 ≥3 学习任务 → 幂等）、任务完成更新 Mastery、进度接口。

## 核心闭环（一条链路）

```
POST /api/interviews          Interview Planner 选题，Mock Interviewer 开场
POST .../messages             Interviewer 状态机推进（internal_observation 落库，前端不可见）
POST .../run-code             Docker 沙箱执行 + 测试用例判分
POST .../end                  Scoring Agent 独立评分 → interview_reports
                              Review Task Generator → review_tasks + learning_tasks(≥3)
GET  .../report               报告页；GET /api/tasks 出现学习计划
```

## 生产迁移

```bash
cd database/alembic
DATABASE_URL=postgresql://... alembic revision --autogenerate -m "init"
DATABASE_URL=postgresql://... alembic upgrade head
```

## 安全说明

- 密钥全部走环境变量，仓库零硬编码（`.env.example` 为模板）。
- JWT HS256 + PBKDF2 密码哈希；所有资源接口校验属主（403）。
- `interview_messages.internal_observation` 永不出现在任何 API 响应中。
- 所有 LLM 输出经 Pydantic Schema 强校验，失败自动重试一次后报错。
