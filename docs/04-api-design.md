# 第四部分：REST API 设计

- Base URL：`/api`；除 auth 外全部需要 `Authorization: Bearer <jwt>`。
- 错误统一格式：`{"detail": "..."}`；`401` 未认证、`403` 无权访问他人资源、`404` 不存在、`409` 状态冲突、`422` 校验失败。
- 完整 Pydantic schema 见 `services/api/app/schemas/`。

## Auth

### POST /api/auth/register （公开）
Req `{email, password(≥8), name}` → 201 `{access_token, token_type:"bearer", user:{id,email,name}}`；409 邮箱已存在。

### POST /api/auth/login （公开）
Req `{email, password}` → 200 同上；401 凭据错误。

## Profile

### GET /api/profile
→ `{user:{id,email,name}, profile:{target_role,current_level,target_level,target_companies,interview_date,weekly_hours,preferred_language,strengths,weaknesses,onboarding_completed}}`

### PUT /api/profile
Req：profile 字段任意子集（部分更新）→ 200 同 GET。用于 Onboarding 提交。

## Topics（Learn）

### GET /api/topics?category=coding
→ `[{id,slug,name,category,description,difficulty,mastery:{skill_level,mastery_score,review_due_at}|null}]`

### GET /api/topics/{topic_id}
→ 单个 topic + 该用户 mastery + 该 topic 下 quiz 数量。404 不存在。

## Tasks（学习任务）

### GET /api/tasks?status=pending
→ `[{id,title,description,task_type,topic_slug,source,source_session_id,status,due_at,payload}]`（按 due_at/created_at 排序）

### POST /api/tasks/{task_id}/complete
→ 200 更新后的 task；403 非本人任务；409 已完成。副作用：更新对应 `user_skill_profiles.mastery_score`。

## Interviews（核心）

### POST /api/interviews
Req：
```json
{"interview_type":"coding|system_design","role":"Senior Backend Engineer",
 "level":"junior|mid|senior|staff","company_style":"Generic Big Tech",
 "duration_minutes":45,"difficulty":"easy|medium|hard","language":"python",
 "focus_areas":["arrays","hash_map"]}
```
→ 201 `{session:{...}, question:{title,prompt,examples,constraints}, opening_message:{...}}`
（Interview Planner 选题 → Interviewer 生成开场白，状态机进入 `introduction`。）

### GET /api/interviews/{session_id}
→ `{session, question, messages:[{id,role,content,stage,created_at}]}`（**internal_observation 永不返回**）；403 非本人。

### POST /api/interviews/{session_id}/messages
Req `{content, action?: "message"|"ask_clarification"|"request_hint"}` → 200 `{message:{role:"interviewer",content,stage}, current_stage}`；409 面试已结束。request_hint 会递增 hint_count 并记录到 hints_used。

### POST /api/interviews/{session_id}/run-code
Req `{code, language:"python", label:"run"|"submit"}` → 200
`{execution:{stdout,stderr,exit_code,timed_out,duration_ms,test_results:[{name,passed,detail}]}}`；409 已结束；422 非 coding 面试。

### POST /api/interviews/{session_id}/end
→ 200 `{report_id, review_task_count}`。流程：Scoring Agent 独立评分 → 落库 report/scores → Review Task Generator 生成 review_tasks + learning_tasks（≥3）→ 更新 user_skill_profiles。幂等：已结束的 session 直接返回既有 report。

### GET /api/interviews/{session_id}/report
→ 完整报告 JSON（interview_summary, overall_score, hire_signal, level_assessment, scores, strengths, weaknesses, key_mistakes, missed_opportunities, hints_used, evidence, ideal_answer_outline, recommended_practice, next_interview_focus）；404 未评分。

### GET /api/interviews/{session_id}/review-tasks
→ `[review_task]`。

## Progress

### GET /api/progress
→ `{streak_days, tasks_completed, interviews_completed, avg_recent_score, weak_topics:[...], readiness:{role,level,score}}`

### GET /api/progress/skills
→ `[{topic_slug,name,category,skill_level,mastery_score,last_practiced_at}]`（雷达图数据源）

### GET /api/progress/interviews
→ `[{session_id,interview_type,role,level,overall_score,hire_signal,ended_at}]`（趋势图数据源）

## Coach（P2，已含最小实现）

### POST /api/coach/chat
Req `{message, topic_slug?, mode?: "explain"|"quiz"|"flashcards"|"review_mistakes"|"plan"}` → `{reply, suggested_actions:[...]}`
