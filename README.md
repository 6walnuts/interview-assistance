# AI Interview Coach

**中文** | [English](README.en.md) | [Español](README.es.md)

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

> ⚠️ **需要 Python ≥ 3.10（推荐 3.12）。先检查版本再往下走：**
>
> ```bash
> python3 --version
> ```
>
> **macOS 用户特别注意**：系统自带的 `python3` 是 Xcode 命令行工具里的 **3.9**
> （路径在 `/usr/bin/python3`），跑本项目会报
> `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`。
> 如果版本低于 3.10，先装新版并**在建 venv 时显式指定版本号**：
>
> ```bash
> brew install python@3.12
> ```

```bash
cd services/api
python3.12 -m venv .venv          # 显式指定版本，别用裸的 python3
source .venv/bin/activate
# Windows: py -3.12 -m venv .venv 然后 .venv\Scripts\activate
.venv/bin/python --version        # 检查点：必须显示 3.12.x 才继续！
pip install -r requirements.txt
python -m app.seed                # 建表 + 导入知识点/题库/Quiz
uvicorn app.main:app --reload --port 8000
```

**防坑技巧**：`source` 激活只对当前终端窗口有效，换了窗口就失效。拿不准时
直接用 venv 内的全路径命令，永远不会认错解释器：

```bash
.venv/bin/python -m app.seed
LOCAL_MODE=true SANDBOX_MODE=subprocess .venv/bin/uvicorn app.main:app --reload --port 8000
```

#### 常见报错对照表

| 报错 | 原因 | 解决 |
|---|---|---|
| `TypeError: unsupported operand type(s) for \|: 'type' and 'NoneType'` | 命令跑在了 Python ≤3.9 上（venv 没激活，或 venv 本身是 3.9 建的） | 看下一行 |
| 同上，但 `.venv/bin/python -m app.seed` 也报 | venv 是用 3.9 创建的（或新旧版本混杂） | `rm -rf .venv` 后用 `python3.12 -m venv .venv` 重建、重装依赖 |
| `psycopg2.OperationalError: connection ... port 5432 failed` | `.env` 里 `DATABASE_URL` 指向了没在跑的 Postgres | 改成 `DATABASE_URL=sqlite:///./dev.db`（或删掉该行用默认值） |
| `command not found: python3.12` | Homebrew 装好了但不在 PATH | 用全路径 `/opt/homebrew/bin/python3.12`（Intel Mac 为 `/usr/local/bin/python3.12`） |
| 前端报 `502` + 余额/配额提示 | LLM 供应商账户没充值或 key 无效 | 按提示充值，或换 `LLM_PROVIDER` |

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

支持 **Python / JavaScript / Go / Java / C++** 五种语言：

```bash
infra/sandbox/build.sh    # 构建全部 5 个语言镜像
# services/api/.env 中设置 SANDBOX_MODE=docker（默认）
# 无 Docker 的本地开发可设 SANDBOX_MODE=subprocess（无隔离，仅限开发；
# 需要本机装有对应工具链 python3/node/go/javac/g++）
```

- Python 和 JavaScript：题目测试用例自动判分
- Go / Java / C++：编译后运行完整程序（CoderPad 模式），候选人在 main 里自测，
  编译错误和输出原样返回；面试官与评分 Agent 依据代码 + 输出评估

沙箱限制：禁网（`--network none`）、CPU/内存上限（编译型语言放宽到 512-768m）、`--pids-limit`（防 fork bomb）、只读根文件系统 + 可执行 tmpfs（编译产物）、nobody 用户、不传入宿主环境变量、宿主侧超时 kill（编译型语言额外加 20-30s 编译余量）。

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

## 系统设计经典题库

`app/seed_questions.py` 内置 44 道原创出题的经典系统设计题（覆盖业界高频主题：
短链接、KV 存储、消息队列、支付、交易所等基础设施题，以及视觉搜索、推荐系统、
RAG、文生图等 ML/GenAI 系统设计题）。每道题带量化约束和评分 rubric——rubric
就是 Scoring Agent 的期望讨论点清单。新建 system_design 面试时按难度 + 重点领域
从题库抽题；重跑 `python -m app.seed` 即可幂等地把新题合入已有数据库。

## 学习路线与章节测试

- **学习路线**：Onboarding 完成后自动调用 Learning Planner Agent，按面试日期和每周可投入时间生成分周任务序列（`POST /api/plan/generate`，Tasks 页按 Week 分组展示，可随时重新生成，已完成任务保留为历史）。
- **章节测试**：每个知识点有独立题库（`GET /api/quiz/{topic_slug}`），题目不足时由 Quiz Generator Agent 自动补题入库；提交判分（`POST /api/quiz/{topic_slug}/submit`）后更新 Mastery、记录错题到 common_mistakes，得分 ≥60% 自动完成对应的学习任务。

## 语音输入与朗读

面试房间和 Learn 页教练面板都支持语音（走 OpenAI 语音 API，需 `LLM_PROVIDER=openai`）：

- **🎙 语音输入**：点击麦克风开始录音，再点停止，录音自动转文字填入输入框（`POST /api/voice/transcribe`，模型 `gpt-4o-mini-transcribe`，约 $0.003/分钟）。
- **🔊 自动朗读**：打开开关后，面试官/教练的回复自动朗读（`POST /api/voice/tts`，模型 `gpt-4o-mini-tts`，约 $0.015/分钟；音色用 `VOICE_TTS_VOICE` 配置）。
- `MOCK_AI=true` 时两个接口返回固定转写文本和一段静音 WAV，离线/测试可用。
- 浏览器会请求麦克风权限；`localhost` 下 Chrome/Edge/Safari 均可直接使用。

**📞 实时语音通话**（面试房间顶栏）：像打电话一样和面试官实时对谈。浏览器通过
WebRTC 直连 OpenAI Realtime API（`gpt-realtime`），后端只签发 10 分钟有效的临时
密钥（`POST /api/voice/realtime-session`），你的 API key 不会暴露给前端。双方的话
自动转成字幕：实时显示在聊天面板，并写入 `interview_messages`
（`POST /api/voice/realtime-transcript`），评分、报告、学习计划照常生成。需要真实
OpenAI key（`MOCK_AI=false`）；费用约 $0.3~0.5/场。

语音面试官掌控完整的 12 阶段状态机：模型通过 function calling 调用
`advance_stage`（推进阶段，前端阶段条实时跟随）和 `record_observation`
（记录私密评估笔记）。工具调用由浏览器转发到
`POST /api/voice/realtime-tool`；阶段变化和观察以 system 消息落库，
`internal_observation` 照旧只进 Scoring Agent、绝不出现在任何 API 响应中。
评分红线不变：语音面试官只面试不打分。

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
