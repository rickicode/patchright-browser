# patchright-browser

[![MCP](https://img.shields.io/badge/MCP-StreamableHTTP-blue)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP server for browser automation via Chromium. Multi-profile, headed/headless, StreamableHTTP protocol.

## Install for AI Agents

AI agents can auto-install by running:

```bash
git clone https://github.com/rickicode/patchright-browser.git ~/.patchright-browser/repo && cd ~/.patchright-browser/repo && bash install.sh
```

Or add to your MCP config directly:

```json
{
  "mcpServers": {
    "patchright": {
      "url": "http://127.0.0.1:9877/mcp/",
      "connectTimeout": 30000
    }
  }
}
```

## Install for Humans

```bash
# Clone
git clone https://github.com/rickicode/patchright-browser.git
cd patchright-browser

# Install
bash install.sh

# Start
~/.patchright-browser/start.sh
```

Server: `http://127.0.0.1:9877/mcp/`

## MCP Config

### Hermes

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  patchright:
    url: http://127.0.0.1:9877/mcp/
    connect_timeout: 30
    enabled: true
```

### Claude Desktop

```json
{
  "mcpServers": {
    "patchright": {
      "url": "http://127.0.0.1:9877/mcp/"
    }
  }
}
```

### Cursor / VS Code

```json
{
  "mcp": {
    "servers": {
      "patchright": {
        "type": "http",
        "url": "http://127.0.0.1:9877/mcp/"
      }
    }
  }
}
```

## Tools

### Browser

| Tool | Description |
|------|-------------|
| `browser_navigate` | Open URL |
| `browser_click` | Click element by ref |
| `browser_type` | Type text into element |
| `browser_snapshot` | Get page structure |
| `browser_take_screenshot` | Capture screenshot |
| `browser_run_code` | Execute Playwright JS |
| `browser_tabs` | Manage tabs |
| `browser_press_key` | Press keyboard key |
| `browser_wait_for` | Wait for text/time |
| `browser_file_upload` | Upload file |
| `browser_console` | Read console |
| `browser_evaluate` | Run JavaScript |

### Profiles

| Tool | Description |
|------|-------------|
| `profile_list` | List all profiles |
| `profile_create` | Create profile |
| `profile_open` | Start browser |
| `profile_close` | Stop browser |
| `profile_update` | Update settings |
| `profile_delete` | Delete profile |

### Proxy

| Tool | Description |
|------|-------------|
| `proxy_add` | Add proxy |
| `proxy_list` | List proxies |
| `proxy_delete` | Remove proxy |

## Usage

```python
# Open page
mcp_patchright_browser_navigate(url="https://example.com")

# Get page structure
mcp_patchright_browser_snapshot()

# Click element
mcp_patchright_browser_click(ref="e5")

# Type text
mcp_patchright_browser_type(ref="e10", text="hello")

# Take screenshot
mcp_patchright_browser_take_screenshot()

# Run JavaScript
mcp_patchright_browser_run_code(
    code="async (page) => await page.title()"
)
```

## Profiles

Isolated browser contexts with separate cookies/sessions.

```python
# Create profile
mcp_patchright_profile_create(name="work", caps=["vision"])

# Open browser
mcp_patchright_profile_open(name="work", mode="headed")

# Use profile
mcp_patchright_browser_navigate(url="https://example.com", profile="work")

# Close
mcp_patchright_profile_close(name="work")
```

## Dashboard

Web UI for managing profiles.

```bash
~/.patchright-browser/start-dashboard.sh
# http://localhost:9878 (password: hijilabs7)
```

## Skills

Install Hermes skills for social media automation:

```bash
cp -r skills/* ~/.hermes/skills/
```

| Skill | Description |
|-------|-------------|
| `x-search` | Search & extract X/Twitter data |
| `threads-search` | Search & extract Threads data |
| `instagram-automation` | Instagram DM, post, comment |
| `threads-automation` | Threads post, reply, DM |
| `x-automation` | X.com post, reply, DM |

## Uninstall

```bash
bash ~/.patchright-browser/uninstall.sh
```

## License

MIT
