# Patchright Browser

MCP server for browser automation via [Patchright](https://github.com/nicobailey/patchright). Multi-profile, multi-mode (headed/headless), StreamableHTTP protocol.

## For AI Agents

If you're an AI agent reading this repo, follow these steps to install and configure:

### 1. Clone & Install

```bash
git clone https://github.com/rickicode/patchright-browser.git
cd patchright-browser
bash install.sh
```

### 2. Start MCP Server

```bash
~/.patchright-browser/start.sh
```

Server runs at `http://127.0.0.1:9877/mcp/` (StreamableHTTP MCP protocol).

### 3. Configure Your MCP Client

Add to your MCP config (`~/.hermes/config.yaml` or equivalent):

```yaml
patchright:
  url: http://127.0.0.1:9877/mcp/
  connect_timeout: 30
  enabled: true
```

Or add via CLI:
```bash
hermes mcp add patchright http://127.0.0.1:9877/mcp/
```

### 4. Install Skills (Optional)

Copy automation skills to your skills directory:

```bash
cp -r skills/* ~/.hermes/skills/
```

Skills available:
- `x-search` — X.com search & data extraction
- `threads-search` — Threads search & data extraction
- `instagram-automation` — Instagram DM, post, comment
- `threads-automation` — Threads post, reply, DM
- `x-automation` — X.com post, reply, DM

### 5. Verify Installation

```bash
# Health check
curl http://127.0.0.1:9877/mcp/

# Test via MCP tool
mcp_patchright_browser_health profile=default

# List profiles
mcp_patchright_profile_list
```

### 6. Dashboard (Optional)

```bash
~/.patchright-browser/start-dashboard.sh
# Open http://localhost:9878 (password: hijilabs7)
```

## Quick Reference

```bash
# Start/stop
~/.patchright-browser/start.sh          # Start MCP server
~/.patchright-browser/start-dashboard.sh # Start dashboard

# Uninstall
bash uninstall.sh           # Remove everything
bash uninstall.sh --keep-data  # Keep profiles

# Profiles
mcp_patchright_profile_list              # List profiles
mcp_patchright_profile_create name=foo   # Create profile
mcp_patchright_profile_open name=foo     # Open browser
mcp_patchright_profile_close name=foo    # Close browser

# Browser automation
mcp_patchright_browser_navigate url=https://example.com profile=default
mcp_patchright_browser_snapshot profile=default
mcp_patchright_browser_click ref=e5 profile=default
mcp_patchright_browser_type ref=e10 text="hello" profile=default
mcp_patchright_browser_take_screenshot profile=default
mcp_patchright_browser_run_code code="async (page) => { return await page.title(); }" profile=default
```

## Architecture

```
AI Agent ──→ patchright-browser (port 9877) ──→ Chromium
             StreamableHTTP MCP               per profile
```

## Features

- **Multi-profile** — isolated browser contexts (cookies, sessions)
- **Multi-mode** — headed (GUI) + headless per profile simultaneously
- **MCP Protocol** — StreamableHTTP, works with any MCP client
- **Auto-detect GUI** — defaults to headed if display available
- **Dashboard** — password-protected web UI
- **Orphan cleanup** — kills stale Chromium on spawn

## Data Directory

```
~/.patchright-browser/
├── profiles/          # browser data (cookies, sessions)
├── profiles.json      # registry
├── configs/           # patchright config JSONs
├── thumbnails/        # screenshots
├── logs/              # bridge logs
├── bin/               # bridge scripts
├── lib/               # Python modules
├── dashboard.py       # web dashboard
├── start.sh           # bridge launcher
└── start-dashboard.sh # dashboard launcher
```

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_click` | Click element by ref |
| `browser_type` | Type text into element |
| `browser_snapshot` | Get accessibility tree |
| `browser_take_screenshot` | Capture screenshot |
| `browser_run_code` | Execute Playwright JS |
| `browser_tabs` | List/create/close tabs |
| `browser_press_key` | Press keyboard key |
| `browser_wait_for` | Wait for text/time |
| `browser_file_upload` | Upload files |
| `browser_console` | Get console output |
| `browser_evaluate` | Evaluate JS expression |
| `profile_list` | List all profiles |
| `profile_create` | Create new profile |
| `profile_open` | Spawn browser |
| `profile_close` | Kill browser |
| `profile_update` | Update profile fields |
| `profile_delete` | Delete profile |
| `proxy_add` | Add proxy config |
| `proxy_list` | List proxies |

## License

MIT
