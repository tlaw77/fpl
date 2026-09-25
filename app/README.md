# FPL Decision Centre Rebuild

This is the clean, contract-first client described in `/spec`. It is intentionally
isolated from the current production application in `/docs` until the ordered
delivery slices and acceptance gates are complete.

## Commands

```bash
npm ci
npm run check
npm run dev
npm run test:browser
```

`npm run check` runs lint, strict TypeScript, unit tests and the production build.
The browser suite starts the built preview automatically and checks both a 390px
mobile viewport and desktop Chromium.

## Current scope

Slice 01 provides:

- Vite and strict TypeScript;
- semantic design tokens and a responsive shell;
- five canonical navigation views with placeholder content;
- keyboard focus, skip navigation and reduced-motion foundations;
- unit, build and browser quality gates;
- no changes to the existing production dashboard or deployment.

Canonical contracts, lifecycle data and real pages arrive in subsequent slices.
