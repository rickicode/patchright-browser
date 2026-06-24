# Patchright Browser

MCP server for browser automation via [Patchright](https://github.com/nicobailey/patchright). Multi-profile, multi-mode (headed/headless), StreamableHTTP MCP protocol.

## Install

```bash
git clone https://github.com/YOUR_USER/patchright-browser.git
cd patchright-browser
bash install.sh
```

## Quick Start

```bash
# Start bridge
~/.patchright-browser/start.sh

# Start dashboard (password: hijilabs7)
~/.patchright-browser/start-dashboard.sh
```

**Bridge:** `http://127.0.0.1:9877/mcp/`
**Dashboard:** `http://localhost:9878`

## Uninstall

```bash
bash uninstall.sh           # remove everything
bash uninstall.sh --keep-data  # keep profiles
```

## Architecture

```
AI Agent (Hermes) ──→ patchright-browser (port 9877) ──→ Chromium
                   StreamableHTTP MCP                   per profile
```

## Features

- **Multi-profile** — isolated browser contexts (cookies, sessions)
- **Multi-mode** — headed (GUI) + headless per profile simultaneously
- **MCP Protocol** — StreamableHTTP, works with any MCP client
- **Auto-detect GUI** — defaults to headed if display available
- **Dashboard** — password-protected web UI for profile management
- **Orphan cleanup** — kills stale Chromium processes on spawn

## Profiles

```bash
# Create profile
mcp_patchright_profile_create name=myprofile caps=["vision"]

# Open browser
mcp_patchright_profile_open name=myprofile mode=headed

# List profiles
mcp_patchright_profile_list

# Delete profile
mcp_patchright_profile_delete name=myprofile
```

## Dashboard

Password-protected web UI at `http://localhost:9878`.

- List all profiles with status
- View active tabs per profile
- See uptime, last used, viewport, caps
- Login/logout with session cookies

Default password: `hijilabs7` (change in `dashboard.py`)

## Hermes Config

Add to `~/.hermes/config.yaml`:

```yaml
patchright:
  url: http://127.0.0.1:9877/mcp/
  connect_timeout: 30
  enabled: true
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_click` | Click element |
| `browser_type` | Type text |
| `browser_snapshot` | Get accessibility tree |
| `browser_take_screenshot` | Screenshot |
| `browser_run_code` | Execute Playwright JS |
| `browser_tabs` | List/create/close tabs |
| `browser_press_key` | Press keyboard key |
| `browser_wait_for` | Wait for text/time |
| `browser_file_upload` | Upload files |
| `profile_*` | Profile management |
| `proxy_*` | Proxy management |

## Skills

Hermes skills for common automation tasks:

| Skill | Description |
|-------|-------------|
| `x-search` | X.com search & data extraction |
| `threads-search` | Threads search & data extraction |
| `instagram-automation` | Instagram DM, post, story |
| `threads-automation` | Threads post, reply, DM |
| `x-automation` | X.com post, reply, DM |
| `promo-hunter` | AI startup promo scanning |

## Data Directory

```
~/.patchright-browser/
├── profiles/          # browser data (cookies, sessions)
│   ├── default/       # chromium data
│   └── default.json   # profile config
├── profiles.json      # registry
├── configs/           # patchright config JSONs
├── proxies.json       # proxy configurations
├── thumbnails/        # screenshots
├── logs/              # bridge logs
├── bin/               # bridge scripts
├── lib/               # Python modules
├── dashboard.py       # web dashboard
├── start.sh           # bridge launcher
└── start-dashboard.sh # dashboard launcher
```

## License

MIT
