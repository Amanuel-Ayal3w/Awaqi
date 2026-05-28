"""RQ queue definitions.

Three queues:
  - ``scraper``       — MoR web scraping + Telegram channel scraping (long-running, 1-h timeout)
  - ``ingest``        — single-document ingestion after upload (shorter, 30-min timeout)
  - ``notification``  — proactive email/SMS notification checks (1-h timeout)
"""

from __future__ import annotations

from rq import Queue

from apps.api.queue.connection import sync_redis

scraper_queue: Queue = Queue("scraper", connection=sync_redis, default_timeout=3600)
ingest_queue: Queue = Queue("ingest", connection=sync_redis, default_timeout=1800)
notification_queue: Queue = Queue("notification", connection=sync_redis, default_timeout=3600)
