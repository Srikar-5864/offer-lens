---
name: offerlens-ui
description: Build the OfferLens demo frontend (web/) in the "Primary Print" design system — paper, ink and flat red/blue/yellow, no gradients, no purple, no boxy cards — with source-highlighting receipts. Use before writing or changing any HTML, CSS or JS.
---

# OfferLens UI

Read `docs/DESIGN.md` in full first. It overrides any habit or default you have.

## Stack
- `web/index.html`, `web/styles.css`, `web/app.js` (ES module), served by FastAPI `StaticFiles`. No framework, no build step, no CDN.
- Fonts: download Archivo (400/500/800) and JetBrains Mono (400) woff2 into `web/fonts/` at setup; `@font-face` with `font-display: swap`.
- Hash-based routing: `#/extract` (default), `#/compare`, `#/results`.

## Build order
1. Tokens + type + layout grid in `styles.css`. Light + dark.
2. Extract view: textarea band, example pills (from `/api/examples`), Extract button, receipt.
3. Source highlighting (see below). 4. JSON toggle + copy. 5. Compare. 6. Results (hand SVG bars from `/api/results`).

## Receipt rendering (safe)
Build every node with `document.createElement` + `textContent`. Never `innerHTML` (CSP + SECURITY.md §4).
Field → color: merchant/issuer/payment_modes = blue · value/max_cap/min_order = red · dates = yellow · others = ink.

## Source highlighting algorithm
For each extracted scalar, generate candidate surface forms (e.g. 150 → "150", "₹150", "Rs 150", "Rs.150", "1.5k";
dates → "31st Oct", "31 Oct", "31/10"; issuer "HDFC Bank" → "HDFC"). Find case-insensitive matches in the
original text, resolve overlaps (longest wins), then rebuild the text node as a sequence of text nodes and
`<mark data-field=…>` elements. Hover/focus on a mark or receipt line toggles `.is-linked` on both.
Unmatched fields simply have no highlight — never fake one.

## Don'ts (auto-reject)
`linear-gradient`, `radial-gradient`, `conic-gradient`, any hue 250–330°, cards with border+shadow, Tailwind/shadcn defaults,
Inter/Roboto/Arial, emoji icons, spinners from libraries.

## Verify
Run the DESIGN.md checklist, plus:
`grep -nE "gradient|innerHTML|#(7|8|9)[0-9a-f]{2}[c-f]" web/` must return nothing.
Screenshot 375px and 1440px in light and dark; look at them before calling it done.
