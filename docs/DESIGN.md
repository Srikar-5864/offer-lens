# UI / UX design — "Primary Print"

Direction: Bauhaus poster meets a printed receipt. Warm paper, black ink, three flat primaries used as
**meaning**, not decoration. Open layouts divided by rules (lines), not boxes. Confident type.

## Hard rules (a PR breaking any of these is rejected)
- ❌ **No gradients** anywhere (backgrounds, buttons, text, borders, shadows that fake gradients).
- ❌ **No purple / violet / indigo** in any token. Hue 250°–330° is banned.
- ❌ **No boxy card grids.** No bordered rectangles with drop shadows holding content. Group with whitespace,
  hairline rules, and alignment. Containers, if any, are pills, circles, or full-bleed bands.
- ❌ No glassmorphism, no neon glow, no emoji as UI icons, no default Tailwind/shadcn look, no Inter/Roboto/Arial.
- ✅ Primaries carry meaning and are used sparingly (≤10% of any screen).

## Tokens (`web/styles.css` `:root`)
```css
--paper:   #F3EEE3;  /* background */
--paper-2: #E9E2D3;  /* bands, input well */
--ink:     #141414;  /* text, rules */
--ink-2:   #5B574F;  /* secondary text (AA on paper) */
--red:     #D7261E;  /* money: value, cap, min order; errors */
--blue:    #1446A0;  /* who: merchant, issuer, payment modes; links, focus ring */
--yellow:  #F2B705;  /* when: dates; highlights; "constrained" badge */
--green-ok:#1F7A3A;  /* only for "schema valid" state */
--rule: 1.5px solid var(--ink);
--radius-pill: 999px;
```
Dark mode (`prefers-color-scheme: dark`): paper `#121110`, ink `#F3EEE3`, primaries brightened
(`#FF4A3D`, `#5B8CFF`, `#FFC933`). Still no gradients.

Type (self-host woff2 in `web/fonts/`, no external CDN at runtime):
- Display: **Archivo** 800, tight tracking (-0.02em), sizes 56/40/28
- Body: **Archivo** 400/500, 16/1.5
- Data/JSON: **JetBrains Mono** 400, 14
Spacing: 4px base, scale 4·8·12·16·24·32·48·72. 12-column asymmetric grid, content offset to columns 2–11.

## Shapes vocabulary
Circle (status, numbers), half-circle (section markers), pill (buttons, chips, toggles), thick rule (separators).
Field chips: pill with a solid color dot on the left matching its meaning color.

## Screens
**1. Extract (home)**
- Left 7 cols: huge headline "Messy offer in. Clean JSON out." then a borderless textarea on `--paper-2`
  band (no border, 2px ink underline that thickens on focus). Example pills underneath (8 demo examples).
- Big round ink button "Extract →" (pill, ink fill, paper text). `⌘/Ctrl+Enter` shortcut.
- Right 5 cols: result as a **receipt**: each field on its own line, label left (ink-2, small caps),
  value right, separated by dotted rules. Color dot = meaning. Nulls shown as an em dash in ink-2 — not hidden.
- **Source highlighting (signature feature):** after extraction, spans in the input text that match extracted
  values get a colored underline (3px, field's color). Hover a receipt line ↔ its span highlights, and vice versa.
- Toggle (pill switch) "Receipt / JSON". JSON view: mono, syntax colors from the primaries, copy button.
- Status row: circle badge "VALID" (green-ok) or "INVALID", latency in ms, model name, "constrained" yellow tag.

**2. Compare** — same input, two receipts side by side: "Base 1.5B + grammar" vs "OfferLens 1.5B".
Fields that differ get a red strike on the wrong side. Single line verdict above: "4 fields fixed, 1 hallucination removed".

**3. Results** — the A/B/C story as a flat bar chart (hand SVG, no chart lib needed): one row per metric,
bars in ink / blue / red, direct value labels, no legend box, no gridline clutter. Below: cost per 1k
as huge numerals ("₹X vs ₹Y") with sources cited in small text. Then "Where it still fails" — 3 real error examples.

## Interaction & quality
- Loading: a single circle that fills clockwise (CSS conic? **No** — that's a gradient; use stroke-dashoffset on an SVG circle).
- Motion: 150–200ms ease-out, opacity/translate only. Respect `prefers-reduced-motion`.
- Empty state: a sentence + one example pill, not an illustration.
- Errors: inline, red text with plain-language fix ("That's longer than 2,000 characters — trim it.").
- Accessibility: WCAG AA contrast, visible 3px blue focus ring, all controls keyboard reachable, `aria-live="polite"` on results,
  labels on every input, color never the only signal (dots + text labels).
- Responsive: 375px → single column, receipt below input; 1440px → as described. No horizontal scroll.

## Checklist before demo
- [ ] grep styles for `gradient`, `#8`/`#9` purples, `box-shadow` — none present
- [ ] No element has both a border on all 4 sides and a shadow
- [ ] Works at 375px and 1440px, light and dark
- [ ] Keyboard-only run-through: paste → extract → toggle JSON → copy
- [ ] Every number on Results comes from `/api/results`
