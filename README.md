# Patchright Browser

MCP server yang memberikan AI agent browser sungguhan. Navigate, click, type, screenshot — semua via MCP protocol.

```
AI Agent ──→ patchright-browser ──→ Chromium
             (MCP protocol)       (multi-profile)
```

## Apa Ini?

Patchright Browser adalah MCP server yang memungkinkan AI agent (Hermes, Claude, Cursor, dll) mengontrol browser Chromium secara real. Agent bisa buka website, klik tombol, isi form, ambil screenshot, upload file — semua otomatis.

**Use cases:**
- Automasi social media (post, reply, DM)
- Scrape data dari website
- Automasi form submission
- Screenshot website untuk monitoring
- Multi-account management
- Browser-based research

## Fitur

### Multi-Profile
Setiap profile = browser terpisah (cookies, session, login berbeda). Bisa jalan beberapa profile sekaligus.

```
Profile "rickicode" → Login Instagram, Threads, X
Profile "work"      → Login Google, Slack
Profile "client-a"  → Login akun client
```

### Headed + Headless
- **Headed** — browser visible (GUI), bisa lihat apa yang terjadi
- **Headless** — invisible, cocok untuk server/automation
- Auto-detect: kalau ada display → headed, kalau tidak → headless

### MCP Protocol
Standar Model Context Protocol. Compatible dengan:
- Hermes Agent
- Claude Desktop
- Cursor
- Any MCP client

### Web Dashboard
Password-protected dashboard untuk manage profiles:
- List semua profiles + status online/offline
- Lihat active tabs per profile
- Monitor uptime, last used, viewport
- Login/logout dengan session cookies

### Skills (Automation Templates)
Skills siap pakai untuk common tasks:
- **x-search** — Cari & extract data dari X/Twitter
- **threads-search** — Cari & extract data dari Threads
- **instagram-automation** — Instagram DM, post, comment
- **threads-automation** — Threads post, reply, DM
- **x-automation** — X.com post, reply, DM

## Install

```bash
curl -sSL https://raw.githubusercontent.com/rickicode/patchright-browser/main/install.sh | bash
```

Atau manual:

```bash
git clone https://github.com/rickicode/patchright-browser.git
cd patchright-browser
bash install.sh
```

## Mulai

```bash
# Start MCP server
~/.patchright-browser/start.sh

# Start dashboard (opsional)
~/.patchright-browser/start-dashboard.sh
```

**MCP Server:** `http://127.0.0.1:9877/mcp/`
**Dashboard:** `http://localhost:9878` (password: `hijilabs7`)

## Konfigurasi MCP

Tambahkan ke config MCP client:

```yaml
# ~/.hermes/config.yaml
patchright:
  url: http://127.0.0.1:9877/mcp/
  connect_timeout: 30
  enabled: true
```

## MCP Tools

### Browser Control

| Tool | Fungsi |
|------|--------|
| `browser_navigate` | Buka URL |
| `browser_click` | Klik elemen |
| `browser_type` | Ketik text |
| `browser_snapshot` | Ambil accessibility tree |
| `browser_take_screenshot` | Screenshot halaman |
| `browser_run_code` | Jalankan JavaScript/Playwright |
| `browser_tabs` | Manage tabs (list/new/close/select) |
| `browser_press_key` | Tekan keyboard key |
| `browser_wait_for` | Tunggu text/time |
| `browser_file_upload` | Upload file |
| `browser_console` | Baca console output |
| `browser_evaluate` | Evaluate JavaScript |

### Profile Management

| Tool | Fungsi |
|------|--------|
| `profile_list` | List semua profiles |
| `profile_create` | Buat profile baru |
| `profile_open` | Buka browser untuk profile |
| `profile_close` | Tutup browser |
| `profile_update` | Update profile settings |
| `profile_delete` | Hapus profile |
| `profile_set_default` | Set default profile |
| `profile_inspect` | Deep state inspection |

### Proxy Management

| Tool | Fungsi |
|------|--------|
| `proxy_add` | Tambah proxy |
| `proxy_list` | List proxies |
| `proxy_get` | Detail proxy |
| `proxy_delete` | Hapus proxy |

## Contoh Penggunaan

### Buka website
```python
mcp_patchright_browser_navigate(url="https://example.com", profile="default")
```

### Klik tombol
```python
mcp_patchright_browser_snapshot(profile="default")  # ambil ref ID
mcp_patchright_browser_click(ref="e5", profile="default")
```

### Isi form
```python
mcp_patchright_browser_type(ref="e10", text="hello world", profile="default")
```

### Screenshot
```python
mcp_patchright_browser_take_screenshot(profile="default")
```

### Jalankan JavaScript
```python
mcp_patchright_browser_run_code(
    code="async (page) => { return await page.title(); }",
    profile="default"
)
```

### Extract data dari halaman
```python
mcp_patchright_browser_run_code(
    code="""async (page) => {
  return await page.evaluate(() => {
    const items = document.querySelectorAll('.item');
    return [...items].map(el => ({
      title: el.querySelector('h3')?.textContent,
      link: el.querySelector('a')?.href,
    }));
  });
}""",
    profile="default"
)
```

### Upload file
```python
mcp_patchright_browser_run_code(
    code="""async (page) => {
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.getByRole('button', { name: 'Upload' }).click()
  ]);
  await chooser.setFiles('/path/to/file.png');
}""",
    profile="default"
)
```

### Multi-tab
```python
# Buka tab baru
mcp_patchright_browser_tabs(action="new", profile="default")

# Switch tab
mcp_patchright_browser_tabs(action="select", index=1, profile="default")

# List tabs
mcp_patchright_browser_tabs(action="list", profile="default")
```

## Skills

Install skills untuk automasi common tasks:

```bash
cp -r skills/* ~/.hermes/skills/
```

### x-search
Cari & extract data dari X/Twitter:
```
cari di x tentang AI agent
search x "free credits" dengan filter:links
extract replies dari post tertentu
```

### threads-search
Cari & extract data dari Threads:
```
cari threads tentang startup AI
search threads "promo code" filter:recent
extract comments dari post
```

### instagram-automation
Instagram DM, post, comment, story:
```
kirim DM ke user di Instagram
post foto ke Instagram
comment di post Instagram
```

### threads-automation
Threads post, reply, DM:
```
post ke Threads
reply ke post Threads
DM di Threads
```

### x-automation
X.com post, reply, DM:
```
post tweet
reply ke tweet
DM di X
```

## Uninstall

```bash
bash ~/.patchright-browser/uninstall.sh           # hapus semua
bash ~/.patchright-browser/uninstall.sh --keep-data  # simpan profiles
```

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
