# GBDI design tokens for Quasar

Token + CSS-layer setup for GBDI frontends, built from **GBDI Brand
Guidelines v01 · 2024** and structured like `co2-calculator/frontend/src/css`.

Source order: the PDF first (printed values, then values measured from its
vector paths and baselines); where the PDF is silent, the live site
<https://www.gbdi.io> (its Framer CSS); on conflicts, the palette pages win.
Every value in `_options.scss` carries its provenance tag.

## Layers of tokens

```
02-tokens/_options.scss     raw palette + scales  ← the only place raw values live
        ↓
02-tokens/_decisions.scss   semantic tokens ($color-primary, $color-text-muted, hero tones, dataviz…)
        ↓
02-tokens/_components.scss  per-component tokens ($button-*, $card-*, $field-*, $table-*…)
        ↓
02-tokens/_quasar-bridge.scss   decisions → Quasar Sass variables ($primary, $h1, $button-*, …)
02-tokens/css-properties.scss   decisions → runtime CSS vars (--gbdi-*) for charts / inline styles
```

In a component: `@use 'src/css/02-tokens' as tokens;` then `tokens.$color-text`.
Never write hex in components — add an option, then a decision.

To change a value, edit it in its own layer file. The token files are Sass
modules (`@use`), so defining a variable earlier in `quasar.variables.scss`
does NOT override them.

## Cascade (same as co2-calculator)

`@layer reset, tokens, quasar-base, layout, quasar-overrides, components, utilities;`

Fonts live in a plain `00-fonts/fonts.css`, loaded before `app.scss`.

Quasar's CSS is imported inside `@layer quasar-base`, so overrides win
without `!important`; Vue SFC styles are unlayered and win over all layers.
`06-components/` holds the two GBDI patterns Quasar lacks: `.gbdi-card`
(standard card, `--grey`, `--panel`) and `.gbdi-hero-card--{green|blue|purple|orange}`.

## Wiring in `quasar.config.js`

```js
css: ['00-fonts/fonts.css', 'app.scss'],
build: {
  sassVariables: 'src/css/quasar.variables.scss',
  extendViteConf(viteConf) {
    // Block Quasar's auto-injected CSS: app.scss imports it inside @layer quasar-base
    viteConf.resolve ??= {};
    viteConf.resolve.alias ??= {};
    viteConf.resolve.alias['quasar/dist/quasar.sass'] = path.resolve(__dirname, './src/css/empty.scss');
    viteConf.resolve.alias['quasar/dist/quasar.css'] = path.resolve(__dirname, './src/css/empty.scss');
    viteConf.css ??= {};
    viteConf.css.preprocessorOptions ??= {};
    viteConf.css.preprocessorOptions.scss ??= {};
    viteConf.css.preprocessorOptions.scss.silenceDeprecations = ['import'];
  },
},
```

## Brand → Quasar mapping

| Quasar | GBDI | Value |
| --- | --- | --- |
| `primary` | Primary Green — buttons, accents, toggles | `#189D7E` |
| `secondary` | Black | `#3E3E3E` |
| `accent` | Orange Bright | `#F59B3A` |
| `positive` / `info` / `warning` | Green Dark / Blue Dark / Orange Dark | `#206D59` / `#31658D` / `#CC7212` |
| `negative` | **WARNING: not GBDI** — IT4R suggestion | `#C62828` |
| font | Satoshi (body, h4–h6); SK Modernist for h1–h3 / `.text-display` | |

## Where each scale comes from

| Scale | Value | Source |
| --- | --- | --- |
| Colours | full primary, secondary (4 hues × 4 steps) and supporting palettes | PDF p.14, p.18 |
| Type sizes | 68 / 60 / 32 display, 24 / 18 headings, 18 / 16 body | PDF p.13 |
| Responsive display | h1 68 → 50 → 32, h2 60 → 44 → 32; 14 / 12 UI text | gbdi.io presets |
| Line heights | display 1.25, body 1.2, paragraph 1.3, hero text 1.45 | measured, PDF p.13 / p.26 |
| | tight 1.1, long-form 1.6, letter-spacing −0.02em / −0.04em | gbdi.io |
| Radii | 2px chips, 4px buttons / swatches / hero cards, 8px standard cards, 10px panels | measured, PDF vector paths |
| | 40px pill | gbdi.io |
| Heights | 48px buttons and fields, 24px chips | measured, PDF ("Download" button) |
| Card padding | 44px standard, 32px hero | measured, PDF p.26 |
| Breakpoints | mobile ≤ 809px, tablet 810–1199px, desktop ≥ 1200px | gbdi.io |
| Spacing scale | 4px steps | not in either — carried over from co2-calculator |

## Brand rules the tokens encode

- Primary green in small splashes (buttons, icons, highlights) — never large fills.
- Pastels are the only colours for large fills, and only on **hero cards**
  (one set per page). Standard cards are white or Green-Grey Card `#F6F8F8`
  with a `#EEF2F2` border. Surfaces are flat.
- Hero card: pastel fill, Bright number, Dark text. Orange (not drawn in the
  PDF) uses Orange Dark for both, since Orange Bright on its pastel is 1.8:1.
- Secondary button = the guideline "Download" button: `#F6F8F8` fill,
  1px `#D5E6E2` border, 4px radius, 48px high.
- Lead paragraphs in Grey Text `#BCC4C2` (the guideline paragraph colour).
- SK Modernist for headings ≥ 32px; Satoshi for 24px / 18px headings and body.
- Illustrations: 1px `#646464` stroke, `#D5E6E2` accent, no white fill on grey.
- Data viz: green first, then blue, purple, orange; each with a dark → pastel
  ramp (`$dataviz-ramps`, `--gbdi-dataviz-<hue>-1..4`); Orange Bright highlight dot.

## Contrast notes (the design is kept as is)

| Pair | Ratio | Where |
| --- | --- | --- |
| white on Primary Green | 3.41:1 | primary buttons — AA only for ≥ 18.66px bold |
| Grey Text on white | 1.78:1 | lead paragraphs |
| Green-Grey Accent border on white | 1.29:1 | secondary button, fields |
| Orange Dark on Orange Pastel | 2.9:1 | orange hero card |

## Open points for GBDI

1. **Error red `#C62828` is NOT part of the GBDI design** (WARNING box in
   `_options.scss`) — validate or replace.
2. **Source conflicts**, resolved toward the palette pages: Grey Text
   `#BCC4C2` (p.18) vs `#BEBFBF` (p.13, gbdi.io); Black `#3E3E3E` (p.18) vs
   `#3D3D3D` (gbdi.io); Purple Pastel `#EFECFE` (p.14, gbdi.io) vs `#F0ECFE` (p.25).
3. **SK Modernist web licence** — confirm before self-hosting (see `00-fonts/fonts.css`).

Logos and illustrations are not included: the guidelines link to downloads
that were not available here.
