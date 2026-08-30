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
| Acceptance completion gate | implemented | early finish is blocked |
| Run persistence | implemented | atomic `run.json` snapshots |
| Evidence Ledger persistence | implemented | `evidence.ndjson` |
| Run history API | implemented | `GET /api/runs` |
| Trace export | implemented | `GET /api/run/<id>/export` |
| UTF-8 evidence console | implemented | `web/console.*` served at `/` |
| Read-only event Replay | implemented | console Replay view |
| Live provider integration | implemented, requires configuration | OpenAI-compatible endpoint |
| Context compaction | planned | not claimed by current version |
| Subagents / Plugins / MCP | planned | not claimed by current version |

## Verification record

The upgrade was verified with:

```text
python -m unittest discover -s tests -v  →  20 tests passed
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

The generated Run ID and timestamps are intentionally not fixed in this document.

## Next honest increments

1. Add a task-typed contract for projects whose correct baseline is already green.
2. Add two distinct seeded bug fixtures and compare traces across tasks.
3. Add API-level tests for project import, Run history and Trace export.
4. Extract the stable logical layers from `aurora.py` only when the extracted module has independent tests and a clear defense explanation.
