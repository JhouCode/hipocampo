---
id: 6
name: project_web_app_rate_limit
description: The web app rate limit: where it is enforced and why not in the app
type: project
---
Uploads above the limit are refused at the edge.

**Why:** the app never buffers what it will refuse.

**How to apply:** change the edge config, not the app, when the limit moves.
