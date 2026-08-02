# MetaMCP Webapp Template

Reference implementation for MCP web dashboards. Clone or copy this structure for new webapps (e.g. git-github-mcp, robotics-mcp).

## Template Features

### Layout
- Retractable sidebar (`Sidebar.tsx`) with nav items
- Topbar with logger and help modals
- Dark theme (slate-950, slate-900, purple/blue accents)

### Modals
- `LoggerModal` - runtime logs (Ctrl+/)
- `HelpModal` - keyboard shortcuts
- `ToolExecutionModal` - MCP tool runner
- `ServerConnectionModal`, `ServerInspectionModal`, `JsonEditorModal`

### Local LLM Integration
- **Providers**: Ollama (default :11434), LMStudio, vLLM, any OpenAI-compatible server
- **Service**: `services/llm.ts` - `listModels()`, `chat(messages)`, `completion(prompt)`
- **Config**: Settings page - provider, baseUrl, model, fetch models
- **Chat Page**: Multi-turn chat UI backed by local LLM

### Setup for New Webapps
1. Copy `web/src/` structure
2. Configure `api/client.ts` for your backend base URL
3. Add/remove sidebar pages as needed
4. LLM: Reuse `llm.ts` and Chat page; adjust Settings section
5. MCP tools: Use `api.executeTool(server, tool, args)` pattern

### Key Paths
- `web/src/services/llm.ts` - LLM client (Ollama, LMStudio)
- `web/src/pages/Chat.tsx` - Chat UI
- `web/src/pages/Settings.tsx` - LLM settings section
