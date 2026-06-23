# datEAUbase UI Design System

The visual language introduced with the **Story pages** (Campaign / Equipment /
Stream). Applies app-wide. Carry these choices into any new page so the app stays
cohesive.

## Where it lives

| Concern | File | Scope |
|---|---|---|
| Colors, base, font | `.streamlit/config.toml` `[theme]` | **Every page, automatically** |
| Badges, KPI cards, section cards, timeline, annotation feed | `app/components/theme.py` | Pages that call `theme.inject_css()` |
| Composed story widgets (header, timeline, freshness…) | `app/components/entity_story.py` | Story pages + Explore |

## Style

**Data-Dense Dashboard** — multiple widgets/tables, KPI cards, modest padding,
grid layout, maximum legible data per screen. Not ornate. Always filterable.

## Tokens

| Role | Hex | Use |
|---|---|---|
| Primary | `#1E40AF` | Primary actions, links, active nav, main data series |
| Accent | `#D97706` | Highlights, secondary series, "new" markers (WCAG-safe amber) |
| Background | `#F8FAFC` | App canvas |
| Surface | `#FFFFFF` | Cards, inputs, sidebar |
| Text | `#0F172A` | Body (>=4.5:1 on canvas and surface) |
| Secondary text | `#475569` | Labels, captions, timestamps |
| Muted / Border | `#E9EEF6` / `#DBEAFE` | Dividers, card borders |
| OK / Warn / Bad | `#16A34A` / `#D97706` / `#DC2626` | Status only |

## Typography

- Body **Fira Sans** (config `font = "sans serif"` falls back cleanly; Fira applied
  to custom components). Headings same family, weight 600.
- **Tabular figures** (`font-variant-numeric: tabular-nums`) on every numeric
  column, timestamp, and metric — prevents column jitter. Monospace for IDs and
  timestamps.
- Type scale: 11 (uppercase labels) · 13.5 (body/table) · 15 (section titles) ·
  22 (page title) · 26 (KPI value).

## Component rules

- **KPI strip**: 4 `st.metric` cards max per row; one number each, optional small
  unit. Cards get border + soft shadow via theme CSS.
- **Section card**: white surface, 1px `#DBEAFE` border, soft shadow, 10px radius.
  Header row = title (left) + muted sub-caption (right).
- **Badges**: pill, 12px, 600 weight. Status badges pair a colored dot **with a
  text label** — never color alone (`color-not-only`). Tones: ok/warn/bad (status),
  blue/amber/grey (category).
- **Timeline** = the story spine. One vertical rail; each event is a node (colored
  by kind) + monospace date + bold title + muted description.
- **One primary visual per section**; one primary CTA per screen.

## Hard rules (carry over)

1. Contrast >= 4.5:1 for text; status never conveyed by color alone (dot **and** label).
2. Tabular figures on all data columns; monospace for IDs/timestamps.
3. **Freshness vs status are different things**: data freshness = plain grey
   timestamps ("12 min ago"), no traffic lights. Colored status badges are only
   for operational equipment/sensor status from the DB.
4. SVG/Streamlit icons, never emoji as structural icons (existing nav emoji are
   grandfathered; don't add more in content).
5. Hover transitions 150–300ms; respect `prefers-reduced-motion`.

## Applying to a new page

```python
from app.components import theme
theme.inject_css()
st.markdown(theme.badge("OK", tone="ok", dot=True), unsafe_allow_html=True)
```

For the colors/font alone, do nothing — `.streamlit/config.toml` already themes it.
