# 第二部分：技术架构

## 总览

```
┌─────────────────────────────────────────────────────────┐
│  apps/web  (Next.js 14 App Router, TS, Tailwind)        │
│  Landing / Onboarding / Dashboard / Interview Room /    │
│  Report / Tasks / Progress   (Monaco Editor)            │
└──────────────────────┬──────────────────────────────────┘
                       │ REST (JSON, JWT Bearer)
┌──────────────────────▼──────────────────────────────────┐
│  services/api  (FastAPI + Pydantic v2 + SQLAlchemy 2)   │
│  routers: auth / profile / topics / tasks / interviews  │
│           / progress / coach                            │
│  services: interview_service / sandbox / progress       │
│  agents:  planner / interviewer / code_evaluator /      │
│           scorer / review_task_generator / coach /      │
│           learning_planner                              │
└───────┬─────────────┬──────────────┬────────────────────┘
        │             │              │
   PostgreSQL      Redis       Docker Sandbox (python:3.12-slim)
   (业务数据)   (session/cache)  --network none, CPU/mem/timeout 限制
                                      │
                               OpenAI API (结构化 JSON 输出)
```

## 前端架构（apps/web）

- **Next.js 14 App Router + TypeScript + Tailwind CSS**；组件风格对齐 shadcn/ui（MVP 用轻量自建组件，避免初期依赖锁定）。
- `lib/api.ts`：统一的类型化 API client（fetch + JWT 注入 + 错误归一化）。
- `lib/types.ts`：与后端 Pydantic schema 对齐的 TS 类型。
- Interview Room：左侧聊天面板（阶段徽章 + 剩余时间），右侧按面试类型切换 Monaco Editor（coding）或设计白板 textarea（system design）；底部 Run Code / Submit / Request Hint / End Interview。
- 状态管理：MVP 用 React state + SWR 风格轮询，不引入重型状态库。

## 后端架构（services/api）

分层：`routers`（HTTP + 校验 + 权限）→ `services`（业务编排）→ `agents`（LLM 调用）→ `models`（SQLAlchemy）。

- 认证：JWT（HS256），`Authorization: Bearer`；密码 PBKDF2-HMAC-SHA256。
- 所有 AI 输出用 Pydantic schema 校验（OpenAI structured output / json mode），解析失败自动重试一次后降级为显式错误。
- `MOCK_AI=true` 时使用确定性 mock agent（无需 API key 即可本地跑通全流程与测试）。

## Agent 架构

7 个职责单一的 Agent，禁止超大 prompt：

| Agent | 输入 | 输出 | 调用时机 |
|---|---|---|---|
| Interview Planner | 面试配置、用户画像 | 选题 + 评分标准 | 创建面试时 |
| Mock Interviewer | 对话历史、题目、阶段状态机 | `{message, stage, action, internal_observation}` | 每轮候选人消息 |
| Code Evaluator | 代码 + 沙箱执行结果 + 测试 | 测试结论、代码质量观察 | Run Code / Submit |
| Scoring Agent | 完整 transcript、代码版本、执行结果、提示记录、internal observations | 完整报告 JSON | End Interview |
| Review Task Generator | 面试报告 | 弱点诊断 + 任务列表 | 报告生成后 |
| Learning Planner | 用户画像 + 技能状态 + 任务 | 日/周学习计划 | Onboarding / 每日 |
| Interview Coach | 用户问题 + 技能状态 | 教学式回答（Explain/Quiz/...） | Learn/Practice 对话 |

工作流：

```
POST /interviews → Planner 选题 → Interviewer 开场
每轮消息 → Interviewer（状态机推进，内部观察落库，候选人只见 message）
Run Code → Sandbox 执行 → Code Evaluator 记录
End → Scoring Agent（独立评分，绝不由 Interviewer 自评）
    → Review Task Generator → learning_tasks / review_tasks 落库
    → 更新 user_skill_profiles
```

## 代码执行架构（Docker Sandbox）

`services/api/app/services/sandbox.py`，通过 `docker run` 执行：

```
docker run --rm -i \
  --network none            # 禁网
  --cpus 0.5 --memory 256m  # CPU / 内存限制
  --pids-limit 64           # 防 fork bomb
  --read-only --tmpfs /tmp:size=16m,exec  # 限制文件访问
  --env-file /dev/null      # 不暴露环境变量
  --user 65534:65534        # nobody
  ai-coach-sandbox:latest python /tmp/main.py
```

- 宿主侧 `subprocess` 超时（默认 10s）双保险防死循环；超时 kill 容器。
- 代码通过 stdin/tmpfs 传入，不挂载宿主目录。
- `SANDBOX_MODE=subprocess` 仅供无 Docker 的本地开发（不安全，文档明示）。

## 数据库架构

PostgreSQL（生产）；本地默认 SQLite 快速启动。SQLAlchemy 2.0 声明式模型，Alembic 管理迁移；`database/init.sql` 提供完整 DDL。详见 `03-data-model.md`。

Redis：会话缓存、面试房间的轻量状态（剩余时间、限流）；MVP 中可选。

## 部署架构（第一版）

| 组件 | 平台 |
|---|---|
| apps/web | Vercel |
| services/api | Railway 或 Render（Docker 部署，需支持 DinD 或改用托管沙箱） |
| PostgreSQL | Supabase 或 Neon |
| Redis | Redis Cloud（可选） |

密钥全部走环境变量（`.env.example` 列出），仓库零硬编码。
