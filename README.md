# Patchright Browser MCP Server

[![MCP](https://img.shields.io/badge/MCP-StreamableHTTP-blue)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Browser automation MCP server. Gives AI agents a real Chromium browser — navigate, click, type, screenshot, extract data.

## Quick Start

### Claude Code
```sh
claude mcp add patchright http://127.0.0.1:9877/mcp/ --transport http
```

### Claude Desktop
Add to `~/.claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "patchright": {
      "url": "http://127.0.0.1:9877/mcp/"
    }
  }
}
```

### Cursor
Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "patchright": {
      "type": "http",
      "url": "http://127.0.0.1:9877/mcp/"
    }
  }
}
```

### Hermes Agent
Add to `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  patchright:
    url: http://127.0.0.1:9877/mcp/
    connect_timeout: 30
    enabled: true
```

### Codex
Settings > MCP Servers > Add server > Streamable HTTP > `http://127.0.0.1:9877/mcp/`

## Install Server

### For AI Agents (auto-install)

Run this command:
```bash
git clone https://github.com/rickicode/patchright-browser.git ~/.patchright-browser/repo && cd ~/.patchright-browser/repo && bash install.sh && ~/.patchright-browser/start.sh
```

### For Humans

```bash
git clone https://github.com/rickicode/patchright-browser.git
cd patchright-browser
bash install.sh
~/.patchright-browser/start.sh
```

### Verify

```bash
curl http://127.0.0.1:9877/mcp/
```

## Tools (27)

### Browser Automation

| Tool | Description | Example |
|------|-------------|---------|
| `browser_navigate` | Open URL | `url="https://example.com"` |
| `browser_click` | Click element | `ref="e5"` |
| `browser_type` | Type text | `ref="e10", text="hello"` |
| `browser_snapshot` | Get page structure | — |
| `browser_take_screenshot` | Capture image | — |
| `browser_run_code` | Execute Playwright JS | `code="async (page) => ..."` |
| `browser_tabs` | Manage tabs | `action="list\|new\|close\|select"` |
| `browser_press_key` | Keyboard input | `key="Enter"` |
| `browser_wait_for` | Wait condition | `text="Loaded"` or `time=5` |
| `browser_file_upload` | Attach file | `paths=["/path/file.png"]` |
| `browser_console` | Read console | — |
| `browser_evaluate` | Run JavaScript | `expression="document.title"` |
| `browser_hover` | Hover element | `ref="e5"` |
| `browser_drag` | Drag and drop | `startRef, endRef` |

### Profile Management

| Tool | Description |
|------|-------------|
| `profile_list` | List all browser profiles |
| `profile_create` | Create new profile |
| `profile_open` | Start browser for profile |
| `profile_close` | Stop browser |
| `profile_update` | Change settings |
| `profile_delete` | Remove profile |
| `profile_set_default` | Set default profile |
| `profile_inspect` | Deep state inspection |

### Proxy

| Tool | Description |
|------|-------------|
| `proxy_add` | Add proxy config |
| `proxy_list` | List proxies |
| `proxy_delete` | Remove proxy |

## Usage Examples

### Extract data from a page
```python
result = mcp_patchright_browser_run_code(code="""async (page) => {
  return await page.evaluate(() => {
    const items = document.querySelectorAll('.item');
    return [...items].map(el => ({
      title: el.querySelector('h3')?.textContent,
      url: el.querySelector('a')?.href,
    }));
  });
}""")
```

### Fill and submit a form
```python
mcp_patchright_browser_type(ref="e5", text="John Doe")
mcp_patchright_browser_type(ref="e8", text="john@example.com")
mcp_patchright_browser_click(ref="e12")  # submit button
```

### Take screenshot
```python
mcp_patchright_browser_take_screenshot()
```

### Multi-tab workflow
```python
mcp_patchright_browser_tabs(action="new")
mcp_patchright_browser_navigate(url="https://site2.com")
mcp_patchright_browser_tabs(action="select", index=0)
```

## Profiles

Each profile = isolated browser with separate cookies, sessions, logins.

```python
# Create
mcp_patchright_profile_create(name="work", caps=["vision"])

# Use
mcp_patchright_profile_open(name="work", mode="headed")
mcp_patchright_browser_navigate(url="https://example.com", profile="work")

# Cleanup
mcp_patchright_profile_close(name="work")
```

## Dashboard

Web UI for profile management.

```bash
~/.patchright-browser/start-dashboard.sh
# http://localhost:9878 (password: hijilabs7)
```

## Skills

Hermes Agent skills for social media automation:

```bash
cp -r skills/* ~/.hermes/skills/
```

| Skill | What it does |
|-------|-------------|
| `x-search` | Search X/Twitter, extract posts + replies |
| `threads-search` | Search Threads, extract posts + comments |
| `instagram-automation` | Instagram DM, post, comment, story |
| `threads-automation` | Threads post, reply, DM |
| `x-automation` | X.com post, reply, DM |

## Uninstall

```bash
bash ~/.patchright-browser/uninstall.sh
```

## License

MIT
