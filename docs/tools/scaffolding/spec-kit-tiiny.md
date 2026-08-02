# Spec Kit / Tiiny / Questionnaire

The three supporting makers.

## Spec Kit (SDD) - `operation="spec_kit"`

GitHub's Spec-Driven Development toolkit integration. Scaffolds a project
with `/speckit.*` slash commands for structured planning.

```python
scaffold_ops(operation="spec_kit", name="my-project",
             config={"ai_integration": "opencode"})
```

| Parameter | Meaning |
|-----------|---------|
| `config.ai_integration` | `opencode` / `claude` / `copilot` / `cursor` / `gemini` (default opencode) |

See [../spec-kit-integration.md](../spec-kit-integration.md) for the
full integration guide.

**Limits**: requires the `specify` CLI on the host - the generator
checks the path and fails honestly if missing.

## Tiiny Site - `operation="tiiny_site"`

Static page scaffold + deploy to tiiny.host.

```python
scaffold_ops(operation="tiiny_site", name="my-page")
```

**Limits**: deploys to a third-party host - requires tiiny.host
credentials and network. The scaffold itself is offline-safe; the deploy
is not.

## Questionnaire - `operation="questionnaire"`

The interactive config card. Renders in chat (Prefab) so the user picks
features without reading the schema.

```python
scaffold_ops(operation="questionnaire")
```

**Limits**: interactive only - no arguments, no headless mode. Use the
other operations directly if you already know the config.
