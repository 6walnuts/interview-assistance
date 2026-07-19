"""Seed learning topics + question bank. Run: python -m app.seed"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import LearningTopic, Question, QuizQuestion

TOPICS: list[dict] = [
    # coding
    {"slug": "arrays", "name": "Arrays", "category": "coding", "difficulty": 1},
    {"slug": "hash-map", "name": "Hash Map", "category": "coding", "difficulty": 1},
    {"slug": "two-pointers", "name": "Two Pointers", "category": "coding", "difficulty": 2},
    {"slug": "sliding-window", "name": "Sliding Window", "category": "coding", "difficulty": 2},
    {"slug": "binary-search", "name": "Binary Search", "category": "coding", "difficulty": 2},
    {"slug": "linked-list", "name": "Linked List", "category": "coding", "difficulty": 2},
    {"slug": "tree", "name": "Tree", "category": "coding", "difficulty": 2},
    {"slug": "graph-bfs-dfs", "name": "Graph / BFS / DFS", "category": "coding", "difficulty": 3},
    {"slug": "heap", "name": "Heap", "category": "coding", "difficulty": 3},
    {"slug": "dynamic-programming", "name": "Dynamic Programming", "category": "coding", "difficulty": 4},
    {"slug": "testing", "name": "Edge Cases & Testing", "category": "coding", "difficulty": 2},
    # backend
    {"slug": "api-design", "name": "API Design", "category": "backend", "difficulty": 2},
    {"slug": "database-index", "name": "Database & Indexing", "category": "backend", "difficulty": 2},
    {"slug": "transactions", "name": "Transactions", "category": "backend", "difficulty": 3},
    {"slug": "caching", "name": "Caching", "category": "backend", "difficulty": 2},
    {"slug": "message-queue", "name": "Message Queue", "category": "backend", "difficulty": 3},
    {"slug": "rate-limiter", "name": "Rate Limiter", "category": "backend", "difficulty": 2},
    {"slug": "idempotency", "name": "Idempotency", "category": "backend", "difficulty": 3},
    # system design
    {"slug": "capacity-estimation", "name": "Capacity Estimation", "category": "system_design", "difficulty": 2},
    {"slug": "sharding", "name": "Sharding", "category": "system_design", "difficulty": 3},
    {"slug": "replication", "name": "Replication", "category": "system_design", "difficulty": 3},
    {"slug": "consistency", "name": "Consistency", "category": "system_design", "difficulty": 4},
    {"slug": "fault-tolerance", "name": "Fault Tolerance", "category": "system_design", "difficulty": 3},
    # cs fundamentals
    {"slug": "concurrency", "name": "Concurrency & Locks", "category": "cs_fundamentals", "difficulty": 3},
    {"slug": "tcp-http", "name": "TCP / HTTP", "category": "cs_fundamentals", "difficulty": 2},
    # infrastructure
    {"slug": "kafka", "name": "Kafka", "category": "infrastructure", "difficulty": 3},
    {"slug": "kubernetes", "name": "Kubernetes", "category": "infrastructure", "difficulty": 3},
    # ai infrastructure
    {"slug": "llm-serving", "name": "LLM Serving & KV Cache", "category": "ai_infrastructure", "difficulty": 4},
    {"slug": "rag-systems", "name": "RAG Systems", "category": "ai_infrastructure", "difficulty": 3},
]

QUESTIONS: list[dict] = [
    {
        "interview_type": "coding", "category": "hash-map", "difficulty": "easy",
        "title": "Two Sum",
        "prompt": "Given an array of integers `nums` and an integer `target`, return the indices "
                  "of the two numbers that add up to `target`. Exactly one solution exists; you may "
                  "not use the same element twice. Implement `def two_sum(nums, target):`.",
        "examples": [{"input": "nums=[2,7,11,15], target=9", "output": "[0,1]"}],
        "constraints": ["2 <= len(nums) <= 10^4", "only one valid answer exists"],
        "test_cases": [
            {"name": "example", "call": "two_sum([2,7,11,15], 9)", "expected": [0, 1]},
            {"name": "negatives", "call": "two_sum([-3,4,3,90], 0)", "expected": [0, 2]},
            {"name": "duplicates", "call": "two_sum([3,3], 6)", "expected": [0, 1]},
        ],
        "rubric": {"optimal": "single-pass hash map, O(n) time / O(n) space"},
    },
    {
        "interview_type": "coding", "category": "sliding-window", "difficulty": "medium",
        "title": "Longest Substring Without Repeating Characters",
        "prompt": "Given a string `s`, return the length of the longest substring without repeating "
                  "characters. Implement `def length_of_longest_substring(s):`.",
        "examples": [{"input": "s='abcabcbb'", "output": "3"}],
        "constraints": ["0 <= len(s) <= 5 * 10^4"],
        "test_cases": [
            {"name": "example", "call": "length_of_longest_substring('abcabcbb')", "expected": 3},
            {"name": "all_same", "call": "length_of_longest_substring('bbbbb')", "expected": 1},
            {"name": "empty", "call": "length_of_longest_substring('')", "expected": 0},
            {"name": "mixed", "call": "length_of_longest_substring('pwwkew')", "expected": 3},
        ],
        "rubric": {"optimal": "sliding window with last-seen index map, O(n)"},
    },
    {
        "interview_type": "coding", "category": "binary-search", "difficulty": "medium",
        "title": "Search in Rotated Sorted Array",
        "prompt": "Given a rotated ascending array `nums` with distinct values and a `target`, return "
                  "its index or -1. Required complexity: O(log n). Implement `def search(nums, target):`.",
        "examples": [{"input": "nums=[4,5,6,7,0,1,2], target=0", "output": "4"}],
        "constraints": ["1 <= len(nums) <= 5000", "all values unique"],
        "test_cases": [
            {"name": "example", "call": "search([4,5,6,7,0,1,2], 0)", "expected": 4},
            {"name": "missing", "call": "search([4,5,6,7,0,1,2], 3)", "expected": -1},
            {"name": "single", "call": "search([1], 1)", "expected": 0},
        ],
        "rubric": {"optimal": "modified binary search identifying the sorted half"},
    },
    {
        "interview_type": "system_design", "category": "rate-limiter", "difficulty": "medium",
        "title": "Design a Distributed Rate Limiter",
        "prompt": "Design a rate limiter for a public API serving 100k requests/second across multiple "
                  "regions. Cover: algorithm choice (token bucket vs sliding window), storage, "
                  "distributed coordination, failure modes, and what happens when the limiter itself "
                  "is down.",
        "examples": [], "constraints": ["p99 added latency < 5ms", "multi-region"],
        "test_cases": [],
        "rubric": {"expected": ["requirements clarification", "algorithm tradeoffs",
                                "Redis vs local counters", "fail-open vs fail-closed", "hot keys"]},
    },
    {
        "interview_type": "system_design", "category": "message-queue", "difficulty": "hard",
        "title": "Design a Streaming Event Pipeline",
        "prompt": "Design a pipeline that ingests clickstream events (1M events/sec), processes them "
                  "with exactly-once semantics, and serves aggregations with < 1 minute freshness. "
                  "Cover: ingestion, partitioning, consumer failure recovery, offset management, "
                  "idempotency, backpressure, and monitoring.",
        "examples": [], "constraints": ["exactly-once end to end", "1M events/sec"],
        "test_cases": [],
        "rubric": {"expected": ["Kafka partitioning", "offset commit strategies", "idempotent sinks",
                                "checkpointing", "DLQ", "lag monitoring"]},
    },
]

QUIZ: list[dict] = [
    {"topic_slug": "kafka",
     "question": "A Kafka consumer commits offsets automatically every 5s and crashes right after "
                 "processing a batch but before the commit. What happens on restart?",
     "options": ["Messages are lost", "The batch is reprocessed (at-least-once)",
                 "Kafka replays from the beginning", "The partition is reassigned permanently"],
     "answer_index": 1,
     "explanation": "Uncommitted offsets mean the consumer resumes from the last committed offset, "
                    "reprocessing the batch — hence sinks must be idempotent."},
    {"topic_slug": "idempotency",
     "question": "Which strategy makes a payment API idempotent?",
     "options": ["Retry with exponential backoff", "Client-generated idempotency key stored with the result",
                 "Optimistic locking on the account row", "At-most-once delivery"],
     "answer_index": 1,
     "explanation": "An idempotency key lets the server detect duplicates and return the stored result."},
]


def seed(db: Session) -> None:
    for t in TOPICS:
        if not db.scalars(select(LearningTopic).where(LearningTopic.slug == t["slug"])).first():
            db.add(LearningTopic(**t))
    db.flush()
    for q in QUESTIONS:
        if not db.scalars(select(Question).where(Question.title == q["title"])).first():
            db.add(Question(**q))
    for quiz in QUIZ:
        topic = db.scalars(select(LearningTopic).where(LearningTopic.slug == quiz["topic_slug"])).first()
        if topic and not db.scalars(select(QuizQuestion).where(
                QuizQuestion.question == quiz["question"])).first():
            db.add(QuizQuestion(topic_id=topic.id, question=quiz["question"], options=quiz["options"],
                                answer_index=quiz["answer_index"], explanation=quiz["explanation"]))
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed(session)
    print("Seeded topics, questions and quizzes.")
