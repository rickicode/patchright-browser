# Patchright Browser

MCP server that gives AI agents a real browser. Navigate, click, type, screenshot — all via MCP protocol.

```
AI Agent ──→ patchright-browser ──→ Chromium
             (MCP protocol)       (multi-profile)
```

## What It Does

| Capability | Example |
|------------|---------|
| Navigate | Open any URL |
| Click | Click buttons, links, menus |
| Type | Fill forms, compose posts |
| Screenshot | Capture page visuals |
| Extract | Read page content via JS |
| Upload | Attach files to forms |
| Multi-tab | Manage multiple pages |
| Profiles | Isolated browser contexts |

## Install (one command)

```bash
curl -sSL https://raw.githubusercontent.com/rickicode/patchright-browser/main/install.sh | bash
```

Then start:

```bash
~/.patchright-browser/start.sh
```

Add to your MCP config:

```yaml
patchright:
  url: http://127.0.0.1:9877/mcp/
  connect_timeout: 30
  enabled: true
```

## Web Dashboard

```bash
~/.patchright-browser/start-dashboard.sh
```

Open `http://localhost:9878` (password: `hijilabs7`)

- View all browser profiles
- See online/offline status
- Check active tabs per profile
- Monitor uptime and last used

## Features

- **Multi-profile** — isolated cookies, sessions, logins per profile
- **Headed + headless** — GUI or invisible, per profile
- **MCP protocol** — works with Hermes, Claude, any MCP client
- **Auto GUI detect** — defaults to headed if display available
- **Orphan cleanup** — kills stale Chromium on spawn
- **Password-protected dashboard** — session cookies, 24h TTL

## Uninstall

```bash
bash ~/.patchright-browser/uninstall.sh
```

## License

MIT
