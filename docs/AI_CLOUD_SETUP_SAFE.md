# AION Cloud AI Development Setup (Safe / Cost-Minimizing)

Status: documentation-only setup plan. This file does not deploy, run migrations, change database state, or modify production configuration.

## Hard safety gates

- Production: `DO_NOT_DEPLOY`. Do not publish/deploy production builds from this workflow.
- PostgreSQL: `PROTECTED`. Read-only access only unless a separate explicit approval authorizes a specific change.
- `BIG_BANG=DO_NOT_RUN`.
- `PR6=DO_NOT_MERGE`.
- Never expose API keys, tokens, database URLs, or other secrets in commits, logs, prompts, screenshots, or artifacts.
- Work only on feature branches. Review diffs and CI results before opening a PR. Do not merge automatically.
- Preserve existing project files and deployment settings. Do not run destructive scripts or database migrations.

## Recommended cloud workflow

### 1. Codex Cloud (primary no-local-machine workflow)

1. Open ChatGPT and navigate to Codex.
2. Connect the GitHub repository `antonharvadskij-stack/3d-adventure-game` only if it is not already connected.
3. Create a cloud environment for this repository; review its setup/install commands before publishing the environment.
4. Keep environment visibility restricted to the owner.
5. Grant the minimum repository and network access needed. Start with no extra network domains; add only verified package registries or documentation hosts when necessary.
6. Do not add production credentials, PostgreSQL credentials, deploy tokens, or cloud-provider secrets.
7. Start tasks with explicit read-only or branch-scoped instructions. Review the diff and test output before accepting any commit or PR.

Suggested first task:
> Read-only audit only. Inspect project structure, scripts, CI workflows, and recent QA state. Do not edit files, run deployments, change PostgreSQL, run migrations, trigger destructive workflows, merge PRs, or modify production settings. Report setup commands and safe tests, identifying any missing dependencies.

### 2. Claude Code (secondary agent)

Claude Code is a separate product and may require an eligible subscription or billed API access. Do not assume that a free third-party model API is compatible with Claude Code or that it makes Claude Code itself free.

- Use the official Claude Code sign-in flow and verify the selected authentication method with `/status`.
- Leave `ANTHROPIC_API_KEY` unset when intending to use an included Claude subscription allowance; environment API keys can route usage to billable API access.
- Before any API-backed session, confirm the provider, rate limits, and billing controls.
- Use a separate feature branch for changes; do not let both agents write to the same branch concurrently.
- Prefer read-only audit/planning first, then small, isolated changes.

Official setup: https://docs.anthropic.com/en/docs/claude-code/getting-started

### 3. Switching between agents safely

- Use Codex Cloud for isolated cloud tasks and review.
- Use Claude Code for a second opinion or focused changes when access is available.
- Only one agent should write to a given branch at a time.
- Before switching, record the branch, commit SHA, changed files, tests run, and unresolved blockers.
- Keep changes in separate branches and compare diffs; never allow automatic merge or production deploy.

### 4. Cost controls

- Start with included plan allowances and explicitly free tiers only.
- Do not enter payment details or enable pay-as-you-go solely to bypass a limit without deliberate approval.
- Avoid long agent sessions; give a narrow task, list the files in scope, and ask for a concise report.
- Check the provider's current quota/pricing page before enabling API usage. Free tiers and model availability can change.
- Do not use API keys found in public repositories or shared by unknown parties.

### 5. Safe validation sequence

1. Inspect repository scripts and CI workflows without executing them.
2. Identify static checks and unit tests that do not access production services.
3. Run only isolated checks in the cloud environment after reviewing their commands.
4. Confirm browser tests and required assets are available; report blocked external resources as blockers rather than weakening checks.
5. Save logs/artifacts without secrets.
6. Review the diff and test report. Stop before merge, deployment, migrations, or database writes.

## AION QA handoff template

```text
AION::CLOUD_AI_HANDOFF
repo=antonharvadskij-stack/3d-adventure-game
branch=<current-feature-branch>
commit=<full-commit-sha>
mode=READ_ONLY_UNTIL_APPROVED
production=DO_NOT_DEPLOY
postgres=PROTECTED
BIG_BANG=DO_NOT_RUN
PR6=DO_NOT_MERGE
changed_files=<list>
checks_run=<list>
checks_passed=<list>
checks_blocked=<list>
secrets_exposed=NO
deployment_performed=NO
database_writes=NO
next_safe_step=<one narrow step>
```

## Not yet configured

This repository file documents the safe setup; it does not itself create or publish a Codex Cloud environment, authenticate Claude Code, configure billing, or run tests. Those actions must be completed and verified in the relevant product UI.
