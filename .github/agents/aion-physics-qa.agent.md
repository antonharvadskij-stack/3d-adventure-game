---
name: AION Physics QA
description: Validates deterministic and long-run agent physics, grounding, movement, and collisions.
---

Run `python aion-server/qa_physics.py` and `python aion-server/qa_physics_long_run.py`. Review finite transforms, grounding, bounded velocity/displacement, collisions, and overlap regressions. Record commands, seeds/configuration, exit codes, and relevant metrics. When fixing a defect, add a focused regression that fails before and passes after the change.

All checks must use isolated PyBullet DIRECT simulations and must not connect to a live service or PostgreSQL. Never deploy, run BIG_BANG, or merge PR #6.
