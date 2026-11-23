# Bulk operations

powerplan has two kinds of bulk, and they answer different questions.

| | Many targets, one kind of change | Many kinds of change |
|---|---|---|
| Tool | `complete_task`, `add_tasks`, `update_task`, `add_to_backlog`, … | **`apply_ops`** |
| Shape | one tool, `indexes` / `tasks` / `changes` / `texts` | a list of ops, each naming a tool |
| Scope | one iteration | any number of iterations, plus the backlog |
| Writes | one | one |
| Since | 0.7.0 | 0.11.0 |

Reach for the per-tool arrays when you are doing one thing to several rows —
`complete_task(version, indexes=[1,3,4])` stays the shortest way to tick three
tasks. Reach for `apply_ops` when a turn needs *different* changes.

---

## Why `apply_ops` exists

A normal turn-end is four changes:

```text
complete_task(v0.11.0, indexes=[1,2,3])
add_tasks(v0.11.0, ["follow-up a", "follow-up b"])
add_to_backlog(texts=["deferred thing"])
close_iteration(v0.11.0, stamp="2026-11-23")
```

As four calls that is four round trips and four full load → mutate → normalize →
write cycles. Worse, it is **not atomic**: if `close_iteration` refuses because
open tasks remain, the first three writes have already landed and `PLAN.md` is
half-updated. The agent then has to work out what did and did not apply.

One `apply_ops` call is one write, and all-or-nothing:

```json
{
  "agent": "claude-opus-5",
  "version": "v0.11.0",
  "ops": [
    {"op": "complete_task", "indexes": [1, 2, 3]},
    {"op": "add_tasks", "tasks": ["follow-up a", "follow-up b"]},
    {"op": "add_to_backlog", "texts": ["deferred thing"]},
    {"op": "close_iteration", "stamp": "2026-11-23"}
  ]
}
```

If any op fails, **nothing is written** and the error names the op by position:

```json
{"success": false, "written": false, "applied": 0,
 "failed_op": {"i": 3, "op": "close_iteration"},
 "error": "ops[3] (close_iteration): Iteration v0.11.0 has 2 open task(s). Pass force=true to close anyway."}
```

## Rules

1. **Each op is `{"op": "<tool name>", ...that tool's own arguments}`.** The 14
   op names are the existing mutating tools, and the keys are their existing
   schemas, so there is nothing new to learn: `create_major`,
   `create_iteration`, `set_iteration_goal`, `add_task`, `add_tasks`,
   `complete_task`, `reopen_task`, `update_task`, `remove_task`, `defer_task`,
   `add_to_backlog`, `append_prose`, `start_iteration`, `close_iteration`.
2. **Ops run in order and see earlier ops' changes.** So create → populate →
   close works in one call.
3. **Atomic.** One parse, one normalize, one write, under the file lock. Any op
   raising aborts the batch before anything reaches disk. The write itself goes
   to a temp file and is moved into place, so a crash cannot truncate `PLAN.md`.
4. **`version` is inherited, with three behaviors.** Ops that address an
   *existing* iteration (`complete_task`, `add_tasks`, `close_iteration`, …)
   take the batch-level `version` when they omit their own. `create_major` and
   `create_iteration` name a *new* section and so always need their own —
   inheriting would mean "create the thing that already exists".
   `add_to_backlog` and `append_prose` have no version at all and reject the key.
5. **The default is resolved once, before the first op.** It is the batch-level
   `version`, else the current iteration. `start_iteration` and
   `close_iteration` move the `(current)` marker, so resolving per-op would let
   a close silently redirect every later op; pinning it up front cannot.
6. **`agent` is inherited only where the tool takes one.** Not by
   `update_task`: that rewrites an existing `[agent: x]` tag whenever an agent
   is given, so a batch-level default would quietly reassign another agent's
   work. Pass `agent` inside the `update_task` op if you do mean to.
7. **Indexes shift after `remove_task` / `defer_task`.** Those drop rows, so
   1-based positions after them mean different tasks. Addressing by index in an
   iteration where an earlier op in the same batch dropped a row is **refused**,
   naming both ops — address by text (`task` / `tasks`) instead, or put the
   removals last. Appending never shifts anything, so index-after-add is fine.
8. **Shape is validated before the first mutation runs** — unknown op, unknown
   key, missing required key, bad caps — so a typo in op 7 is reported with its
   position instead of surfacing as a `TypeError` from somewhere inside. Semantic
   failures (task not found, iteration not found, open tasks on close) can only
   come from the mutation itself; they abort the batch the same way. Every
   failure is a `ValueError` with a locatable message, never an `AttributeError`.
9. **At most 50 ops.** Each op's own 100-target cap still applies inside it.
10. **The result carries the lint report.** `check.ok` / `check.issue_count`
    come from `check_plan` over the mutated plan, so a batch that leaves the
    document dirty (a forced close with open tasks, two iterations marked
    current) says so without another call.

## `dry_run`

`dry_run: true` parses, applies and normalizes exactly as a real call, reports
the per-op outcome, and writes nothing. It raises everything a real call would,
including a missing `PLAN.md`, so it is an honest pre-flight rather than a
weaker check — useful before a long batch, or when an agent is unsure whether a
close will be refused.

## Result

```json
{"success": true, "path": "/…/PLAN.md", "written": true, "dry_run": false,
 "applied": 4, "resolved_version": "v0.11.0",
 "ops": [{"i": 0, "op": "complete_task", "version": "v0.11.0", "count": 3},
         {"i": 1, "op": "add_tasks", "version": "v0.11.0", "count": 2},
         {"i": 2, "op": "add_to_backlog", "count": 1},
         {"i": 3, "op": "close_iteration", "version": "v0.11.0"}],
 "check": {"ok": true, "issue_count": 0},
 "iterations": 27, "message": "applied 4 op(s) in one write"}
```

A summary, not the task rows. Per-op `index` values are *mid-batch* and already
stale by the time the batch ends, so echoing them would mislead. Read the result
back with `show_current_iteration`, which the turn-end rule asks for anyway.

## Not included

`create_plan` is not an op: it creates the file, under its own lock, and
`apply_ops` requires a plan that already exists. The read-only views
(`show_*`, `get_*`, `find_task`, `check_plan`) are not ops either — a batch of
mutations returns a summary, and `check_plan`'s verdict already rides along in
the result.

## Python

```python
from powerplan import apply_ops, mutations as m

m.mutate_and_save(
    "PLAN.md",
    lambda plan: apply_ops(plan, [
        {"op": "complete_task", "version": "v0.11.0", "indexes": [1, 2]},
        {"op": "close_iteration", "version": "v0.11.0", "stamp": "2026-11-23"},
    ]),
)
```

`apply_ops` is pure in-memory: the caller supplies the one write. An op adapter
must never call `save_plan` / `mutate_and_save` itself — that is what keeps the
batch all-or-nothing.
