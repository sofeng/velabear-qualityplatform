---
name: testhub-self-debug-repair
description: TestHub platform self-debugging and self-repair workflow for local Docker Desktop testhub-local-* services, local Playwright Agent, visual flow recording, continued recording, iframe-aware component placement, generated Playwright scripts, local replay, and execution result validation. Use when Codex must reproduce a TestHub recording/replay issue, patch the platform, sync local containers, and prove the fix with a real end-to-end browser chain.
---

# TestHub Self Debug Repair

## Core Workflow

Use this skill when the task is not only to change code, but to prove the TestHub platform behavior end to end.

1. Reproduce the issue with the real platform flow before changing code.
2. Capture concrete evidence: flow id, recording session id, execution id, failing step, generated script, screenshot, stderr, and execution records.
3. Diagnose from the narrowest failing boundary first: generated script, local Agent response, backend execution API, graph data, then UI state.
4. Patch the smallest responsible module. Do not rewrite unrelated flow/editor logic.
5. Sync the changed service into the local Docker container.
6. Repeat the same real user chain until it passes.
7. For visual flow work, verify normal replay, tail continued recording, middle-node continued recording, and branched replay.

## Local TestHub Environment

Prefer the frontend reverse proxy unless direct backend access is proven working:

```powershell
$Frontend = "http://localhost:31080"
$Api = "http://localhost:31080/api"
$Agent = "http://127.0.0.1:18765"
```

Common local services:

```powershell
docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "testhub-local-"
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:18765/health
```

Common sync commands:

```powershell
npm --prefix frontend run build
docker cp frontend/dist/. testhub-local-frontend:/usr/share/nginx/html/
docker cp apps/testcases/views.py testhub-local-backend:/app/apps/testcases/views.py
docker restart testhub-local-backend
```

Restart the local Playwright Agent after changing Agent code:

```powershell
tools/stop_local_playwright_agent.ps1
tools/start_local_playwright_agent.ps1
```

For Django tests against local Docker MySQL, prefer root when the app user lacks test DB permissions:

```powershell
$env:DB_HOST='127.0.0.1'; $env:DB_PORT='13306'; $env:DB_USER='root'; $env:DB_PASSWORD='root123'; $env:DB_NAME='testhub'
python manage.py test <test-path> --keepdb
```

## Visual Flow Checks

When debugging recording, real-time graph generation, continued recording, or replay:

- Confirm junk steps are filtered before `innerComponents` are generated.
- Confirm repeated typing becomes one input component rather than duplicate components.
- Confirm no-op container/blank clicks are ignored unless they are command buttons.
- Confirm iframe steps stay inside the iframe component and do not fall back to main-page locators.
- Confirm page nodes represent system pages, not every snapshot.
- Confirm continued recording appends from the selected node/component without clearing the existing graph.
- Confirm a middle-component continuation can create a second branch.
- Confirm replay traverses every branch and records per-step execution results.

## Script Generation Rules

Generated Playwright scripts must prefer recorded precise locators and scoped fallbacks:

- Wait for a candidate locator to be visible before falling back.
- Do not fall back from an iframe component to whole-page text search.
- For buttons and generic clicks, pass the current scope to helper functions.
- Treat screenshots and execution step logs as the source of truth for whether a click actually changed the page.
- If a step reports success but the browser state did not change, fix the locator strategy rather than adding sleeps blindly.

## Verification Pattern

For a real browser validation chain:

1. Log in to TestHub as a platform user.
2. Open the target visual flow or create it from a recording.
3. Generate or run the local replay through the local Agent.
4. Check the execution record summary: `status`, `step_count`, `success_count`, `failed_count`, `stderr`.
5. If failed, download or inspect the failing step screenshot and generated script section.
6. Fix and sync.
7. Replay again.
8. Continue recording from the tail component and stop recording.
9. Continue recording from a middle component and stop recording.
10. Replay again and verify all branches succeed.

Keep temporary scripts in repo-root `.tmp-*` files when useful, and do not commit or rely on secrets in those files. Use environment variables for external system passwords.

## Reporting

End with the evidence that matters:

- Changed files and why.
- Container sync status.
- Flow id, recording session id, execution id.
- Replay summary, including branch count when available.
- Any residual risk or skipped validation.
