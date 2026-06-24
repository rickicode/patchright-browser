---
name: instagram-automation
description: "Instagram automation via Patchright MCP — DM, like, comment, search, profile, get images. Browser-based (not API). Part of social-media-browser umbrella."
triggers:
  - "instagram"
  - "dm instagram"
  - "like post ig"
  - "komentar instagram"
  - "cari user instagram"
  - "baca pesan ig"
  - "kirim pesan ig"
  - "profil instagram"
  - "get images instagram"
tools:
  - mcp_patchright_browser_navigate
  - mcp_patchright_browser_click
  - mcp_patchright_browser_type
  - mcp_patchright_browser_snapshot
  - mcp_patchright_browser_run_code
  - mcp_patchright_browser_file_upload
  - mcp_patchright_browser_take_screenshot
---

# Instagram Automation via Patchright MCP

## Prerequisites
- Patchright profile must be **already logged in** to Instagram (headed mode recommended)
- Use `profile="rickicode"` (default) or whichever profile has IG session
- All interactions use `mcp_patchright_*` tools

## Key Patterns

### Language Notes
Instagram UI is in **Bahasa Indonesia**. Button/label names:
- Like = "Suka" / Unlike = "Batal Suka"
- Comment = "Komentari" → input: "Tambahkan komentar…"
- Send DM = textbox "Kirim pesan..." → press Enter
- Search = "Cari" (explore page has textbox)
- Follow = "Ikuti" / Unfollow = "Berhenti Mengikuti"
- Share = "Bagikan"
- Save = "Simpan"

---

## 1. DM — Read Messages

```
Navigate: https://www.instagram.com/direct/inbox/
```

**Inbox structure:**
- Left sidebar: list of conversations as buttons
- Each button shows: profile pic, name, last message preview, timestamp
- Unread badge: "Unread" text element
- Search DM contacts: textbox "Cari" at top of sidebar

**Open a conversation:**
- Click the conversation button (e.g., button containing "Retno")
- URL changes to `/direct/t/<thread_id>/`

**Read messages in thread:**
- Messages are in `group` elements with timestamps
- Each message has: sender profile pic link, content text/image
- Own messages show "Anda:" prefix in inbox preview
- Message types: text, "Klip" (shared reel), image attachment ("mengirim lampiran")

**Get message history via run_code:**
```js
async (page) => {
  const msgs = await page.evaluate(() => {
    const groups = document.querySelectorAll('[role="group"]');
    return [...groups].map(g => ({
      text: g.innerText?.substring(0, 200),
      time: g.closest('[data-testid]')?.querySelector('time')?.textContent
    }));
  });
  return msgs;
}
```

---

## 2. DM — Send Text Message

```
Navigate: https://www.instagram.com/direct/t/<thread_id>/
```

**Method 1 — snapshot + type:**
1. `snapshot` → find textbox ref (usually labeled "Kirim pesan..." or empty textbox)
2. `type(ref=..., text="pesan", submit=true)` — Enter sends the message

**Method 2 — run_code (more reliable):**
```js
async (page) => {
  const box = page.getByPlaceholder('Kirim pesan');
  await box.click();
  await box.fill('pesan kamu');
  await box.press('Enter');
  return 'sent';
}
```

**Verify sent:** After send, the message appears in the chat with "Anda:" prefix in sidebar.

---

## 3. DM — Send Image/Photo

**Steps:**
1. Navigate to DM thread
2. Click "Tambahkan Foto atau Video" button
3. File chooser opens → use `file_upload` with local file path
4. Image preview appears with "Hapus lampiran: <filename>" and "Kirim" button
5. Click "Kirim" to send

**Important:** File must be in allowed workspace directory (e.g., `/workspaces/`).
If image is from internet, download it to workspace first via `terminal` (curl/wget).

**run_code approach (reliable):**
```js
async (page) => {
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.getByRole('button', { name: /Tambahkan Foto atau Video/ }).click()
  ]);
  await fileChooser.setFiles('/path/to/image.jpg');
  await page.waitForTimeout(2000);
  // Now click Kirim
  await page.getByRole('button', { name: 'Kirim' }).click();
  await page.waitForTimeout(1000);
  return 'image sent';
}
```

---

## 4. Like / Unlike Post

**From feed or post page:**
1. Find "Suka" button (heart icon) → click to like
2. Button changes to "Batal Suka" (filled heart) when liked
3. Click "Batal Suka" to unlike

**Identify by ref:** In snapshot, look for `button "Suka"` or `button "Batal Suka"`.

**From post modal (after clicking comment):**
- Same pattern, button labeled "Batal Suka" if already liked

---

## 5. Comment on Post

**Open post detail first:**
- Navigate to post URL: `https://www.instagram.com/p/<shortcode>/`
- Or click "Komentari" button from feed → opens post modal

**Add comment:**
1. Find textbox "Tambahkan komentar…"
2. Type comment + Enter

**run_code approach (most reliable):**
```js
async (page) => {
  const box = page.getByPlaceholder('Tambahkan komentar');
  await box.click();
  await box.fill('komentar kamu');
  await box.press('Enter');
  await page.waitForTimeout(1000);
  return 'commented';
}
```

**Delete own comment:**
1. Navigate to the post
2. Find your comment in the list
3. Click the "…" (more options) button next to your comment
4. Click "Hapus" (Delete)
5. Confirm deletion

---

## 6. Search Users / Posts

**Navigate to explore:** `https://www.instagram.com/explore/`

**Search flow:**
1. `snapshot` → find textbox "Cari Input" (ref)
2. `type(ref, text="search term")` — results appear as dropdown
3. `snapshot` → results show as links with format:
   - `link "Foto profil <username> <username> <display name> • <bio/followers>"`
   - URL: `/<username>/`

**Direct profile URL:** `https://www.instagram.com/<username>/`

---

## 7. View Profile + List Posts

**Navigate:** `https://www.instagram.com/<username>/`

**Extract profile data via run_code:**
```js
async (page) => {
  await page.waitForTimeout(3000);
  return await page.evaluate(() => {
    const result = {};
    result.name = document.querySelector('header h2')?.textContent;
    
    // Stats: posts, followers, following
    const spans = document.querySelectorAll('header span, header li span');
    result.stats = [...spans].map(s => s.textContent?.trim()).filter(t => t && t.length < 30).slice(0, 10);
    
    // Posts grid
    const postLinks = document.querySelectorAll('a[href*="/p/"]');
    result.posts = [...postLinks].slice(0, 12).map(a => ({
      url: a.href,
      alt: a.querySelector('img')?.alt?.substring(0, 100) || '',
      thumbnail: a.querySelector('img')?.src?.substring(0, 150) || ''
    }));
    
    return result;
  });
}
```

**Post URL pattern:** `https://www.instagram.com/p/<shortcode>/`
**Reel URL pattern:** `https://www.instagram.com/<username>/reel/<shortcode>/`

**Profile tabs:**
- Postingan (default grid)
- Reels → `/<username>/reels/`
- Postingan ulang → `/<username>/reposts/`
- Ditandai (tagged) → `/<username>/tagged/`

---

## 8. Get Images from Post

**From profile grid (thumbnails):**
```js
async (page) => {
  return await page.evaluate(() => {
    const imgs = document.querySelectorAll('a[href*="/p/"] img');
    return [...imgs].map(img => ({
      src: img.src,
      alt: img.alt?.substring(0, 100)
    }));
  });
}
```

**From post detail page:**
```js
async (page) => {
  await page.goto('https://www.instagram.com/p/<shortcode>/');
  await page.waitForTimeout(2000);
  return await page.evaluate(() => {
    const imgs = document.querySelectorAll('article img[src*="cdninstagram"]');
    return [...imgs].map(i => i.src);
  });
}
```

**Note:** CDN URLs are session-bound and expire. To save images:
1. Get the `src` URL from the page
2. Use `page.request.get(url)` in run_code (has session cookies)
3. Or take a screenshot with `take_screenshot`

---

## 9. Share Post via DM

1. Open post (navigate to URL or click from feed)
2. Click "Bagikan" button
3. Search/select recipient in the share dialog
4. Click "Kirim" to share

---

## 10. Follow / Unfollow

**From profile page:**
- "Ikuti" = Follow
- "Mengikuti" = Following (hover shows "Berhenti Mengikuti" to unfollow)

---

## 11. View Story Highlights

**Navigate to profile:** `https://www.instagram.com/<username>/`

**List all highlights:**
```js
async (page) => {
  return await page.evaluate(() => {
    return [...document.querySelectorAll('a[href*="/stories/highlights/"]')].map(a => ({
      name: a.innerText.trim(),
      href: a.getAttribute('href'),
      id: a.getAttribute('href').match(/highlights\/(\d+)/)?.[1]
    }));
  });
}
```

**Open a specific highlight:**
```
navigate: https://www.instagram.com/stories/highlights/<ID>/
```

**Handle "Lihat Cerita" confirmation popup:**
Instagram shows a confirmation: "Lihat sebagai <username>?" → must click "Lihat Cerita" button.
```js
async (page) => {
  const btn = page.get_by_role("button", name="Lihat Cerita");
  if (await btn.count() > 0) {
    await btn.click();
    await page.waitForTimeout(5000);
  }
}
```

**Navigate through story slides:**
Stories auto-advance, but you can also click the right side of the screen:
```js
async (page) => {
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(3000);
    // Capture current state
    const info = await page.evaluate(() => ({
      hasVideo: !!document.querySelector('video'),
      text: document.body.innerText.substring(0, 200)
    }));
    // Advance
    await page.mouse.click(750, 350);
    await page.waitForTimeout(1500);
    if (!page.url.includes('stories')) break; // story ended
  }
}
```

**Story metadata (music, timestamp):**
The story viewer shows: highlight name, posting time ("151 ming"), and music info ("Gita Gutawa · Harmony Cinta") in the body text.

**Download story videos:** See `references/instagram-story-video-extraction.md` for the full workflow (GraphQL interception → cookies → curl download).

---

## Pitfalls

1. **Ref staleness**: After any navigation or page change, refs expire. Always `snapshot` fresh before clicking.
2. **Comment input**: `type(ref, submit=true)` may timeout on comment fields. Use `run_code` with `getByPlaceholder('Tambahkan komentar')` instead.
3. **File upload path**: Files must be in workspace directory (`/workspaces/`). Download external files there first.
4. **CDN image URLs**: Instagram CDN URLs expire and are session-bound. Use `page.request.get()` in run_code to download with cookies.
5. **Rate limiting**: Rapid actions may trigger "Try Again Later". Add `waitForTimeout(2000)` between actions.
6. **Language**: UI is Bahasa Indonesia. Use Indonesian labels ("Suka", "Komentari", "Kirim pesan", "Cari").
7. **Modal vs page**: Comment and share actions open modals/overlays. Close with "Tutup" button when done.
8. **CRUD completeness**: When testing any action (like, comment, follow), ALWAYS test the reverse (unlike, delete comment, unfollow). User requires full CRUD coverage.
9. **Story viewer "Lihat Cerita" button**: When viewing highlights/stories while logged in, Instagram shows a confirmation popup: "Lihat sebagai <username>?" with a "Lihat Cerita" button. Must click this button before the story actually plays. Use `page.get_by_role("button", name="Lihat Cerita")`.
10. **Story videos use blob URLs + MSE**: Instagram stories stream video via Media Source Extensions (blob: URLs). The actual video data comes from CDN URLs fetched via GraphQL. To download story videos: (a) intercept GraphQL responses for `video_url` fields, (b) save browser cookies early, (c) download CDN URLs via curl with cookies. See `references/instagram-story-video-extraction.md` for full workflow.
11. **Story context auto-closes**: After all story slides play, the browser context may auto-close. Wrap `await browser.close()` in try/except. Save data (cookies, URLs) incrementally during playback, not after.
12. **Highlight links**: Instagram highlights are `<a>` elements with `href="/stories/highlights/<ID>/"`. The text content is the highlight name (may include emoji). List all: `document.querySelectorAll('a[href*="/stories/highlights/"]')`.
