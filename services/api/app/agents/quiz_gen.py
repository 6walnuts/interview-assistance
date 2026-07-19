"""Quiz Generator: fills a topic's question bank with graded multiple-choice items."""
from ..models import LearningTopic, UserProfile
from .agent_schemas import GeneratedQuiz, GeneratedQuizQuestion
from .llm import complete_json
from .prompts import QUIZ_GEN_SYSTEM


def _mock_quiz(topic: LearningTopic, count: int, offset: int = 0) -> GeneratedQuiz:
    questions = []
    for i in range(count):
        questions.append(GeneratedQuizQuestion(
            question=f"({topic.name}) Concept check #{offset + i + 1}: which statement about "
                     f"{topic.name.lower()} is correct?",
            options=[
                f"The correct core property of {topic.name.lower()} (mock answer)",
                "A plausible but wrong statement",
                "Another common misconception",
                "An unrelated statement",
            ],
            answer_index=0,
            explanation=f"Mock mode: option 1 states the core property of {topic.name}. "
                        "Configure a real LLM provider for substantive questions.",
            difficulty=topic.difficulty,
        ))
    return GeneratedQuiz(questions=questions)


def generate_quiz(
    topic: LearningTopic,
    count: int,
    existing_questions: list[str],
    profile: UserProfile | None,
) -> GeneratedQuiz:
    system = QUIZ_GEN_SYSTEM.format(
        count=count,
        topic=topic.name,
        category=topic.category,
        level=profile.target_level if profile else "mid",
        role=profile.target_role if profile else "Software Engineer",
        difficulty=topic.difficulty,
        existing="; ".join(q[:80] for q in existing_questions[:20]) or "(none)",
    )
    messages = [{"role": "user", "content": f"Write the {count} questions now."}]
    quiz = complete_json(system, messages, GeneratedQuiz,
                         lambda: _mock_quiz(topic, count, offset=len(existing_questions)))
    # Guard against models returning an out-of-range answer index.
    quiz.questions = [q for q in quiz.questions if 0 <= q.answer_index < len(q.options)]
    return quiz
