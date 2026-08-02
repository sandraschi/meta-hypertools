# Landing Page Builder - `scaffold_ops(operation="landing_page")`

The quick marketing surface. Tailwind page in the fleet design language
(dark zinc, amber accents, lucide icons) - no backend, no build chain
beyond the static scaffold.

## Usage

```python
scaffold_ops(operation="landing_page", name="fleet-landing",
             description="Landing page for the fleet launch")

# Dashboard
Builders page -> Landing Page card
```

## What you get

- Responsive Tailwind layout (hero, features, CTA)
- Fleet dark theme baked in
- SEO-friendly structure

## Limits

- **`config` required** via MCP.
- **Static only** - no backend, no forms wiring, no analytics. It is a
  page, not an app.
- **Copy is placeholder** - write the real copy (see the fleet promotion
  standard: concrete workflows, not "AI magic").
