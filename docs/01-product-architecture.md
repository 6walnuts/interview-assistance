# 第一部分：产品架构

## 1. 产品定位

**AI Interview Coach** —— 面向 SDE / Backend / Infra / AI Infra 候选人的 AI 面试教练平台。

与一次性模拟面试工具的核心差异：**闭环**。

```
学习 (Learn)
  → 专项练习 (Practice)
  → 模拟面试 (Mock Interview)
  → 自动评分 (Scoring)
  → 面试复盘 (Review)
  → 个性化学习计划 (Plan)
  → 再次练习
```

### 候选商业化英文名（5 个）

| 名称 | 说明 |
|---|---|
| **Offerloop** | 强调"闭环 → 拿 offer"，域名友好 |
| **Hirely** | 简短、SaaS 感强 |
| **MockMentor** | 模拟面试 + 教练双关 |
| **Interview Forge** | "锻造"面试能力，工程师审美 |
| **SignalPrep** | 呼应面试官术语 "hiring signal" |

### 目标用户

- 准备 SWE 面试的学生（New Grad / Intern）
- Junior → Staff 各级别在职工程师
- Backend / Infrastructure / Distributed Systems / AI Infra 方向候选人
- 目标 Google / Meta / Amazon / Microsoft / OpenAI 等公司的用户

### 解决的问题 → 对应模块

| 用户问题 | 解决模块 |
|---|---|
| 不知道该学什么 | Learn（知识地图）+ Learning Planner |
| 刷题多但没有能力地图 | Progress（Mastery / 雷达图） |
| 缺少接近真人的面试训练 | Mock Interviewer Agent（状态机驱动） |
| 面试后不知道怎么继续学 | Scoring → Review Task Generator → 学习任务 |
| 无法长期追踪进步 | user_skill_profiles + 得分趋势 |
| 现有工具只有一次性问答 | 报告自动转化为学习计划（核心闭环） |

## 2. 用户流程

```
注册/登录
  → Onboarding（岗位、级别、公司、面试日期、每周时间、强弱项、简历）
  → Dashboard（今日任务 / 下次面试 / 薄弱项）
  ├─ Learn：知识地图 → Coach Agent 讲解 / Quiz / Flashcards
  ├─ Practice：Daily Drill / Coding / Quiz / 错题复习
  ├─ Mock Interview：Setup → Interview Room → End
  │     → Scoring Agent 评分 → Review 页（报告）
  │     → Review Task Generator 自动生成学习任务 → 回到 Dashboard
  └─ Progress：雷达图 / 趋势 / 面试历史
```

## 3. MVP 范围（第一版）

**实现：**
1. 注册 / 登录（JWT）
2. 目标岗位与级别设置（Onboarding）
3. Coding 模拟面试（文本对话 + Monaco Editor + Python 执行）
4. Backend System Design 模拟面试（文本对话 + 文本白板）
5. Docker 沙箱 Python 代码执行
6. Scoring Agent 独立评分 → 面试报告页
7. Review Task Generator 自动生成 ≥3 个学习任务
8. 学习任务页（Tasks）
9. 基础 Progress Dashboard（Mastery + 面试历史）

**不实现（明确砍掉）：** 视频/语音面试、表情与眼神分析、多人面试、移动/桌面端、社交、公司招聘端、推荐算法、多模型路由、多语言代码执行、实时协同白板。

## 4. 页面结构

| 路由 | 页面 | MVP |
|---|---|---|
| `/` | Landing：价值主张、五模块、示例报告、CTA | ✅ |
| `/register` `/login` | 注册登录 | ✅ |
| `/onboarding` | 目标岗位/级别/公司/日期/时间/强弱项 | ✅ |
| `/dashboard` | 今日任务、下次面试、最近成绩、薄弱项 | ✅ |
| `/learn` | 知识地图（7 大方向 → 知识点 → Mastery） | ✅（简版） |
| `/practice` | Daily Drill / Quiz / 错题复习 | ✅（简版） |
| `/interviews/new` | Mock Interview Setup | ✅ |
| `/interviews/[id]` | Interview Room（左聊天，右 Editor/白板） | ✅ |
| `/interviews/[id]/report` | Review 页：评分、Hire Signal、学习计划 | ✅ |
| `/tasks` | 学习任务列表 | ✅ |
| `/progress` | 能力雷达、趋势、面试历史 | ✅（简版） |

## 5. 功能优先级

| 优先级 | 功能 | 理由 |
|---|---|---|
| P0 | 面试房间 + Interviewer Agent 状态机 | 产品核心体验 |
| P0 | Scoring Agent + 报告页 | 差异化：真实 hiring signal |
| P0 | 报告 → 学习任务闭环 | 产品最重要的功能闭环 |
| P0 | 代码沙箱执行 | Coding 面试的可信度 |
| P1 | Onboarding + Dashboard | 留存入口 |
| P1 | Tasks / Progress | 闭环可见性 |
| P2 | Learn / Practice / Coach 对话 | 内容型模块，可持续迭代 |
| P3 | 语音、简历深挖、公司风格库 | 后续版本 |
