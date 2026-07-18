# powerplan — Product Requirements

**One-liner:** An MCP server that makes `PLAN.md` the operational backbone of
agentic development — human-language tools for creating iterations, tracking
tasks, and keeping the plan truthful across a multi-agent swarm.

**Home:** standalone GitHub project (CynaCons/powerplan). Also available as a PowerSpawn git submodule so spawn-based projects get both MCP servers.

Status: PRD revision 2026-07-18 — see [PLAN.md](PLAN.md) for the build plan.

---

## 1. Problem

`PLAN.md` is the coordination backbone across projects, but it is often
maintained by freeform agent edits. Observed failure modes:

- An agent marked an iteration COMPLETE whose behavior failed in the live app;
  the plan carried no durable signal to challenge that claim.
- The plan header ("Active iteration") drifted from the actual state.
- Work happened but was invisible ("agent worked, nothing changed") — no
  lightweight record of which agent last touched a line.
- Every project re-invents plan conventions; agents parse them inconsistently.

## 2. Users

- **A coordinator agent:** reads state, creates iterations, closes iterations,
  keeps the header truthful.
- **Worker agents** (e.g. PowerSpawn spawns): complete tasks, add discovered
  tasks, optionally tag lines with their agent id.
- **The human developer:** reads ASCII views, sets goals, arbitrates.

## 3. Product principles

1. **Single writer.** All plan mutations go through powerplan tools; direct
   file edits are lint violations (process rule in each project's agent docs).
2. **Evidence or it didn't happen** — *workflow principle only.* Completing
   work should rest on real proof (artifact path, commit hash, report line,
   live session). The MCP does **not** require, store, or enforce evidence
   parameters. Coordinators and humans hold that gate outside the tool.
3. **Truthful header, always.** Active-iteration/header state is derived and
   auto-synced, never hand-maintained.
4. **Tolerant reader, surgical writer.** Parse any reasonable PLAN.md flavor;
   rewrite only the lines being edited; preserve all freeform prose
   byte-for-byte. Phase-like headers and other non-format prose stay opaque.
5. **Human-language API.** Tool names read like sentences
   (`create_iteration`, `complete_task`, `show_current_iteration`).
6. **Lightweight attribution.** Mutation tools accept an optional `agent`
   argument; when provided, the touched task/iteration line gets a small
   trailing tag like `[agent: grok-4-5]`. Nothing more — no audit journal,
   no before/after log file.

## 4. Managed plan format (powernote style)

The format powerplan authors and rewrites is:

| Construct | Pattern |
|---|---|
| Major | `## vX.Y — Title` (optional `>` one-line description under it) |
| Iteration | `### vX.Y.Z — Title` (optional status in title) |
| Goal | optional `**Goal:** ...` line under an iteration |
| Tasks | `- [ ]` / `- [x]` checkbox lines |
| Backlog | optional `## Backlog` (or `## Future (Backlog)`) section |

There is **no phase concept** in the managed format. Files that contain
phase-like headers (`# Phase N: ...`) or other freeform structure are still
readable: those lines are preserved as opaque prose, not modeled as structure.
Iterations (and majors, when present) are the structural units tools operate on.

## 5. Capabilities (tool surface)

### Read / show
| Tool | Behavior |
|---|---|
| `show_plan` | ASCII overview of majors + iterations with progress |
| `show_current_iteration` | ASCII detail of the active iteration |
| `get_iteration(version)` | Structured JSON (goal, tasks, status, progress) |
| `list_iterations(filter)` | open / complete / all |
| `get_backlog` | Backlog items |
| `find_task(text)` | Locate tasks by fuzzy text match |

### Mutate
| Tool | Behavior |
|---|---|
| `create_iteration(version, title, goal?, agent?)` | New iteration section, correct position, version monotonicity enforced |
| `set_iteration_goal(version, goal, agent?)` | Set/replace the **Goal:** line |
| `add_task(version, text, agent?)` / `update_task` / `remove_task` | Checkbox task CRUD |
| `add_to_backlog(text, agent?)` | Append to backlog section |
| `defer_task(version, task, to, reason?, agent?)` | Move to backlog/another iteration |

Optional `agent` on any mutation that touches a line: append/update a trailing
`[agent: <id>]` tag on that line when provided.

### Lifecycle
| Tool | Behavior |
|---|---|
| `complete_task(version, task, agent?)` | Tick the task; optional agent tag. No evidence parameter. |
| `reopen_task(version, task, agent?)` | Untick the task (e.g. when a completion is invalidated) |
| `start_iteration(version)` | Marks active; auto-syncs plan header |
| `close_iteration(version, force?)` | Reports open tasks; requires `force=true` to close while any remain open; stamps date / status |

### Integrity
| Tool | Behavior |
|---|---|
| `check_plan` | Minimal structure lint only: version monotonicity, malformed checkboxes/sections, header/active-iteration drift. Does **not** enforce evidence or audit trails. |

## 6. Cross-project mechanics

- **Discovery:** walk up from cwd to the nearest `PLAN.md` (zero per-project
  config). Optional `plan_path` argument on every tool for overrides.
- **Concurrency:** advisory file lock around read-modify-write so parallel
  workers don't clobber each other.

## 7. Enforcement model (honest scope)

The MCP cannot physically block a raw file edit. Enforcement is:

1. powerplan as the only sanctioned writer (agent-docs rule in each project);
2. `check_plan` available as a structure lint (optional pre-commit/CI);
3. process/culture: "evidence or it didn't happen" is how humans and
   coordinator agents judge completions — not a tool parameter.

There is no `.plan-audit.jsonl` and no mutation journal.

## 8. PowerSpawn synergy (why it lives here)

- Same install: every project with PowerSpawn gets powerplan for free.
- Coordination link (v0.2+): worker spawns can pass `agent` with their
  spawn id so touched lines show `[agent: …]` without a separate log.
- Shared Python stack and release cadence.

## 9. Non-goals (v0.1)

- Not a general task tracker/Jira replacement; PLAN.md stays a readable file.
- No web UI; ASCII + markdown only.
- No evidence parameter, audit journal, or automatic verification of work claims.
- No forced rewrite of existing PLAN.md files to the managed format (tolerant
  reader preserves foreign structure as prose).

## 10. Success criteria

- At least two real projects operated through powerplan with zero manual
  PLAN.md edits for one full iteration each.
- `check_plan` green (structure lint) when used as a gate.
- A coordinator agent can answer "what is open and what just closed" from
  `show_plan` / `show_current_iteration` without reading the raw file by hand.
