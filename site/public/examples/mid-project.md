# Field Guide — Implementation Plan

**Goal:** Offline field notebook with hierarchy and save-in-place.

**Philosophy:** Evidence or it didn't happen. One writer for the plan.

---

## Current Status

| Iteration | Status |
|-----------|--------|
| v0.1.x | **shipped** — canvas + text |
| v0.2.0 | **current** — File System Access save |
| v0.2.1 | planned — revert to last saved |

---

## v0.1 — Canvas Core
> Shipped foundation

### v0.1.0 — Scaffold + text
- [x] App shell
- [x] Text tool + inline edit
- [x] Hierarchy panel

## v0.2 — Files
> Real files, not localStorage theatre

### v0.2.0 — Save-in-place (current)
**Goal:** Ctrl+S writes the open HTML via FSA
- [x] File System Access handle store
- [ ] Debounced autosave 1.5s
- [ ] Dirty indicator in top bar
- [ ] E2E: save → reopen → content intact
- [ ] Smoke + Playwright green

### v0.2.1 — Revert
- [ ] Revert to last saved from handle
- [ ] Confirm dialog when dirty

## Future (Backlog)
- Cloud sync (post-MVP)
- Collaboration
