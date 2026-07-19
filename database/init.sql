-- AI Interview Coach — PostgreSQL DDL (mirror of services/api/app/models.py)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(120) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id),
  target_role VARCHAR(120) NOT NULL DEFAULT 'Software Engineer',
  current_level VARCHAR(40) NOT NULL DEFAULT 'mid',
  target_level VARCHAR(40) NOT NULL DEFAULT 'mid',
  target_companies JSONB NOT NULL DEFAULT '[]',
  interview_date DATE,
  weekly_hours INT NOT NULL DEFAULT 5,
  preferred_language VARCHAR(40) NOT NULL DEFAULT 'python',
  locale VARCHAR(10) NOT NULL DEFAULT 'en',
  strengths JSONB NOT NULL DEFAULT '[]',
  weaknesses JSONB NOT NULL DEFAULT '[]',
  resume_text TEXT,
  onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS learning_topics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug VARCHAR(80) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  category VARCHAR(40) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  subtopics JSONB NOT NULL DEFAULT '[]',
  difficulty INT NOT NULL DEFAULT 2,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_learning_topics_category ON learning_topics (category);

CREATE TABLE IF NOT EXISTS user_skill_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  topic_id UUID NOT NULL REFERENCES learning_topics(id),
  skill_level INT NOT NULL DEFAULT 0,
  mastery_score INT NOT NULL DEFAULT 0,
  correct_answers INT NOT NULL DEFAULT 0,
  incorrect_answers INT NOT NULL DEFAULT 0,
  common_mistakes JSONB NOT NULL DEFAULT '[]',
  recommended_next_steps JSONB NOT NULL DEFAULT '[]',
  last_practiced_at TIMESTAMPTZ,
  review_due_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_user_topic UNIQUE (user_id, topic_id)
);
CREATE INDEX IF NOT EXISTS ix_user_skill_profiles_user ON user_skill_profiles (user_id);

CREATE TABLE IF NOT EXISTS questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  interview_type VARCHAR(30) NOT NULL,
  category VARCHAR(60) NOT NULL DEFAULT 'general',
  difficulty VARCHAR(20) NOT NULL DEFAULT 'medium',
  title VARCHAR(200) NOT NULL,
  prompt TEXT NOT NULL,
  examples JSONB NOT NULL DEFAULT '[]',
  constraints JSONB NOT NULL DEFAULT '[]',
  test_cases JSONB NOT NULL DEFAULT '[]',
  rubric JSONB NOT NULL DEFAULT '{}',
  companies JSONB NOT NULL DEFAULT '[]',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_questions_type ON questions (interview_type);

CREATE TABLE IF NOT EXISTS interview_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  role VARCHAR(120) NOT NULL DEFAULT 'Software Engineer',
  level VARCHAR(40) NOT NULL DEFAULT 'mid',
  company_style VARCHAR(80) NOT NULL DEFAULT 'Generic Big Tech',
  interview_type VARCHAR(30) NOT NULL,
  duration_minutes INT NOT NULL DEFAULT 45,
  difficulty VARCHAR(20) NOT NULL DEFAULT 'medium',
  language VARCHAR(40) NOT NULL DEFAULT 'python',
  focus_areas JSONB NOT NULL DEFAULT '[]',
  question_id UUID REFERENCES questions(id),
  current_stage VARCHAR(40) NOT NULL DEFAULT 'introduction',
  hint_count INT NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_interview_sessions_user_status ON interview_sessions (user_id, status);

CREATE TABLE IF NOT EXISTS learning_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  topic_slug VARCHAR(80),
  task_type VARCHAR(30) NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  payload JSONB NOT NULL DEFAULT '{}',
  source VARCHAR(30) NOT NULL DEFAULT 'coach',
  source_session_id UUID REFERENCES interview_sessions(id),
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  due_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_learning_tasks_user_status ON learning_tasks (user_id, status);

CREATE TABLE IF NOT EXISTS learning_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  topic_id UUID REFERENCES learning_topics(id),
  mode VARCHAR(30) NOT NULL DEFAULT 'explain',
  summary TEXT NOT NULL DEFAULT '',
  duration_minutes INT NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_learning_sessions_user ON learning_sessions (user_id);

CREATE TABLE IF NOT EXISTS interview_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES interview_sessions(id),
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  stage VARCHAR(40) NOT NULL DEFAULT 'introduction',
  internal_observation JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_interview_messages_session_created
  ON interview_messages (session_id, created_at);

CREATE TABLE IF NOT EXISTS candidate_code_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES interview_sessions(id),
  language VARCHAR(40) NOT NULL DEFAULT 'python',
  code TEXT NOT NULL,
  label VARCHAR(40) NOT NULL DEFAULT 'run',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_code_versions_session ON candidate_code_versions (session_id);

CREATE TABLE IF NOT EXISTS code_execution_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES interview_sessions(id),
  code_version_id UUID NOT NULL REFERENCES candidate_code_versions(id),
  stdout TEXT NOT NULL DEFAULT '',
  stderr TEXT NOT NULL DEFAULT '',
  exit_code INT NOT NULL DEFAULT 0,
  timed_out BOOLEAN NOT NULL DEFAULT FALSE,
  duration_ms INT NOT NULL DEFAULT 0,
  test_results JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_code_execution_results_session ON code_execution_results (session_id);

CREATE TABLE IF NOT EXISTS interview_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES interview_sessions(id),
  dimension VARCHAR(60) NOT NULL,
  score INT NOT NULL,
  evidence TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_interview_scores_session ON interview_scores (session_id);

CREATE TABLE IF NOT EXISTS interview_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL UNIQUE REFERENCES interview_sessions(id),
  interview_summary TEXT NOT NULL DEFAULT '',
  overall_score NUMERIC(3,1) NOT NULL DEFAULT 0,
  hire_signal VARCHAR(30) NOT NULL DEFAULT 'mixed',
  level_assessment VARCHAR(120) NOT NULL DEFAULT '',
  scores JSONB NOT NULL DEFAULT '{}',
  strengths JSONB NOT NULL DEFAULT '[]',
  weaknesses JSONB NOT NULL DEFAULT '[]',
  key_mistakes JSONB NOT NULL DEFAULT '[]',
  missed_opportunities JSONB NOT NULL DEFAULT '[]',
  hints_used JSONB NOT NULL DEFAULT '[]',
  evidence JSONB NOT NULL DEFAULT '[]',
  ideal_answer_outline JSONB NOT NULL DEFAULT '[]',
  recommended_practice JSONB NOT NULL DEFAULT '[]',
  next_interview_focus JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS review_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES interview_sessions(id),
  user_id UUID NOT NULL REFERENCES users(id),
  diagnosed_weakness VARCHAR(255) NOT NULL DEFAULT '',
  topic_slug VARCHAR(80),
  task_type VARCHAR(30) NOT NULL DEFAULT 'learn',
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_review_tasks_session ON review_tasks (session_id);
CREATE INDEX IF NOT EXISTS ix_review_tasks_user ON review_tasks (user_id);

CREATE TABLE IF NOT EXISTS quiz_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id UUID NOT NULL REFERENCES learning_topics(id),
  question TEXT NOT NULL,
  options JSONB NOT NULL DEFAULT '[]',
  answer_index INT NOT NULL,
  explanation TEXT NOT NULL DEFAULT '',
  difficulty INT NOT NULL DEFAULT 2,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_topic ON quiz_questions (topic_id);

CREATE TABLE IF NOT EXISTS quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  quiz_question_id UUID NOT NULL REFERENCES quiz_questions(id),
  selected_index INT NOT NULL,
  is_correct BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_quiz_attempts_user ON quiz_attempts (user_id);
