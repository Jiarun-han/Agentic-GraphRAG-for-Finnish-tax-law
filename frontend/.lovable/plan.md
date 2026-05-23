# Taxxa AI — Finnish Tax Law Research Assistant

A single-page TanStack Start app that lets users ask Finnish tax law questions and renders the structured response from a configurable backend (`/ask`).

## Design

- Dark navy `#1a1f36` background, white text, Finnish blue `#003580` accent
- Inter font, soft shadow cards, rounded corners
- Light/dark mode toggle (defaults to dark)
- Responsive: two-column (answer + sources) on desktop, stacked on mobile

Tokens added to `src/styles.css` as oklch semantic variables: `--background`, `--foreground`, `--primary` (Finnish blue), `--card`, `--accent`, plus warning/danger for banners. Inter loaded via Google Fonts in `__root.tsx` head.

## Pages & Components

Single route: `src/routes/index.tsx` composes the page from small components in `src/components/taxxa/`:

- `Header.tsx` — logo "Taxxa AI" with a small graph/network icon (lucide `Network`), subtitle, "Powered by GraphRAG + DeepSeek" badge, theme toggle
- `QuestionForm.tsx` — textarea (3 rows), 3 example-question chips that fill the textarea, primary "Ask" button, loading state ("Analyzing sources…" with pulsing dot)
- `AnswerCard.tsx` — renders markdown via `react-markdown`; post-processes `[source_id]` tokens into blue clickable badges that scroll to the matching citation
- `CitationsCard.tsx` — list of citation mini-cards; publisher icon resolved from `source_id` prefix (📜 Finlex, 🏛️ Vero), shows `doc_title` + `section` + claim
- `SearchStrategyCard.tsx` — collapsible (shadcn `Collapsible`), renders `sub_queries` as chips and "Context nodes analyzed: N"
- `WarningsBanner.tsx` — yellow banner for `unverified_claims`, red banner for `conflicts`
- `AssumptionBadge.tsx` — info banner above answer when `assumption` present
- `Footer.tsx` — hackathon credits
- "Copy answer" button on answer card; "Ask another question" button that scrolls back to the form

## API Integration

- Config: read `import.meta.env.VITE_API_URL` with fallback `http://localhost:8000`. Add to `.env` (committed) so it can be changed.
- Client hook `useAskTaxxa` using TanStack Query `useMutation` → `POST {API_URL}/ask` with `{ question }`
- Typed `TaxxaResponse` interface matching the spec
- On network error / non-2xx: render friendly message "Backend not connected. Please start the API server." (toast via sonner + inline error card)

No backend / Lovable Cloud needed — this is a pure frontend client to the external FastAPI service.

## Dependencies to add

- `react-markdown` (markdown rendering)
- Inter font via Google Fonts `<link>` in root head

## File changes

- `src/styles.css` — replace theme tokens with Taxxa palette (light + dark), set Inter as base font
- `src/routes/__root.tsx` — add Inter font links, update meta title/description to "Taxxa AI — Finnish Tax Law Research Assistant", mount `<Toaster />` and theme provider
- `src/routes/index.tsx` — replace placeholder with the page composition
- `src/components/taxxa/*` — new components listed above
- `src/lib/taxxa-api.ts` — typed fetch client + types
- `src/hooks/use-theme.ts` — minimal dark/light toggle persisted to localStorage
- `.env` — `VITE_API_URL=http://localhost:8000`

## Out of scope

- No persistence, no auth, no history of past questions
- No backend implementation (consumes the external API as specified)
