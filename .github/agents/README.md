# AION specialist agent profiles

These profiles define reusable specialist instructions for GitHub Copilot's custom-agent workflow. They are role definitions, not proof that independent background processes are already running. They can be selected in supported Copilot agent experiences; repository CI remains the source of truth for test results.

## Roles
- **AION Coordinator** — plans and coordinates work; requires evidence before closure.
- **AION Diagnostics** — investigates CI/logs/artifacts and identifies root causes.
- **AION Physics** — owns simulation, movement, collision, and long-run regression.
- **AION Browser QA** — owns browser lifecycle, visual, and interaction validation.
- **AION Independent Reviewer** — reviews changes and evidence independently.

## Suggested operating cycle
1. Diagnostics collects the failed run, job logs, reports, screenshots, and reproduction.
2. Coordinator creates a bounded implementation task.
3. The relevant specialist makes the smallest change and adds a regression test.
4. Browser QA and physics QA run independently where relevant.
5. Independent Reviewer checks the diff and checks the exact tested commit.
6. Coordinator publishes the result with links and any unresolved risks.

## AION safety contract
- Work on `aion/long-run-agent-physics-regression` unless explicitly authorized otherwise.
- Test against `aion-server-test` only.
- Never deploy production.
- PostgreSQL remains protected.
- Never run BIG_BANG.
- Never merge PR #6.
- Never claim a test passed without a completed run with a successful conclusion.
- Never suppress a real failure simply to make CI green.

## Existing validation workflows
- [AION QA](../workflows/aion-qa.yml) runs deterministic physics, a 120-second isolated simulation regression, and browser movement/collision tests.
- [AION Visual QA](../workflows/aion-visual-qa.yml) validates client JavaScript syntax and runs the browser visual smoke test.

Workflow reports and screenshots are stored as GitHub Actions artifacts. See [GitHub's artifact documentation](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts).
