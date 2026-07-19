# 第七部分：开发计划（分四阶段）

## Phase 1 — 可运行骨架（本仓库当前状态）

**目标**：端到端闭环在本地跑通（mock AI 亦可）。

任务：
- Monorepo 结构、FastAPI 骨架、SQLAlchemy 全部数据模型、JWT 认证
- Interview Planner / Mock Interviewer / Scoring / Review Task Generator 四个 Agent（结构化 JSON + Pydantic 校验 + mock 模式）
- Docker 沙箱 Python 执行（禁网/限 CPU/限内存/超时/pids-limit）
- Next.js 页面：Landing、注册登录、Onboarding、Dashboard、Interview Setup、Interview Room（Monaco）、Report、Tasks、Progress
- 题库与知识点 seed、pytest 端到端测试

交付物：本仓库代码 + `docs/` + README。
验收标准：`pytest` 全绿；本地起前后端后可完成「创建面试 → 对话 → 跑代码 → 结束 → 看报告 → 自动出现 ≥3 个学习任务」。

## Phase 2 — 真实 AI 质量与内容

目标：接入 OpenAI 后体验达到"可给真实用户用"。
任务：调优四个 Prompt 并建立离线评测集（10 段标注面试对话回归测试评分稳定性）；扩充题库（Coding 30 题 / System Design 10 题，带 test_cases 与 rubric）；Coach Agent 的 Quiz / Flashcards / Explain 模式；user_skill_profiles 随任务完成与面试结果更新；面试计时与阶段自动推进。
交付物：评测脚本 + 内容库 + Coach 页面。
验收标准：评分与人工标注 hire_signal 一致率 ≥70%；同一 transcript 重复评分方差 ≤0.5。

## Phase 3 — 闭环深化与留存

目标：让用户"回来"。
任务：Learning Planner 的每日/每周计划与 review_due_at 间隔复习；Dashboard streak 与今日任务推送（邮件）；Progress 雷达图与趋势图完善；错题本（common_mistakes 聚合）；报告页"一键开始复习任务"。
验收标准：完成一次面试的用户 7 日内回访率可度量；任务完成率埋点上线。

## Phase 4 — 商业化与扩展

目标：可收费、可扩展。
任务：订阅与用量计费（面试次数）；语音模式（STT/TTS）；简历深挖与 Behavioral 面试类型上线；公司风格题库（Google/Meta/Amazon 风格差异）；沙箱多语言（Java/Go/C++，按语言镜像隔离）；托管沙箱服务替换 DinD。
验收标准：付费转化漏斗埋点；沙箱 P95 执行延迟 <3s。

---

# 第六部分：项目目录（映射说明）

```
interview-assistance/
├── apps/
│   └── web/                    # Next.js 14 前端
│       ├── app/                # App Router 页面
│       ├── components/
│       └── lib/                # api client / types / auth
├── packages/                   # （预留）共享 TS 类型包
├── services/
│   └── api/                    # FastAPI 后端
│       ├── app/
│       │   ├── agents/         # 7 个 Agent + prompts + LLM 封装
│       │   ├── routers/        # HTTP 层
│       │   ├── services/       # 业务编排 / 沙箱
│       │   ├── schemas/        # Pydantic
│       │   ├── models.py       # SQLAlchemy（全部 16 张表）
│       │   ├── seed.py         # 题库与知识点种子
│       │   └── main.py
│       └── tests/              # pytest 端到端测试
├── database/
│   ├── init.sql                # 完整 DDL（Postgres）
│   └── alembic/                # 迁移脚手架
├── infra/
│   ├── docker-compose.yml      # postgres + redis + api
│   └── sandbox/Dockerfile      # 代码执行沙箱镜像
└── docs/                       # 设计文档（本目录）
```
