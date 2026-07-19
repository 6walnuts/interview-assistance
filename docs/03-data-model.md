# 第三部分：数据模型

约定：所有表主键 `id UUID`（默认 `gen_random_uuid()`）；均含 `created_at`、`updated_at TIMESTAMPTZ`；软状态用 `status`；JSON 字段在 Postgres 中为 `JSONB`。完整 DDL 见 `database/init.sql`，SQLAlchemy 模型见 `services/api/app/models.py`。

## users
| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid PK | |
| email | varchar(255) UNIQUE, index | 登录名 |
| password_hash | varchar(255) | PBKDF2 |
| name | varchar(120) | |
| status | varchar(20) | active / disabled |

## user_profiles（1:1 users）
| 字段 | 类型 |
|---|---|
| user_id | uuid FK→users UNIQUE |
| target_role | varchar(120)（如 Senior Backend Engineer） |
| current_level / target_level | varchar(40)（junior/mid/senior/staff） |
| target_companies | jsonb（["Google","OpenAI"]） |
| interview_date | date NULL |
| weekly_hours | int |
| preferred_language | varchar(40)（python 等） |
| strengths / weaknesses | jsonb（topic slug 数组） |
| resume_text | text NULL |
| onboarding_completed | boolean |

## learning_topics（知识地图节点）
| 字段 | 类型 |
|---|---|
| slug | varchar(80) UNIQUE, index |
| name | varchar(120) |
| category | varchar(40) index（coding / backend / system_design / cs_fundamentals / infrastructure / ai_infrastructure / behavioral） |
| description | text |
| subtopics | jsonb |
| difficulty | int（1-5） |
| status | varchar(20) |

## user_skill_profiles（用户 × 知识点，Coach 维护的学习状态）
| 字段 | 类型 |
|---|---|
| user_id | uuid FK→users, index |
| topic_id | uuid FK→learning_topics |
| skill_level | int（0-5） |
| mastery_score | int（0-100） |
| correct_answers / incorrect_answers | int |
| common_mistakes | jsonb |
| recommended_next_steps | jsonb |
| last_practiced_at / review_due_at | timestamptz NULL |
| UNIQUE(user_id, topic_id) | |

## learning_tasks（闭环产物：报告 → 任务）
| 字段 | 类型 |
|---|---|
| user_id | uuid FK, index |
| topic_slug | varchar(80) NULL |
| task_type | varchar(30)（learn / practice / quiz / design_drill / mock_interview） |
| title | varchar(255)；description text |
| payload | jsonb（quiz 题目、练习配置、下次面试配置等） |
| source | varchar(30)（interview_report / coach / onboarding） |
| source_session_id | uuid FK→interview_sessions NULL |
| status | varchar(20)（pending / in_progress / completed）index |
| due_at / completed_at | timestamptz NULL |

## learning_sessions（Coach 对话/练习会话）
user_id FK · topic_id FK NULL · mode varchar(30)（explain/quiz/flashcards/...）· summary text · duration_minutes int · status

## questions（题库）
| 字段 | 类型 |
|---|---|
| interview_type | varchar(30) index（coding / system_design / ...） |
| category | varchar(60)；difficulty varchar(20)（easy/medium/hard） |
| title varchar(200)；prompt text |
| examples / constraints | jsonb |
| test_cases | jsonb（[{input, expected, hidden}]） |
| rubric | jsonb（评分标准） |
| companies | jsonb；status |

## interview_sessions
| 字段 | 类型 |
|---|---|
| user_id | uuid FK index |
| role varchar(120) · level varchar(40) · company_style varchar(80) |
| interview_type | varchar(30)（coding / system_design） |
| duration_minutes int · difficulty varchar(20) · language varchar(40) |
| focus_areas | jsonb |
| question_id | uuid FK→questions NULL |
| current_stage | varchar(40)（状态机 12 阶段） |
| hint_count | int |
| status | varchar(20)（in_progress / completed / abandoned）index |
| started_at / ended_at | timestamptz |

## interview_messages
session_id FK index · role varchar(20)（interviewer/candidate/system）· content text · stage varchar(40) · internal_observation jsonb NULL（仅面试官消息，永不下发前端）· created_at index

## candidate_code_versions
session_id FK index · language varchar(40) · code text · label varchar(40)（run/submit）

## code_execution_results
session_id FK · code_version_id FK→candidate_code_versions · stdout text · stderr text · exit_code int · timed_out bool · duration_ms int · test_results jsonb

## interview_scores（单维度得分，便于聚合查询）
session_id FK index · dimension varchar(60) · score int（1-5）· evidence text

## interview_reports（1:1 session）
session_id FK UNIQUE · interview_summary text · overall_score numeric(3,1) · hire_signal varchar(30)（strong_no_hire…strong_hire）· level_assessment varchar(120) · scores jsonb · strengths / weaknesses / key_mistakes / missed_opportunities / hints_used / evidence / ideal_answer_outline / recommended_practice / next_interview_focus 均 jsonb

## review_tasks（报告诊断出的复盘任务）
session_id FK index · user_id FK index · diagnosed_weakness varchar(255) · topic_slug varchar(80) · task_type varchar(30) · title varchar(255) · description text · status varchar(20)

## quiz_questions
topic_id FK index · question text · options jsonb · answer_index int · explanation text · difficulty int · status

## quiz_attempts
user_id FK index · quiz_question_id FK · selected_index int · is_correct bool

## 索引策略小结
- 高频查询路径：`interview_messages(session_id, created_at)`、`learning_tasks(user_id, status)`、`user_skill_profiles(user_id)`、`interview_sessions(user_id, status)`。
- 唯一约束：`users.email`、`user_profiles.user_id`、`user_skill_profiles(user_id, topic_id)`、`interview_reports.session_id`、`learning_topics.slug`。
