---
id: 5
name: reference_migration_checklist
description: Checklist for a schema change, PENDING approval by the owner
type: reference
---
1. write the up migration. 2. write the down migration. 3. run both on a copy.

**Why:** a migration that cannot be undone is a one-way door.

**How to apply:** use this list before opening a change that touches the schema.
