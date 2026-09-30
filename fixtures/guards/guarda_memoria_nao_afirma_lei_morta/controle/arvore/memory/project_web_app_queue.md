---
id: 4
name: project_web_app_queue
description: The web app worker queue: retry cap, dead-letter queue, and where its numbers live
type: project
---
The queue retries a job three times and then parks it in the dead-letter queue.

**Why:** retrying forever hid a poison message behind a busy worker.

**How to apply:** check the dead-letter count before blaming the worker.
