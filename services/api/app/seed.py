"""Seed learning topics + question bank. Run: python -m app.seed"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, SessionLocal, engine
from .models import LearningTopic, Question, QuizQuestion
from .seed_questions import CLASSIC_QUESTIONS

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
    {"slug": "ood", "name": "Object-Oriented Design", "category": "cs_fundamentals", "difficulty": 2},
    # infrastructure
    {"slug": "kafka", "name": "Kafka", "category": "infrastructure", "difficulty": 3},
    {"slug": "kubernetes", "name": "Kubernetes", "category": "infrastructure", "difficulty": 3},
    # ai infrastructure
    {"slug": "llm-serving", "name": "LLM Serving & KV Cache", "category": "ai_infrastructure", "difficulty": 4},
    {"slug": "rag-systems", "name": "RAG Systems", "category": "ai_infrastructure", "difficulty": 3},
    # 八股文 (CN interview canon: the rote-knowledge backbone of domestic backend interviews)
    {"slug": "java-basics", "name": "Java 基础与集合", "category": "bagu", "difficulty": 2},
    {"slug": "java-concurrency", "name": "Java 并发", "category": "bagu", "difficulty": 3},
    {"slug": "jvm", "name": "JVM 原理", "category": "bagu", "difficulty": 3},
    {"slug": "spring", "name": "Spring 全家桶", "category": "bagu", "difficulty": 2},
    {"slug": "mysql", "name": "MySQL", "category": "bagu", "difficulty": 2},
    {"slug": "redis", "name": "Redis", "category": "bagu", "difficulty": 2},
    {"slug": "computer-network", "name": "计算机网络", "category": "bagu", "difficulty": 2},
    {"slug": "operating-system", "name": "操作系统", "category": "bagu", "difficulty": 2},
    {"slug": "distributed-systems", "name": "分布式与高并发", "category": "bagu", "difficulty": 3},
    {"slug": "mq", "name": "消息队列", "category": "bagu", "difficulty": 2},
    # machine learning (domain knowledge: theory & algorithms, vs. ai_infrastructure's engineering)
    {"slug": "ml-fundamentals", "name": "Bias-Variance & Overfitting", "category": "machine_learning", "difficulty": 2},
    {"slug": "supervised-learning", "name": "Supervised Learning Models", "category": "machine_learning", "difficulty": 2},
    {"slug": "feature-engineering", "name": "Feature Engineering", "category": "machine_learning", "difficulty": 2},
    {"slug": "model-evaluation", "name": "Model Evaluation & Metrics", "category": "machine_learning", "difficulty": 2},
    {"slug": "neural-networks", "name": "Neural Networks & Backprop", "category": "machine_learning", "difficulty": 3},
    {"slug": "training-optimization", "name": "Training & Optimization", "category": "machine_learning", "difficulty": 3},
    {"slug": "embeddings", "name": "Embeddings & Representations", "category": "machine_learning", "difficulty": 3},
    {"slug": "transformers", "name": "Transformers & Attention", "category": "machine_learning", "difficulty": 4},
    {"slug": "llm-fine-tuning", "name": "LLM Fine-tuning (SFT / LoRA / RLHF)", "category": "machine_learning", "difficulty": 4},
    {"slug": "recommendation-systems", "name": "Recommendation Systems", "category": "machine_learning", "difficulty": 3},
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
    {"topic_slug": "ml-fundamentals",
     "question": "Your model has 99% training accuracy but 70% validation accuracy. What is the most "
                 "likely problem and a reasonable first fix?",
     "options": ["Underfitting — add more layers", "Overfitting — add regularization or more data",
                 "Data leakage — remove the validation set", "Vanishing gradients — switch to ReLU"],
     "answer_index": 1,
     "explanation": "A large train/validation gap signals high variance (overfitting); regularization, "
                    "dropout, early stopping or more data narrow the gap."},
    {"topic_slug": "mysql",
     "question": "InnoDB 的普通二级索引查询 `select * from t where name='x'` 通常需要回表，"
                 "以下哪种手段最直接地避免回表？",
     "options": ["把 name 列改成主键", "对查询列建立覆盖索引（联合索引包含所需列）",
                 "增大 buffer pool", "改用哈希索引"],
     "answer_index": 1,
     "explanation": "覆盖索引让二级索引本身就包含查询所需的全部列，服务器无需回聚簇索引取整行，"
                    "这是最常用的避免回表手段。"},
    {"topic_slug": "redis",
     "question": "Redis 同时开启 RDB 和 AOF 时，重启后以哪份数据恢复？为什么？",
     "options": ["RDB，因为快照更完整", "AOF，因为它通常拥有更完整的最近写入",
                 "两者合并恢复", "取决于文件哪个更大"],
     "answer_index": 1,
     "explanation": "AOF 记录每条写命令、丢数据窗口更小，所以两者并存时 Redis 优先用 AOF 恢复；"
                    "RDB 只作为兜底快照。"},
    {"topic_slug": "computer-network",
     "question": "TCP 挥手后主动关闭方进入 TIME_WAIT 等待 2MSL，最主要是为了什么？",
     "options": ["节省服务器端口", "确保最后一个 ACK 丢失时能重发，并让旧连接的报文在网络中消亡",
                 "给应用层时间清理缓冲区", "防止 SYN 洪泛攻击"],
     "answer_index": 1,
     "explanation": "2MSL 等待既保证对端未收到最后 ACK 时的 FIN 重传还能得到响应，"
                    "也确保本连接的旧报文全部过期，不会串入使用相同四元组的新连接。"},
    {"topic_slug": "java-concurrency",
     "question": "volatile 能保证可见性和有序性，但不能保证原子性。下面哪个场景用 volatile 就足够？",
     "options": ["多线程对同一计数器做 i++", "一个线程写状态标志位、其他线程读它退出循环",
                 "实现无锁队列的出入队", "多线程更新共享的 HashMap"],
     "answer_index": 1,
     "explanation": "状态标志位是单写多读、且写操作本身是单次赋值，volatile 的可见性保证足够；"
                    "复合操作（读-改-写）仍需要锁或 CAS。"},
    {"topic_slug": "transformers",
     "question": "In self-attention, why is the dot product of queries and keys divided by sqrt(d_k)?",
     "options": ["To keep the sequence length constant", "To normalize the value vectors",
                 "To stop softmax saturating when dot products grow with dimension",
                 "To make attention weights sum to 1"],
     "answer_index": 2,
     "explanation": "Dot products scale with dimension d_k; dividing by sqrt(d_k) keeps their variance "
                    "stable so softmax gradients don't vanish."},
]


def seed(db: Session) -> None:
    for t in TOPICS:
        if not db.scalars(select(LearningTopic).where(LearningTopic.slug == t["slug"])).first():
            db.add(LearningTopic(**t))
    db.flush()
    for q in [*QUESTIONS, *CLASSIC_QUESTIONS]:
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
