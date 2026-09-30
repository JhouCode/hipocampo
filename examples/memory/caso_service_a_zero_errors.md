---
name: caso_service_a_zero_errors
id: 1
description: "service-a error dashboard read 0 errors for a week because the log filter matched no lines at all after a log-format change"
metadata:
  node_type: memory
  type: project
  escopo: web
  regra: feedback_count_population_before_zero
---
The error panel of service-a showed 0 errors for seven days after a deploy. The deploy had
changed the log line prefix, and the panel's filter matched on the old prefix: it was counting
errors over zero lines.

Found when someone asked "0 out of how many?" and the line count for the window came back 0
while the service was plainly serving traffic.

Rule this case proves: [[feedback_count_population_before_zero]]

**Why:** kept as the concrete evidence for the rule; if this case is revoked, the rule's
`prova:` count has to change with it.

**How to apply:** when a dashboard reports a clean zero after a deploy, check the denominator
of the same window first.
