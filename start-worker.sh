OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES uv run rq worker --url redis://localhost:6379/0 scraper ingest notification
