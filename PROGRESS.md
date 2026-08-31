# AURORA TRACE Progress

This file records completed work only. Planned work is explicitly marked as planned and is not evidence of implementation.

## Repository history at the upgrade start

The repository already contained a complete initial snapshot. It must not be described as a from-zero staged history.

```text
26e860d docs: correct repository status in log
85aaf82 docs: record reproducible development plan
412efff 建立 AURORA TRACE 初始版本
```

## Current implementation status

| Area | Status | Evidence |
| --- | --- | --- |
| Tool Registry and ToolSpec | implemented | `aurora.py`, Registry tests |
| Structured tool errors | implemented | 15-test suite |
| Causal event fields | implemented | `parent_event_id`, `phase`, `evidence_type` |
| Adaptive Acceptance Contract | implemented | repair/feature/refactor/change baseline policies |
| Run persistence | implemented | atomic `run.json` snapshots |
| Evidence Ledger persistence | implemented | `evidence.ndjson` |
| Run history API | implemented | `GET /api/runs` |
| Trace export | implemented | `GET /api/run/<id>/export` |
| UTF-8 evidence console | implemented | `web/console.*` served at `/` |
| Read-only event Replay | implemented | console Replay view |
| Live provider integration | implemented, requires configuration | OpenAI-compatible endpoint |
| Evidence-aware Context Budget | implemented | deterministic old-content compaction with role preservation |
| Approval Gate | runtime implemented | auto/manual policy, pending tool arguments and approve/reject API |
| Cooperative cancellation | runtime implemented | approval wake-up, long-command interruption and `CANCELLED` state |
| Subagents / Plugins / MCP | planned | not claimed by current version |

## Verification record

The upgrade was verified with:

```text
python -m unittest discover -s tests -v  →  34 tests passed
python -m py_compile aurora.py          →  passed
node --check web/app.js                 →  passed
node --check web/console.js             →  passed
```

A real Mock end-to-end Run also reached `COMPLETED` with:

- 21 events;
- one non-empty Diff;
- Evidence Score 100;
- four evidence gates true;
- persisted `run.json` and `evidence.ndjson`.

The Mock fixture boundary is explicit: it accepts the built-in repair contract only; mismatched feature/refactor/change requests are rejected before workspace creation.

The generated Run ID and timestamps are intentionally not fixed in this document.

## Next honest increments

1. Add API-level tests for project import, Run history, Approval Gate and Trace export.
2. Add a second seeded bug fixture only if it supports a clearly different evidence story.
3. Extract the stable logical layers from `aurora.py` only when the extracted module has independent tests and a clear defense explanation.
