# AGENTS.md — Instructions for AI Agents

This file helps AI agents understand and use the patchright-browser project.

## What Is This?

A browser automation MCP server. You can control Chromium browsers via MCP tools.

## How To Install

```bash
git clone https://github.com/rickicode/patchright-browser.git
cd patchright-browser && bash install.sh
~/.patchright-browser/start.sh
```

## How To Add MCP Server

```yaml
# In your MCP config:
patchright:
  url: http://127.0.0.1:9877/mcp/
  connect_timeout: 30
  enabled: true
```

## How To Use

All tools use the `profile` parameter. Default profile is "default".

```python
# Navigate
mcp_patchright_browser_navigate(url="https://example.com", profile="default")

# Get page structure
mcp_patchright_browser_snapshot(profile="default")

# Click element
mcp_patchright_browser_click(ref="e5", profile="default")

# Type text
mcp_patchright_browser_type(ref="e10", text="hello world", profile="default")

# Screenshot
mcp_patchright_browser_take_screenshot(profile="default")

# Run JavaScript
mcp_patchright_browser_run_code(
    code="async (page) => { return await page.title(); }",
    profile="default"
)
```

## Profiles

Each profile = isolated browser (separate cookies, sessions).

```python
# List profiles
mcp_patchright_profile_list()

# Create profile
mcp_patchright_profile_create(name="myprofile", caps=["vision"])

# Open browser
mcp_patchright_profile_open(name="myprofile", mode="headed")

# Close browser
mcp_patchright_profile_close(name="myprofile")
```

## Common Patterns

### Extract data from page
```python
result = mcp_patchright_browser_run_code(code="""async (page) => {
  return await page.evaluate(() => {
    const items = document.querySelectorAll('.item');
    return [...items].map(el => ({
      title: el.querySelector('h3')?.textContent,
      link: el.querySelector('a')?.href,
    }));
  });
}""", profile="default")
```

### Upload file
```python
# First click the upload button to trigger file chooser
mcp_patchright_browser_run_code(code="""async (page) => {
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.getByRole('button', { name: 'Upload' }).click()
  ]);
  await chooser.setFiles('/path/to/file.png');
}""", profile="default")
```

### Multi-tab
```python
# Open new tab
mcp_patchright_browser_tabs(action="new", profile="default")

# Switch tab
mcp_patchright_browser_tabs(action="select", index=1, profile="default")

# List tabs
mcp_patchright_browser_tabs(action="list", profile="default")
```

## Skills

Install skills for common tasks:
```bash
cp -r skills/* ~/.hermes/skills/
```

Then use natural language:
- "cari di x tentang AI agent"
- "search threads tentang startup"
- "post ke threads tentang promo"
