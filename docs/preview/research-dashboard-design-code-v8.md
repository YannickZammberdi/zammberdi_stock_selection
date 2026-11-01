# Research Dashboard Design Code — V8

Reusable visual system extracted from the approved 药明康德 V8 homepage. This is a **visual layer only**: keep each report's data, analysis, and information architecture separate.

## Files

- `research-dashboard-v8.css` — complete stylesheet (layout foundation plus V8 visual layer) for the V7/V8-style semantic hooks.
- `药明康德_603259_研究首页_v8.html` — reference implementation.

## Apply it

Include the stylesheet in the page head. It contains both the homepage layout rules and the V8 visual layer:

```html
<link rel="stylesheet" href="research-dashboard-v8.css">
```

Keep or map these hooks in the target page: `.hero-main`, `.valuation`, `.target`, `.metrics` / `.metric`, `.score-panel`, `.quality-table` / `.q-row`, `.logic-grid` / `.logic-item` / `.logic-claim`, `.scenario-list` / `.scenario-row`, and `.risk-panel`.

The stylesheet is a visual/layout system, not a data template. If the next page uses different markup, map its corresponding regions to these hooks rather than changing its content to match the reference.

## Design rules

- Canvas: warm neutral `#F1EFE9`; ordinary cards: warm near-white `#FBF9F4`.
- Positive: `#D7F0DE` / `#166534`; attention: `#FFF0B3` / `#854D0E`; risk: `#F8DADA` / `#991B1B`.
- Color by meaning, not by section. Keep objective market data neutral; color full semantic cards and scenario rows.
- Cards use 12–16px corner radii, soft shadows, generous padding, and minimal borders. Avoid thick colored rails and repeated dividers.
- Hierarchy: clear section title → bold module title → short bold takeaway → regular-weight explanation → muted supporting note. Emphasize only selected figures.
- Valuation Q&A uses one consistent question-and-answer row style; do not put an isolated semantic-color badge behind one question label.
- Responsive overrides preserve the card language on mobile; verify at desktop and phone widths after applying.

## Semantic assignment guidance

Use positive styling only for supported positive conclusions, attention styling for assumptions/shortfalls requiring monitoring, and risk styling for material downside. Do not infer a color from the subject area alone. For example, a valuation snapshot is neutral; the target upside can be positive, while the assumptions behind it may need attention styling.
