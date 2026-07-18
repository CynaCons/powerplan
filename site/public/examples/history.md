# ShopQueue — Implementation Plan

**Goal:** Queue tablet for a small shop; offline-first, one HTML artifact.

---

## v0.1 — Text on Canvas (Foundation)
> First usable version

### v0.1.0 — Project Scaffold + App Shell
- [x] Initialize Vite React-TS project
- [x] App shell layout
- [x] Smoke test: dev server clean

### v0.1.1 — Stores + default data
- [x] Workspace store
- [x] Canvas store
- [x] Smoke: stores hydrate

## v0.2 — Testing + polish
> SRS + Playwright

### v0.2.0 — Testing infrastructure
- [x] Playwright config
- [x] data-testid attributes
- [x] Smoke: `npx playwright test` passes

### v0.2.1 — Interaction overhaul (user feedback)
- [x] One-shot text tool
- [x] Multi-select Ctrl+Click
- [x] 52 tests pass

## v0.3 — Shipping
### v0.3.0 — Release pipeline
- [x] GitHub Actions HTML artifact
- [x] Tag v0.3.0

## Planned (Not Yet Shipped)
### Print
- [ ] Print CSS
- [ ] Ctrl+P layout

## Future (Backlog)
- **Plugins** — community extensions
- **Mobile PWA** — tablet polish
