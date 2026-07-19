"""Classic system-design question bank.

Original prompts and rubrics written for this project, covering the classic
interview problems popularized by the ByteByteGo / Alex Xu book series
(System Design Interview Vol 1 & 2, ML System Design, GenAI System Design).
Only the well-known problem topics are used; all text here is original.

Each rubric lists the discussion points the Scoring Agent should expect from
a strong candidate.
"""

def _q(category: str, difficulty: str, title: str, prompt: str,
       constraints: list, expected: list) -> dict:
    return {
        "interview_type": "system_design", "category": category,
        "difficulty": difficulty, "title": title, "prompt": prompt,
        "examples": [], "constraints": constraints, "test_cases": [],
        "rubric": {"expected": expected},
    }


CLASSIC_QUESTIONS: list[dict] = [
    # ---------------- Vol 1 classics ----------------
    _q("sharding", "medium", "Design Consistent Hashing for a Cache Cluster",
       "Your service caches user sessions across a fleet of cache servers that scales "
       "up and down daily. Design the key-distribution scheme so that adding or removing "
       "a server moves as few keys as possible. Explain how requests find the right "
       "server and how you handle hot keys and uneven distribution.",
       ["cluster size changes daily", "minimize key remapping on membership change"],
       ["hash ring concept", "virtual nodes for balance", "remapping cost vs mod-N hashing",
        "hot key mitigation", "membership discovery", "replication across ring neighbors"]),

    _q("replication", "hard", "Design a Distributed Key-Value Store",
       "Design a distributed key-value store that serves get/put at low latency across "
       "multiple data centers. Cover partitioning, replication, consistency guarantees, "
       "failure detection, and how a read behaves during a network partition.",
       ["99.99% availability", "tunable consistency", "values up to 1 MB"],
       ["partitioning strategy", "leaderless vs leader replication", "quorum reads/writes (N,R,W)",
        "vector clocks / conflict resolution", "hinted handoff and read repair",
        "gossip failure detection", "CAP tradeoff articulation"]),

    _q("sharding", "medium", "Design a Distributed Unique ID Generator",
       "Services across many regions need 64-bit, roughly time-ordered unique IDs at "
       "high throughput without a single point of failure. Design the generator; discuss "
       "clock skew, machine-ID assignment, and what breaks if a server's clock jumps backwards.",
       ["10k+ IDs/sec per node", "IDs roughly sortable by time", "no central bottleneck"],
       ["snowflake-style bit layout", "timestamp/machine/sequence tradeoffs",
        "clock skew handling", "machine-ID assignment (ZooKeeper/config)",
        "alternatives: UUID, DB ticket server, and why they fall short"]),

    _q("caching", "easy", "Design a URL Shortener",
       "Design a service that turns long URLs into short links and redirects visitors. "
       "Cover short-code generation, storage, redirect latency, and analytics counting, "
       "plus how you prevent abuse.",
       ["100M new links/year", "redirect p99 < 50ms", "codes 7 chars or fewer"],
       ["base62 encoding vs hashing, collision handling", "read-heavy ratio and cache strategy",
        "301 vs 302 tradeoff for analytics", "DB schema and lookup path",
        "rate limiting / malicious link scanning", "capacity estimation"]),

    _q("message-queue", "medium", "Design a Web Crawler",
       "Design a crawler that continuously downloads billions of pages for a search index. "
       "Cover URL frontier design, politeness (per-host rate limits), deduplication of "
       "content and URLs, freshness, and trap avoidance.",
       ["1B pages/month", "respect robots.txt", "avoid crawling traps"],
       ["frontier queues with politeness + priority", "DNS caching", "content dedup (hashing/simhash)",
        "URL normalization and seen-set at scale", "distributed workers and partitioning by host",
        "freshness / recrawl scheduling"]),

    _q("message-queue", "medium", "Design a Notification System",
       "Design a system that sends push, SMS and email notifications triggered by product "
       "events. Cover fan-out, third-party provider integration, retries, rate limiting per "
       "user, preferences/opt-outs, and exactly-once user experience.",
       ["10M notifications/day", "no duplicate sends visible to users", "provider outages happen"],
       ["queue-based decoupling per channel", "idempotency keys against duplicates",
        "retry with backoff + DLQ", "user preference / do-not-disturb checks",
        "provider failover", "delivery tracking and observability"]),

    _q("caching", "medium", "Design a News Feed System",
       "Design the home feed for a social network: users follow others and see their posts "
       "ranked by recency. Cover fanout-on-write vs fanout-on-read, the celebrity problem, "
       "feed storage, and pagination.",
       ["300M users", "median follower count 200, max 100M", "feed p99 < 200ms"],
       ["push vs pull fanout tradeoffs", "hybrid approach for celebrities",
        "feed cache data model (per-user lists)", "pagination / cursor design",
        "write amplification estimation", "ranking hook without breaking latency"]),

    _q("api-design", "hard", "Design a Chat System",
       "Design a messaging service supporting 1:1 and group chats with online presence, "
       "typing indicators, and multi-device sync. Cover connection management, message "
       "ordering, delivery guarantees (sent/delivered/read), and offline delivery.",
       ["50M DAU", "messages must never be lost", "multi-device consistency"],
       ["WebSocket connection service + service discovery", "message ID ordering per channel",
        "ack ladder: sent/delivered/read", "inbox model and offline sync cursor",
        "group fan-out strategy", "presence via heartbeat", "storage choice for message history"]),

    _q("caching", "medium", "Design a Search Autocomplete System",
       "Design type-ahead suggestions: as the user types, return the top 10 most popular "
       "completions within tens of milliseconds. Cover the data structure, how popularity "
       "updates flow in, and how you keep p99 latency low at high QPS.",
       ["p99 < 100ms", "suggestions update daily (or faster)", "top-10 by frequency"],
       ["trie with precomputed top-k per node", "prefix sharding across servers",
        "offline aggregation pipeline for frequencies", "browser caching / debouncing",
        "storage size estimation", "filtering unsafe suggestions"]),

    _q("capacity-estimation", "hard", "Design a Video Streaming Platform",
       "Design a YouTube-like service: users upload videos that are transcoded and streamed "
       "worldwide. Cover the upload/transcoding pipeline, storage tiers, CDN strategy, "
       "and the metadata/serving path for watch pages.",
       ["500 hours uploaded per minute", "global audience", "adaptive bitrate playback"],
       ["transcoding as DAG of chunked jobs", "pre-signed upload and resumable uploads",
        "storage: blob store + CDN tiering, cost awareness", "DASH/HLS adaptive bitrate",
        "metadata DB scaling and caching", "capacity estimation for storage/bandwidth"]),

    _q("replication", "hard", "Design a Cloud File Storage & Sync Service",
       "Design a Google Drive-like service: files sync across a user's devices and can be "
       "shared. Cover chunking and deduplication, delta sync, conflict resolution when two "
       "devices edit offline, and metadata consistency.",
       ["files up to 10 GB", "sync latency a few seconds", "bandwidth-efficient updates"],
       ["file chunking + content-addressed dedup", "delta sync via chunk diffs",
        "metadata service with strong consistency", "offline edits and conflict copies",
        "notification/long-poll for change propagation", "sharing ACL model"]),

    # ---------------- Vol 2 classics ----------------
    _q("database-index", "medium", "Design a Proximity Service",
       "Design the backend for 'restaurants near me': given a location, return nearby "
       "businesses ranked by distance. Cover geospatial indexing options and how you "
       "scale reads for dense city centers.",
       ["100M businesses", "search radius 500m-20km", "read-heavy (100:1)"],
       ["geohash vs quadtree vs S2 comparison", "index sharding strategy",
        "cache hot regions", "precision vs radius tradeoffs at geohash boundaries",
        "business data update pipeline", "ranking beyond pure distance"]),

    _q("message-queue", "medium", "Design Nearby Friends",
       "Design a feature where opted-in friends see each other's live location within a "
       "few kilometers. Unlike static businesses, every user's location changes constantly. "
       "Cover location ingestion, pub/sub fan-out to friends, and privacy controls.",
       ["updates every 30s from active users", "end-to-end delay < 10s", "opt-in only"],
       ["WebSocket + pub/sub per user channel", "Redis TTL for ephemeral locations",
        "fan-out to friend subscribers only", "batching/throttling location updates",
        "privacy: opt-in, precision reduction, TTL expiry", "scale estimate for concurrent users"]),

    _q("capacity-estimation", "hard", "Design a Maps Service",
       "Design core Google-Maps-style functionality: map tile serving, geocoding, and "
       "turn-by-turn navigation with live ETA. Focus on the routing engine's data "
       "representation and how live traffic updates ETAs.",
       ["global road network", "route computation < 1s", "traffic-aware ETA"],
       ["road network as graph, hierarchical routing / contraction ideas",
        "map tiles: pre-rendered pyramid + CDN", "geocoding index",
        "live traffic ingestion from devices", "ETA recomputation and rerouting",
        "storage estimation for tiles and graph"]),

    _q("message-queue", "hard", "Design a Distributed Message Queue",
       "Design a Kafka-like distributed message queue: producers append, consumer groups "
       "read in order with offsets. Cover the storage engine, partitioning, replication "
       "and leader failover, and delivery semantics.",
       ["millions of msgs/sec", "configurable retention", "at-least-once minimum"],
       ["append-only segmented log + page cache", "partitions as ordering/parallelism unit",
        "consumer groups and offset management", "ISR replication and leader election",
        "at-least/at-most/exactly-once tradeoffs", "backpressure and retention policies"]),

    _q("capacity-estimation", "medium", "Design a Metrics Monitoring & Alerting System",
       "Design a system that collects metrics from 100k servers, stores them for querying "
       "and dashboards, and fires alerts on thresholds. Cover pull vs push collection, "
       "time-series storage, downsampling, and alert deduplication.",
       ["10M time series", "1-2 year retention with downsampling", "alert delay < 1min"],
       ["pull vs push tradeoffs", "time-series DB: encoding, compaction, cold storage",
        "downsampling/rollup tiers", "alert rule evaluation and dedup/silencing",
        "cardinality explosion risks", "query path for dashboards"]),

    _q("kafka", "hard", "Design an Ad Click Event Aggregation System",
       "Design the pipeline that counts ad clicks and returns per-ad aggregates over the "
       "last M minutes, used for billing. Cover exactly-once aggregation, late/duplicate "
       "events, windowing, and reconciliation against the raw log.",
       ["1B clicks/day", "billing-grade correctness", "top-100 ads query in real time"],
       ["stream processing with windowed aggregation", "event-time vs processing-time + watermarks",
        "dedup via event IDs", "exactly-once sinks / idempotent upserts",
        "lambda-style reconciliation with batch recount", "hot ad key skew handling"]),

    _q("transactions", "medium", "Design a Hotel Reservation System",
       "Design booking for a hotel chain: browse rooms, hold, pay, confirm — without "
       "double-booking under concurrency. Cover the inventory model, race handling, "
       "and how overbooking policies would be implemented safely.",
       ["5k hotels, 1M rooms", "no double-booking", "peak flash-sale traffic"],
       ["inventory as date x room-type counts, not per-room rows",
        "optimistic vs pessimistic locking comparison", "hold with TTL then confirm",
        "idempotent booking API", "payment integration in the state machine",
        "cache consistency for availability search"]),

    _q("replication", "hard", "Design a Distributed Email Service",
       "Design a Gmail-scale email service: receiving/sending via SMTP, mailbox storage, "
       "search, and spam filtering. Focus on the mailbox storage model and how search "
       "over decades of mail stays fast.",
       ["1B users", "50 GB mailbox cap", "search p99 < 500ms"],
       ["SMTP ingress pipeline with queueing", "mailbox metadata vs blob body separation",
        "per-user search index design", "spam/phishing filtering stage",
        "storage replication and legal retention", "conversation threading model"]),

    _q("replication", "hard", "Design S3-like Object Storage",
       "Design an object store with buckets, objects, versioning and 11-nines durability. "
       "Cover the data path (how bytes land on disk), metadata service, erasure coding vs "
       "replication, and how you verify integrity over years.",
       ["exabyte scale", "11 nines durability", "objects bytes to 5 TB"],
       ["separation of metadata and data planes", "placement groups and durability math",
        "erasure coding vs 3x replication cost/latency", "multipart upload",
        "background scrubbing / bit-rot repair", "consistency model for overwrite/list"]),

    _q("caching", "medium", "Design a Real-time Gaming Leaderboard",
       "Design a leaderboard for a game with millions of players: update scores in real "
       "time, show top-10 and each player's exact rank with neighbors. Discuss why a "
       "relational approach struggles and what you'd use instead.",
       ["25M DAU", "rank query < 50ms", "monthly reset with history"],
       ["Redis sorted set core operations", "why SQL rank queries don't scale",
        "sharding sorted sets and merging top-k", "approximate rank at long tail",
        "persistence/rebuild strategy", "anti-cheat validation before write"]),

    _q("idempotency", "hard", "Design a Payment System",
       "Design the payment flow for an e-commerce checkout that charges cards via an "
       "external PSP. Money must never be lost or double-charged. Cover the payment state "
       "machine, idempotency end-to-end, webhook handling, and reconciliation.",
       ["integrates external PSP", "exactly-once money movement", "PSP can be slow/down"],
       ["payment state machine with persisted transitions", "idempotency keys at every hop",
        "async webhooks + polling fallback", "retry with same key, never blind retry",
        "double-entry ledger recording", "daily reconciliation against PSP reports"]),

    _q("transactions", "hard", "Design a Digital Wallet",
       "Design in-app wallet balances supporting transfers between users at high "
       "throughput. A transfer must debit one account and credit another atomically — "
       "across partitions. Compare distributed transaction options and justify one.",
       ["1M TPS target", "no negative balances", "auditable history"],
       ["why single-DB transactions stop scaling", "2PC vs TCC vs saga comparison",
        "event-sourced ledger + reproducible state", "partitioning accounts and hot accounts",
        "exactly-once via idempotent commands", "audit/replay capability"]),

    _q("consistency", "hard", "Design a Stock Exchange",
       "Design a limit-order exchange: order entry, matching engine, market data fan-out. "
       "Focus on the matching engine's data structures, deterministic sequencing, "
       "microsecond-level latency thinking, and fault tolerance without losing orders.",
       ["100k orders/sec", "matching latency in microseconds", "orders never lost"],
       ["order book structures (price levels + FIFO queues)", "single-threaded deterministic matching",
        "sequencer + event sourcing for recovery", "hot-warm failover with replay",
        "market data multicast/fan-out", "risk checks pre-trade", "why general DBs are too slow"]),

    # ---------------- ML system design classics ----------------
    _q("embeddings", "medium", "Design a Visual Search System",
       "Design 'search by image' for an e-commerce app: a user photographs an item and "
       "gets visually similar products. Cover embedding model choice, the vector index, "
       "and how you evaluate and retrain the system.",
       ["100M product images", "results < 500ms", "catalog updates daily"],
       ["image embedding model + contrastive training idea", "ANN index (HNSW/IVF) tradeoffs",
        "offline vs online embedding computation", "evaluation: recall@k, human ratings",
        "handling new products (index refresh)", "serving architecture and caching"]),

    _q("neural-networks", "medium", "Design a Street-Image Face & Plate Blurring System",
       "Design the offline pipeline that detects and blurs faces and license plates in "
       "billions of street-level photos before publication. Cover model choice, precision/"
       "recall tradeoffs given privacy stakes, and the human-review loop.",
       ["10B images backlog + daily increments", "privacy demands very high recall", "batch, not realtime"],
       ["object detection model choice and training data", "recall-first threshold tuning",
        "hard-negative mining loop", "batch inference pipeline design and cost",
        "human review sampling for QA", "metrics: recall/precision per class, drift monitoring"]),

    _q("embeddings", "medium", "Design Video Search Ranking",
       "Design search over a huge video corpus: given a text query, return relevant videos "
       "using both text metadata and visual content. Cover the two-tower retrieval + "
       "ranking split and how you train with noisy click data.",
       ["1B videos", "query p99 < 300ms", "clicks as weak labels"],
       ["retrieval/ranking two-stage architecture", "two-tower text/video embedding model",
        "training with click data and its biases", "ANN retrieval + feature-rich ranker",
        "offline metrics (recall@k, nDCG) vs online A/B", "freshness for new videos"]),

    _q("supervised-learning", "medium", "Design a Harmful Content Detection System",
       "Design the ML system that flags policy-violating posts (violence, hate, spam) on "
       "a social platform. Cover multi-label modeling, class imbalance, the human "
       "moderation loop, and adversarial users who adapt to your model.",
       ["10M posts/day", "multiple violation types", "appeals must be supported"],
       ["multi-label vs per-class binary models", "handling extreme class imbalance",
        "threshold tiers: auto-remove vs human review", "feedback loop from moderator decisions",
        "adversarial adaptation and periodic retraining", "metrics: per-class PR, prevalence"]),

    _q("recommendation-systems", "hard", "Design a Video Recommendation System",
       "Design the homepage video recommender: from a billion-scale corpus, pick the "
       "handful each user sees. Cover candidate generation, ranking objectives beyond "
       "clicks (watch time, satisfaction), exploration, and feedback loops.",
       ["1B videos, 2B users", "response < 200ms", "avoid clickbait optimization"],
       ["candidate generation (two-tower, collaborative signals)", "ranking model and multi-objective labels",
        "position bias correction", "exploration vs exploitation",
        "filter bubbles / feedback loop mitigation", "online metrics beyond CTR"]),

    _q("recommendation-systems", "medium", "Design an Event Recommendation System",
       "Design recommendations for a local-events platform. Events expire quickly and "
       "have no interaction history when created — a perpetual cold-start problem. Cover "
       "content features, location constraints, and ranking with sparse feedback.",
       ["events live days not years", "location-bounded relevance", "sparse labels"],
       ["cold-start via content + creator features", "location/time hard filters then ranking",
        "hybrid content + collaborative approach", "training data construction from RSVPs",
        "evaluation with limited feedback", "freshness-aware index updates"]),

    _q("feature-engineering", "hard", "Design an Ad Click Prediction System",
       "Design pCTR prediction for a social ads system: billions of daily impressions, "
       "money directly tied to calibration. Cover feature pipelines, model architecture, "
       "calibration, and continual/online learning as trends shift within hours.",
       ["5B impressions/day", "well-calibrated probabilities required", "distribution shifts hourly"],
       ["feature families: user/ad/context, hashing high-cardinality ids",
        "model evolution: LR -> deep + embeddings", "calibration and why it matters for auctions",
        "online/continual learning and delayed labels", "training/serving skew prevention",
        "metrics: log loss, calibration curves, revenue A/B"]),

    _q("embeddings", "medium", "Design Similar-Listing Recommendations",
       "Design 'similar homes' for a vacation-rental platform: on a listing page, show "
       "alternatives a guest would also consider. Cover embedding listings from user "
       "browsing sessions, and blending similarity with availability and price fit.",
       ["7M listings", "shown on every listing page", "must respect dates/party size"],
       ["session-based listing embeddings (co-view/skip signals)",
        "hard constraints filter before similarity", "blending similarity with quality/price",
        "cold-start listings via content features", "offline metrics + interleaving tests"]),

    _q("recommendation-systems", "hard", "Design a Personalized News Feed Ranker",
       "Design the ML ranking layer for a social feed: order hundreds of candidate posts "
       "per refresh, balancing engagement with integrity and diversity. Cover multi-task "
       "modeling, value-model aggregation of predictions, and re-ranking rules.",
       ["p99 ranking budget 150ms", "multiple engagement signals", "diversity constraints"],
       ["multi-task model predicting several actions", "value model combining predictions",
        "feature logging and training pipeline", "diversity/author-repeat re-ranking",
        "counterfactual evaluation limits, A/B design", "integrity demotions in ranking"]),

    _q("recommendation-systems", "medium", "Design People You May Know",
       "Design friend suggestions for a social network. The core signal is graph "
       "structure (mutual friends), but scale makes second-degree computation expensive. "
       "Cover graph features, embedding approaches, and precomputation vs online serving.",
       ["1B users, avg 500 connections", "suggestions refresh daily", "privacy constraints"],
       ["friends-of-friends generation and its cost", "graph features (mutual count, affinity)",
        "graph embeddings as complement", "offline precompute + delta updates",
        "ranking model on candidate pairs", "privacy filters and dismissed-suggestion memory"]),

    # ---------------- GenAI system design classics ----------------
    _q("transformers", "medium", "Design an Email Smart-Compose Feature",
       "Design inline sentence completion for an email client: as the user types, suggest "
       "the next few words within ~100ms. Cover model size/latency tradeoffs, on-device vs "
       "server inference, triggering policy, and privacy of training data.",
       ["p95 < 100ms end-to-end", "suggestion acceptance is the key metric", "private user text"],
       ["small autoregressive model, latency budget math", "when to trigger and when to stay silent",
        "beam vs greedy for short spans", "personalization signals",
        "training on user data: privacy/anonymization", "metrics: acceptance rate, saved keystrokes"]),

    _q("transformers", "medium", "Design a Machine Translation Service",
       "Design a Google-Translate-style service for 100+ languages including low-resource "
       "pairs. Cover multilingual model strategy, back-translation for data scarcity, "
       "serving cost at scale, and quality evaluation beyond BLEU.",
       ["100+ languages", "latency < 500ms for a paragraph", "low-resource pairs matter"],
       ["multilingual encoder-decoder vs per-pair models", "back-translation and pivoting",
        "tokenization across scripts", "batching/quantization for serving cost",
        "evaluation: BLEU/COMET + human eval", "handling named entities and formatting"]),

    _q("llm-serving", "hard", "Design a Personal Assistant Chatbot Platform",
       "Design a ChatGPT-style assistant serving millions of concurrent conversations. "
       "Cover the inference serving stack (batching, KV cache, streaming), conversation "
       "state, safety filtering, and cost/latency optimization.",
       ["10M DAU", "first token < 1s, streaming after", "GPU cost is the dominant expense"],
       ["continuous batching and KV-cache memory math", "streaming token delivery (SSE/WebSocket)",
        "context window management and summarization", "safety: input/output filtering layers",
        "model routing (small model first)", "multi-region GPU capacity and queueing",
        "metrics: TTFT, tokens/sec, cost per conversation"]),

    _q("neural-networks", "medium", "Design an Image Captioning System",
       "Design a system that generates alt-text captions for every image uploaded to a "
       "social platform, for accessibility. Cover vision-language model architecture, "
       "hallucination control given screen-reader users depend on accuracy, and batch "
       "vs realtime serving.",
       ["500M images/day", "captions must not hallucinate", "multiple languages"],
       ["vision encoder + language decoder architecture", "training data pairs and quality filtering",
        "hallucination mitigation: confidence, object grounding", "batch pipeline vs on-demand",
        "evaluation: CIDEr/human eval, per-language QA", "fallback taxonomy when uncertain"]),

    _q("rag-systems", "medium", "Design an Enterprise RAG Question-Answering System",
       "Design a retrieval-augmented assistant that answers employee questions over "
       "internal wikis, tickets and docs. Cover chunking and indexing, hybrid retrieval, "
       "permission-aware answers, grounding/citations, and evaluation.",
       ["10M documents with ACLs", "answers must cite sources", "docs update continuously"],
       ["chunking strategy and metadata", "hybrid dense+keyword retrieval, reranking",
        "ACL enforcement at retrieval time, not generation", "grounded generation with citations",
        "hallucination evaluation: faithfulness metrics", "index freshness pipeline",
        "feedback loop from thumbs-down"]),

    _q("neural-networks", "hard", "Design a Realistic Face Generation System",
       "Design a system that generates realistic, diverse, non-existent human faces for "
       "use as avatars. Compare GAN and diffusion approaches, cover training stability, "
       "diversity and bias measurement, and misuse prevention.",
       ["photorealistic 1024x1024 output", "must not reproduce training identities", "abuse potential is high"],
       ["GAN vs diffusion tradeoffs", "training stability techniques",
        "memorization/identity-leak testing", "diversity and demographic bias evaluation",
        "watermarking and provenance", "abuse policy: deepfake mitigations"]),

    _q("training-optimization", "hard", "Design a High-Resolution Image Synthesis Pipeline",
       "Design the training and serving pipeline for a diffusion model producing "
       "high-resolution images. Direct pixel-space diffusion at 1024px is too expensive — "
       "cover latent diffusion, super-resolution stages, sampler steps vs quality, and "
       "GPU serving economics.",
       ["1024px outputs", "generation < 10s", "training on billions of images"],
       ["latent diffusion rationale (VAE compression)", "cascaded/super-resolution stages",
        "sampler choice and step-count distillation", "large-scale training: data curation, sharded training",
        "serving: batching, fp16/int8, cost per image", "quality metrics: FID + human preference"]),

    _q("embeddings", "hard", "Design a Text-to-Image Generation Service",
       "Design a Midjourney-style product: text prompt in, images out, at consumer scale. "
       "Cover text-image alignment (why CLIP-style guidance matters), prompt handling, "
       "safety filtering on both prompt and output, and queueing under GPU scarcity.",
       ["1M images/day", "p50 < 15s", "strict content policy"],
       ["text encoder conditioning and guidance scale", "prompt preprocessing/expansion",
        "two-sided safety: prompt classifier + output classifier", "GPU queue with priority tiers",
        "caching/dedup of similar prompts", "alignment evaluation: CLIP score + human ranking"]),

    _q("llm-fine-tuning", "medium", "Design a Personalized Headshot Generator",
       "Design a feature where a user uploads ~15 selfies and receives professional-style "
       "headshots. Per-user fine-tuning at scale is the core challenge. Compare full "
       "fine-tuning, LoRA, and encoder-based personalization; cover identity preservation.",
       ["10k users/day", "per-user turnaround < 30min", "identity must be preserved"],
       ["per-user LoRA vs full fine-tune cost math", "encoder-based zero-shot alternatives",
        "identity preservation evaluation (face-sim metrics)", "training job orchestration per user",
        "user-data retention/deletion policy", "GPU fleet scheduling and cost"]),

    _q("training-optimization", "hard", "Design a Text-to-Video Generation System",
       "Design a short-video generation service from text prompts. Video adds temporal "
       "consistency and an order-of-magnitude compute jump over images. Cover model "
       "architecture choices, temporal coherence, training data pipelines, and serving "
       "long-running jobs.",
       ["clips 5-15s", "temporal consistency across frames", "minutes-long generation acceptable"],
       ["spatio-temporal architecture over image backbone", "temporal attention/consistency techniques",
        "video-text training data curation at scale", "async job design: queue, progress, notifications",
        "compute estimation and cascaded generation", "evaluation: frame quality + motion + human eval"]),
]
