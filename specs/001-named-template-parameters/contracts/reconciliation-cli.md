# Contract — Reconciliation command and report artifact

**Direction**: operator → this service (no HTTP surface)
**Command**: `marketplace/wpp_templates/management/commands/reconcile_template_parameters.py`
**Use case**: `TemplateParameterReconciliationUseCase`

Operator-triggered by design (FR-030): it cannot run unannounced in production, and it introduces no
persisted model, no read endpoint and no permission.

---

## Invocation

```bash
python manage.py reconcile_template_parameters [options]
```

| Option | Type | Default | Purpose |
| --- | --- | --- | --- |
| `--waba-id` | repeatable string | all eligible WABAs | Restrict to specific WABAs |
| `--app-uuid` | repeatable UUID | — | Restrict to specific apps; resolved to their WABAs |
| `--limit` | int | none | Stop after N WABAs. For a bounded first run |
| `--dry-run` | flag | off | Classify and report without writing to the mirror |
| `--restart` | flag | off | Discard stored progress and start over. Without it, a run resumes |
| `--output` | path | `reconciliation-<run_id>.csv` in the working directory | Where the artifact is written |
| `--budget` | int | `settings.META_SYNC_TEMPLATES_DRAIN_BUDGET` (30) | WABAs per minute |

### Examples

```bash
# Bounded first run to size the problem before touching the fleet
python manage.py reconcile_template_parameters --limit 20 --dry-run --output /tmp/probe.csv

# Full fleet run
python manage.py reconcile_template_parameters --output /tmp/reconciliation-2026-09-17.csv

# Resume after an interruption (default behaviour — no flag needed)
python manage.py reconcile_template_parameters --output /tmp/reconciliation-2026-09-17.csv

# One account
python manage.py reconcile_template_parameters --waba-id 102290129340398
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Run completed; the artifact was written. A non-zero count of unclassifiable rows is **not** a failure — it is a finding the report records |
| `1` | The run could not start or could not write the artifact (bad arguments, unreachable Redis, unwritable output path) |

---

## Execution

```
resolve target WABAs  (reuses tasks._apps_for_waba, which excludes ignores_meta_sync apps)
        │
        ├── an app excluded by ignores_meta_sync → reported as `unclassifiable`
        │    with reason `sync_disabled`, never counted as classified (Edge Cases)
        ▼
load progress from Redis  (unless --restart)
        │
        ▼
for each WABA not already in progress.done_waba_ids:
        │
        ├── per-WABA TTL lock held by a recent scheduled sync?
        │      → skip the WABA; do **not** append it to done_waba_ids;
        │        increment run counter `skipped_recent_sync`; emit no translation rows
        │        (this is a WABA-level skip, not a sixth translation category)
        │
        ├── snapshot pre-state for every translation of every app on this WABA:
        │      (body, parameter_format, body_named_params, variable_count)
        │
        ├── GET Meta's template list once for the WABA
        │      └── error / invalid token / WABA gone → every translation reported
        │          `unclassifiable` with the reason; the run continues
        │
        ├── apply via TemplateSyncUseCase(app).sync_templates(templates=...) for each app
        │      (skipped when --dry-run)
        │
        ├── classify each translation by comparing pre-state to post-state
        │
        ├── mark_synced(TTL_WHATSAPP_TEMPLATES) and append the WABA to progress
        │
        └── sleep 60 / budget seconds
        ▼
write the CSV artifact, log the summary
```

**Reuse, not reimplementation** (FR-031, FR-032): applying Meta's list through the existing
`TemplateSyncUseCase` is what makes convergence, in-place name replacement and the absence of duplicate
rows structural. Reconciliation classifies and reports; the sync path records.

---

## Classification

Five categories, kept distinct because each points an operator at a different action (FR-034).

| `category` | Condition | Operator action |
| --- | --- | --- |
| `corrected` | Post-state format or names differ from pre-state | None — it is fixed |
| `unchanged` | Pre-state already matched Meta | None |
| `anomalous` | Post-state `parameter_anomaly` is set | Inspect; the template may need fixing at Meta |
| `format_not_yet_known` | Post-state `parameter_format` is still `NULL` — Meta did not return this template | Investigate; usually a pending library template |
| `unclassifiable` | Meta could not be reached for this WABA, the token is invalid, the WABA is gone, or the app is excluded by `ignores_meta_sync` | Fix the account, then re-run |

`previously_broken` is a **separate boolean column**, not a category: `true` when the pre-state body
contained named placeholders and the row had no recorded parameters. This is the fleet broken by the
pre-existing defect and the count SC-010 asks for. It is separate because a template can be both
broken-before and corrected-now, and collapsing that into one column would conflate categories FR-034
requires kept apart.

**Not counted as either classified or broken**: `format_not_yet_known` and `unclassifiable` (FR-015).

**WABA-level skip, not a translation category.** `skipped_recent_sync` is a run counter and a log line for a WABA whose TTL lock is held by a recent scheduled sync (FR-032, FR-034). No CSV translation rows are emitted for that WABA; it is not appended to `done_waba_ids`, so a resume retries it. It MUST NOT be stored as `category` on a translation row.

---

## Report artifact

CSV, one row per translation, fixed columns — predictable size for an account with thousands of templates
(NFR-004), and directly filterable and countable by an operator.

| Column | Example |
| --- | --- |
| `run_id` | `2026-09-17T18:04:11Z` |
| `project_uuid` | `3f2a...` |
| `app_uuid` | `6b2f...` |
| `app_code` | `wpp-cloud` |
| `waba_id` | `102290129340398` |
| `template_name` | `order_update` |
| `template_uuid` | `9c41...` |
| `translation_uuid` | `ab77...` |
| `language` | `pt_BR` |
| `message_template_id` | `1234567890` |
| `category` | `corrected` |
| `previously_broken` | `true` |
| `format_before` | *(empty — was NULL)* |
| `format_after` | `NAMED` |
| `param_names_before` | *(empty)* |
| `param_names_after` | `nome;cota` |
| `anomaly_type` | *(empty)* |
| `anomaly_body_names` | *(empty)* |
| `anomaly_example_names` | *(empty)* |
| `reason` | *(empty — set for `unclassifiable`)* |

**Name lists are semicolon-delimited.** For an `anomalous` row, `anomaly_body_names` and
`anomaly_example_names` carry both observed sets, which is what FR-011 requires to be retained.

**Example values never appear in the artifact or in the logs.** Only names, formats and counts. This
follows FR-044 and SC-011 — the artifact is a file an operator will copy around, and example values are
author-supplied content.

---

## Logging

Structured log records so a run is observable while in progress (FR-033), every one attributable to its
originating app, project and template (FR-043).

| Point | Level | Content |
| --- | --- | --- |
| Run start | `INFO` | `run_id`, target WABA count, `dry_run`, `resumed` |
| Per WABA start | `INFO` | `waba_id`, app count, position in the run |
| WABA skipped — lock held | `INFO` | `waba_id`, `skipped_recent_sync`; not marked done |
| Per translation classified | `INFO` | project, app, template name, language, `message_template_id`, category, `previously_broken`, format before → after |
| Anomaly observed | `WARNING` | Same identifiers plus `anomaly_type` and both name sets |
| WABA unclassifiable | `ERROR` | `waba_id`, reason, affected app UUIDs |
| Run end | `INFO` | Per-category counts, `previously_broken` total, artifact path, elapsed |

**Never logged at any level**: example values (FR-044, SC-011).

---

## Progress and resumption

Redis key `template_param_reconcile:progress`, JSON, `ex=60*60*24` — the same shape and TTL as the
`template_status:{app_uuid}` map that library template polling already uses.

```json
{
  "run_id": "2026-09-17T18:04:11Z",
  "started_at": "2026-09-17T18:04:11Z",
  "done_waba_ids": ["102290129340398", "987654321098765"],
  "counters": { "corrected": 412, "unchanged": 1180, "anomalous": 7,
                "format_not_yet_known": 3, "unclassifiable": 12, "previously_broken": 389,
                "skipped_recent_sync": 2 },
  "rows_written": 1614
}
```

| Behaviour | Rule |
| --- | --- |
| Interrupted run restarted | Resumes from `done_waba_ids`; already-processed WABAs are not re-fetched (FR-031, Story 4 scenario 4) |
| `--restart` | Deletes the key and starts a new `run_id` |
| A completed run re-run | Converges to the same values and produces an identical report — the classification is a pure comparison against Meta (Story 4 scenario 3, SC-005) |
| Concurrent with the scheduled sync for one WABA | If the TTL lock is held, skip the WABA, do not mark it done, increment `skipped_recent_sync`. Once the lock is clear, resume processes it; both paths then converge through `TemplateSyncUseCase`, last write wins, no duplicate rows (Story 4 scenario 5) |

Rows are appended to the artifact per WABA rather than buffered to the end, so an interrupted run leaves a
usable partial report.

---

## Testing

| Concern | Approach |
| --- | --- |
| Redis | A fake injected through `redis_conn`. **No test reaches real Redis** (Constitution VIII) |
| Meta | `TemplateService` mocked at the client boundary |
| Pacing | `sleep` injected so tests do not actually wait; assert it is called with `60 / budget` seconds |
| Five categories | One fixture per category, asserting they are never conflated |
| `previously_broken` | A translation with a named body and `variable_count = 0`, asserted both `previously_broken` and `corrected` |
| Resumption | Run, truncate progress mid-way, re-run, assert processed WABAs are skipped |
| Idempotency | Run twice against the same stubbed Meta response, assert byte-identical artifacts (SC-005) |
| `ignores_meta_sync` | Asserted `unclassifiable` with reason `sync_disabled`, not counted as classified |
| TTL lock held | WABA recorded as `skipped_recent_sync`, not in `done_waba_ids`, no mirror write, no translation CSV rows; not counted as classified, broken, or unclassifiable |
| Command layer | `call_command` with the use case patched: argument parsing, artifact written, exit code |
