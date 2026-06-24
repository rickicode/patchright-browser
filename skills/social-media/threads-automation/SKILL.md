---
name: threads-automation
description: "Threads (threads.com) automation via Patchright MCP — post, reply, like, repost, DM, search, profile. Column-based web UI, English. Part of social-media-browser umbrella."
triggers:
  - "threads"
  - "threads.net"
  - "post threads"
  - "reply threads"
  - "like threads"
  - "dm threads"
  - "repost threads"
  - "search threads"
  - "profil threads"
  - "utas"
tools:
  - mcp_patchright_browser_navigate
  - mcp_patchright_browser_click
  - mcp_patchright_browser_type
  - mcp_patchright_browser_snapshot
  - mcp_patchright_browser_run_code
  - mcp_patchright_browser_file_upload
  - mcp_patchright_browser_take_screenshot
---

# Threads Automation via Patchright MCP

## Prerequisites
- Patchright profile must be **already logged in** to Threads (threads.com)
- Use `profile="rickicode"` (default) or whichever profile has Threads session
- All interactions use `mcp_patchright_*` tools
- Threads shares Instagram auth — same profile works for both

## Architecture: Column-Based Layout

Threads uses a **multi-column layout** (like TweetDeck):
- **Left sidebar**: Navigation (fixed)
- **Center area**: One or more columns (feed, profile, post detail, search, messages)
- Each column has its own `Column title` (h1), `Column body` (region), and `More` button
- Columns can be stacked — navigate opens new column, "Back" button closes it

**Key difference from Instagram:**
- English UI throughout (Like, Reply, Repost, Share, Follow, Post, Message)
- Posts are called "threads"
- No "Suka/Komentari" — it's "Like/Reply"
- Column-based, not page-based
- URL pattern: `threads.com/@username/post/<shortcode>`

---

## 1. Create Post (New Thread)

### Method 1 — Sidebar "New thread" button
1. Click sidebar button `button "New thread"`
2. Compose modal/panel opens

### Method 2 — Inline compose in feed
1. In feed column, find `button "Empty text field. Type to compose a new post."`
2. Click to focus, type content
3. Click `button "Post"` to publish

### Method 3 — run_code (most reliable)
```js
async (page) => {
  await page.goto('https://www.threads.com/');
  await page.waitForTimeout(3000);
  
  // Click compose area
  const compose = page.getByRole('button', { name: /Empty text field|What\'s new/ });
  await compose.click();
  await page.waitForTimeout(500);
  
  // Type content
  await page.keyboard.type('Your thread text here');
  await page.waitForTimeout(500);
  
  // Click Post
  const postBtn = page.getByRole('button', { name: 'Post' });
  await postBtn.click();
  await page.waitForTimeout(2000);
  
  return 'posted';
}
```

### Create button (bottom sidebar)
- `button "Create"` at bottom of left sidebar — also opens compose

---

## 1b. Post with Image (Patchright file upload)

```js
async (page) => {
  // 1. Open composer
  await page.getByRole('button', { name: 'New thread' }).click({ force: true });
  await page.waitForTimeout(2000);

  // 2. Trigger file chooser + upload
  const [fileChooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.getByRole('button', { name: 'Attach media' }).click()
  ]);
  await fileChooser.setFiles('/workspaces/patchright-browser/image.png');
  await page.waitForTimeout(3000);

  // 3. DUPLICATE CHECK — Threads sometimes uploads 2 copies!
  const removeButtons = page.getByRole('button', { name: 'Remove' });
  if (await removeButtons.count() > 1) {
    await removeButtons.first().click();
    await page.waitForTimeout(500);
  }

  // 4. Type text (under 500 chars!)
  const textbox = page.getByRole('textbox', { name: 'Empty text field. Type to' });
  await textbox.click();
  await textbox.fill('Your post text here');

  // 5. Post
  await page.getByRole('button', { name: 'Post', exact: true }).click();
  await page.waitForTimeout(3000);
  return 'posted';
}
```

**Pitfall — file path**: Patchright only allows files from `/workspaces/patchright-browser/`. Copy files there first:
```bash
cp /tmp/screenshot.png /workspaces/patchright-browser/screenshot.png
```

---

## 2. Like / Unlike Post

**From feed or post detail:**
1. Find `button "Like N"` (where N is count, e.g., "Like 36")
2. Click to like — button stays "Like N+1"
3. Click again to unlike

**Identify in snapshot:**
- Like button: `button "Like36"` or `button "Like 36"` (count may be attached)
- Liked state: count increases by 1

**run_code approach:**
```js
async (page) => {
  // Find the Like button near a specific post
  const likeBtn = page.getByRole('button', { name: /^Like/ }).first();
  await likeBtn.click();
  await page.waitForTimeout(500);
  return 'liked';
}
```

---

## 4. Reply to Post

**From feed:**
1. Click `button "Reply"` or `button "Reply N"` on a post
2. Reply compose opens (may open post detail column)
3. Type reply in the textbox
4. Click `button "Post"` to send reply

**From post detail page:**
1. Navigate to `/@username/post/<shortcode>`
2. Find compose area (`textbox "Empty text field. Type to compose a new post."` with placeholder "Reply to username...")
3. Type reply + click "Post"
4. Compose also has: `button "Attach media"`, `button "Add a GIF"`, `button "Expand composer"`

**Reply sorting:**
- `button "Sort Top More"` — sort replies by Top/Recent

**Reply thread structure:**
- Replies show: profile pic, username, timestamp, "Author" badge (if post author), "Liked by original author" indicator
- Each reply has action bar: Like, Reply, Repost, Share
- Each reply has "More" button (⋯) with same options as other user's posts

**run_code approach:**
```js
async (page) => {
  // Navigate to post
  await page.goto('https://www.threads.com/@username/post/SHORTCODE');
  await page.waitForTimeout(3000);
  
  // Click compose
  const compose = page.getByRole('button', { name: /Empty text field/ });
  await compose.click();
  await page.waitForTimeout(500);
  
  // Type reply
  await page.keyboard.type('Your reply here');
  await page.waitForTimeout(500);
  
  // Post
  await page.getByRole('button', { name: 'Post' }).click();
  await page.waitForTimeout(2000);
  return 'replied';
}
```

---

## 3. Repost / Quote Repost

**Repost:**
1. Click `button "Repost"` or `button "Repost N"` on a post
2. Confirm repost in dialog (if any)

**Quote Repost (repost with comment):**
1. Click "Repost" → select "Quote" option
2. Add your text + click "Post"

---

## 5. Share Post

- Click `button "Share"` or `button "Share N"`
- Opens share dialog (copy link, send via DM, etc.)

---

## 6. Post "More" Menu Options

### Own Post Menu (`button "More"` on your post)
Click "More" button on your own post → opens menu with:

**Group 1:**
- `menuitem "Insights"` → view post analytics

**Group 2:**
- `menuitem "Save"` → bookmark the post
- `menuitem "Pin to profile"` → pin to top of profile
- `menuitem "Archive"` → hide from profile (not delete)
- `menuitem "Hide like and share counts"` → hide engagement numbers
- `menuitem "Reply options"` → control who can reply

**Group 3:**
- `menuitem "Delete"` → delete the post permanently

**Group 4:**
- `menuitem "Copy link"` → copy post URL

### Other User's Post Menu (`button "More"` on their post)
Click "More" button on other user's post → opens menu with:

**Group 1:**
- `menuitem "Add to feed"` (submenu with "Next" arrow)

**Group 2:**
- `menuitem "Save"` → bookmark
- `menuitem "Not interested"` → hide similar content

**Group 3:**
- `menuitem "Mute"` → mute the user
- `menuitem "Notify me"` → notifications for this post
- `menuitem "Restrict"` → restrict their interactions
- `menuitem "Unfollow"` → unfollow the user
- `menuitem "Report"` → report the post

**Group 4:**
- `menuitem "Copy link"` → copy post URL

**run_code to click menu item:**
```js
async (page) => {
  // Click More button on post
  await page.evaluate(() => {
    const btns = document.querySelectorAll('button');
    for (const btn of btns) {
      const img = btn.querySelector('img[alt="More"]');
      if (img && btn.closest('[role="region"]')) {
        btn.click();
        return;
      }
    }
  });
  await page.waitForTimeout(1000);
  
  // Click specific menu item (e.g., Delete)
  const deleteItem = page.getByRole('menuitem', { name: 'Delete' });
  await deleteItem.click();
  await page.waitForTimeout(1000);
  
  // Confirm if dialog appears
  const confirmBtn = page.getByRole('button', { name: /Delete|Confirm/ });
  if (await confirmBtn.isVisible()) {
    await confirmBtn.click();
  }
  
  return 'deleted';
}
```

---

## 7. DM (Direct Messages)

### Inbox
```
Navigate: https://www.threads.com/messages/
```

**Structure:**
- Header: "Messages" button + "New message" link
- Search box for messages
- Tabs: "Inbox" / "Requests" (with unread count)
- Conversation list: each is a `link` with:
  - Profile picture
  - Username
  - Last message preview
  - Timestamp (16h, 1w, 4w, 9w, 12w)
- URL pattern: `/messages/t/<thread_id>/`

### Read Messages
```
Navigate: https://www.threads.com/messages/t/<thread_id>/
```

**Conversation structure:**
- Header: profile pic, username, display name, followers count, "View profile" link, "Follow" button
- Messages in `grid` layout with timestamps
- Each message: profile pic link, text, action buttons (3 buttons: reply/react/more)
- "Seen" indicator for last message
- Input: `textbox "Message..."` + attachment/media buttons

### Send DM
```js
async (page) => {
  await page.goto('https://www.threads.com/messages/t/<thread_id>/');
  await page.waitForTimeout(3000);
  
  // Find message input (contenteditable div with role="textbox")
  const input = page.locator('[role="textbox"][contenteditable="true"]');
  await input.click();
  await input.fill('Your message');
  await input.press('Enter');
  
  return 'sent';
}
```

### DM Message Actions
Each message has 3 action buttons in a `gridcell`:
1. **Reply** (no label, first button) — reply to specific message
2. **React** (no label, second button) — add emoji reaction
3. **More** (label "More", third button) — more options menu

**Note:** Buttons only appear on hover. Use `force: true` click or hover first.

### DM Input Area Buttons
- `button "More options"` — attachment/media options
- `button "Add an emoji"` — emoji picker
- `textbox` (contenteditable, placeholder "Message...") — message input

### DM Inbox Conversation Options
Each conversation in inbox has `svg "More options for conversation"` — options for that conversation (mute, archive, delete, etc.)

### DM Requests
```
Navigate: https://www.threads.com/messages/requests
```
- Shows message requests from non-followers
- Accept or decline requests

### Send New DM
```
Navigate: https://www.threads.com/messages/new/
```
- Search for user → select → compose message → send

---

## 7. Search

```
Navigate: https://www.threads.com/search
```

**Structure:**
- Search box (`searchbox "Search"`)
- "Filter" button
- "Follow suggestions" section with user cards
- Each suggestion: profile pic, username link, display name, "Follow" button, follower count

**Search flow:**
1. Navigate to `/search`
2. Type in `searchbox "Search"` (type=search, placeholder="Search")
3. Results appear inline in column

**Filter tabs** (appear after query entered):
- `link "Top"` → `/search?q={term}` (default, best match)
- `link "Recent"` → `/search?q={term}&filter=recent` (chronological)
- `link "Profiles"` → `/search?q={term}&filter=profiles` (users only)

**Filter button:** `button "Filter"` (icon, next to search box)

**Search with query:**
```
Navigate: https://www.threads.com/search?q=<query>
```

**Search specific author's posts:**
```
Navigate: https://www.threads.com/search?from_author=<username>
```

**Tag search:**
```
Navigate: https://www.threads.com/search?q=<tag>&serp_type=tags&tag_id=<id>
```

**Result types:**

*Post results* (Top/Recent filters):
- Profile pic button with "Follow" overlay
- Username link → /@username
- Optional tag badges (hashtag icon + tag link)
- Timestamp link → /@username/post/<postId>
- "More" button (⋯)
- Post text content
- Optional "Translate" button (non-English)
- Optional media (image link to /@username/post/<postId>/media)
- Optional link preview card (og:image + domain + title)
- Action bar: Like N, Reply N, Repost N, Share N

*Profile results* (Profiles filter):
- Grid layout: 4 profiles per row (profile pic, Follow button, username, display name)
- List layout below: profile pic, username, display name, bio snippet, Follow button
- Each has follower count

*Follow suggestions* (empty search):
- Section heading "Follow suggestions"
- Each: profile pic, username link, display name, "Follow" button, follower count, bio

**Note:** Exact username match auto-redirects to profile page.

---

## 8. Profile

```
Navigate: https://www.threads.com/@<username>
```

**Structure:**
- Column title: username with `link "Search posts from username"` → `/search?from_author=<username>` + `button "More"` (⋯)
- Profile info:
  - Display name (h1)
  - Username
  - Bio text
  - Link (redirect via l.threads.com)
  - Tags/interests (clickable, e.g., "AI Threads", "Coding", "saham", "programming") with `button "+"` to add
  - Followers count with profile pictures (e.g., "401 followers")
  - Recent views count (e.g., "20.1K recent views")
  - Insights link → `/insights`
  - Instagram link (redirect to instagram.com)
- `button "Edit profile"` (own profile only)
- Tabs: **Threads**, **Replies**, **Media**, **Reposts**
  - Threads: `/@username`
  - Replies: `/@username/replies`
  - Media: `/@username/media`
  - Reposts: `/@username/reposts`
- Post composer below tabs: "What's new?" + `button "Post"`
- Vertical feed (one post per row, NOT grid)
- Infinite scroll with skeleton loading

**Note:** Threads does NOT show "following" count. No highlights feature like Instagram Stories.

**Extract profile data via run_code:**
```js
async (page) => {
  await page.goto('https://www.threads.com/@username');
  await page.waitForTimeout(5000);
  
  return await page.evaluate(() => {
    const result = {};
    const h1 = document.querySelectorAll('h1');
    result.displayName = h1[1]?.textContent; // second h1 is display name
    result.username = document.querySelector('[class*="username"]')?.textContent;
    result.bio = document.querySelector('[class*="bio"]')?.textContent;
    result.followers = document.body.innerText.match(/(\d[\d,.]*)\s*followers/)?.[1];
    result.recentViews = document.body.innerText.match(/([\d,.]+[KMB]?)\s*recent views/)?.[1];
    
    // Get post links
    const postLinks = document.querySelectorAll('a[href*="/post/"]');
    result.posts = [...postLinks].map(a => ({
      url: a.href,
      text: a.querySelector('img')?.alt?.substring(0, 100) || a.textContent?.substring(0, 100)
    }));
    
    return result;
  });
}
```

---

## 9. Post Detail

```
Navigate: https://www.threads.com/@<username>/post/<shortcode>
```

**Structure:**
- Column title: "Thread" with view count (e.g., "2.5K views")
- "Back" button
- "More" button (⋯)
- Post content (text, images, carousel indicator "2/2")
- Action buttons: Like, Reply, Repost, Share, Translate
- "More" button on each reply/thread
- Reply compose area
- Replies thread below

---

## 10. Activity / Notifications

```
Navigate: https://www.threads.com/activity
```

**Page title:** `(N) Activity • Threads`
**Header:** `heading "Activity"` + filter dropdown `button "All"` (with chevron)

**Notification types:**

1. **Likes** — "username and N others" → timestamp → link to liked post
   - Aggregated: multiple likes grouped as "username and 20 others"
   - No action buttons, click goes to post

2. **Follows from Posts** — "username and N others" → "Followed from your post" label → link to post
   - Key identifier: text "Followed from your post"

3. **Direct Follows** — two variants:
   - "Followed you" + `button "Follow back"`
   - "You're now following" + `button "Following"`

4. **Replies** — username → quoted original post text → reply link → action bar (Like/Reply/Repost/Share)
   - Shows the original post as plain text, then the reply

5. **System/Platform** — from "threads" official account
   - "Your thread got over 100 views."
   - "Your thread was shared over 5 times and got over 1,000 views."
   - "Threads is now in Accounts Center..."
   - No action buttons

6. **Suggested Threads** — "Suggested thread" label + full post with Like/Reply/Repost/Share counts
   - Has action buttons with counts (e.g., "Like 31", "Reply 129")

**Filter:** `button "All"` dropdown at top for filtering notification type

---

## 11. Follow / Unfollow

**From profile page:**
- `button "Follow"` → click to follow
- After follow: button changes to "Following" (click to unfollow)

**From search results:**
- Each user card has `button "Follow"` next to their name

---

## 12. Save Post

- `link "Saved"` in sidebar → `/saved/` (bookmarked posts)
- Save action via "More" menu on individual posts

---

## 13. Translate Post

- `button "Translate"` appears on non-English posts
- Click to translate inline

---

## 15. Custom Feeds

Users can create custom feeds in the sidebar:
- Feeds section shows: Following, Ghost posts, custom feeds (AI Threads, Coding, etc.)
- `button "Edit"` to manage feeds
- `button "Show more"` to see all feeds
- Posts can be added to feeds via "Add to feed" menu items

## 16. Fediverse Sharing

Some posts show "Post is shared to Fediverse" icon — indicates the post is also visible on federated platforms.

---

## URL Reference

| Action | URL |
|--------|-----|
| Home/Feed | `https://www.threads.com/` |
| Following feed | `https://www.threads.com/following/` |
| Ghost posts | `https://www.threads.com/ghost_posts/` |
| Search | `https://www.threads.com/search` |
| Search query | `https://www.threads.com/search?q=<query>` |
| Search recent | `https://www.threads.com/search?q=<query>&filter=recent` |
| Search profiles | `https://www.threads.com/search?q=<query>&filter=profiles` |
| Search author | `https://www.threads.com/search?from_author=<username>` |
| Tag search | `https://www.threads.com/search?q=<tag>&serp_type=tags&tag_id=<id>` |
| Profile | `https://www.threads.com/@<username>` |
| Replies | `https://www.threads.com/@<username>/replies` |
| Media | `https://www.threads.com/@<username>/media` |
| Reposts | `https://www.threads.com/@<username>/reposts` |
| Post detail | `https://www.threads.com/@<username>/post/<shortcode>` |
| DM inbox | `https://www.threads.com/messages/` |
| DM requests | `https://www.threads.com/messages/requests` |
| DM thread | `https://www.threads.com/messages/t/<thread_id>/` |
| New DM | `https://www.threads.com/messages/new/` |
| Activity | `https://www.threads.com/activity` |
| Insights | `https://www.threads.com/insights/` |
| Saved | `https://www.threads.com/saved/` |
| Custom feed | `https://www.threads.com/custom_feed/<id>/` |

---

## Pitfalls

1. **Duplicate image upload**: Patchright `fileChooser.setFiles()` sometimes uploads 2 copies. After upload, check for multiple "Remove" buttons — if count > 1, click first one to remove duplicate. Always verify `Remove` button count before typing text.

2. **Character limit ~500**: Threads has a ~500 character limit. If the counter shows negative (e.g., "-51"), the post will NOT publish. Shorten text or split into thread. Check counter in snapshot before clicking Post.

3. **File upload path restriction**: Patchright only allows files from `/workspaces/patchright-browser/`. Files from other paths (e.g., `/workspaces/`, `/tmp/`) get "File access denied: outside allowed roots". Always copy files to `/workspaces/patchright-browser/` before uploading.

4. **Cookie banners**: Some sites (fal.ai, etc) show cookie consent banners that block interaction. Dismiss with `getByRole('button', {name: /reject|decline|close/i})` before proceeding.

5. **Ref staleness**: After any navigation or page change, refs expire. Always `snapshot` fresh before clicking.
2. **Ref staleness**: After navigation or column change, always `snapshot` fresh.
3. **English UI**: All labels are English (Like, Reply, Repost, Share, Follow, Post, Message, More, Create).
4. **Button labels with counts**: "Like 36", "Reply 6", "Repost 4", "Share 6" — counts are part of the label text.
5. **Compose area**: Labeled "Empty text field. Type to compose a new post." or "What's new?"
6. **Post button**: After typing in compose, click `button "Post"` to publish.
7. **Loading states**: Threads content loads async — use `waitForTimeout(3000-5000)` after navigation.
8. **"More" menu**: Posts have "More" button (⋯) for edit, delete, save, mute, block options.
9. **Thread vs Reply**: Original posts = "Threads", responses = "Replies". Profile has separate tabs.
10. **DM thread URL**: `/messages/t/<thread_id>/` — different from Instagram's `/direct/t/<id>/`.
11. **Translate button**: Appears on non-English posts. "Translate" label.
12. **Fediverse indicator**: Some posts show "Post is shared to Fediverse" icon.
13. **Tags**: Posts can have community tags (e.g., "AI Threads", "Coding") shown as links.
14. **Views count**: Post detail shows view count (e.g., "2.5K views"). Profile shows "20.1K recent views".
15. **Follow suggestions**: Search page shows "Follow suggestions" section with user cards.
16. **Search filters**: Top/Recent/Profiles tabs appear after query. "Filter" button next to search box.
17. **Profile grid vs list**: Search Profiles shows 4-per-row grid at top, then list below. Profile page uses vertical feed (not grid).
18. **Activity aggregation**: Likes are grouped as "username and N others". Follows show "Followed from your post" or "Followed you".
19. **System notifications**: From "threads" official account — view milestones, platform updates. No action buttons.
20. **Suggested threads**: Appear in activity with "Suggested thread" label + full engagement counts.
21. **Search redirect**: Exact username match in search auto-redirects to profile page.
22. **Link preview cards**: Posts can have OG link previews (favicon, domain, title, image).
23. **No following count**: Profile only shows followers, not following count.
24. **No highlights**: Threads does not have Instagram-style highlights/stories.
25. **DM message actions**: 3 buttons per message (Reply, React, More). Buttons only visible on hover.
26. **DM input**: contenteditable div with role="textbox", NOT a textarea/input. Use `page.locator('[role="textbox"][contenteditable="true"]')`.
27. **Post "More" menu**: Own posts have Delete/Archive/Pin/Reply options. Other posts have Mute/Restrict/Report/Unfollow.
28. **Reply compose**: Has "Attach media" + "Add a GIF" + "Expand composer" buttons.
29. **Reply sorting**: "Sort Top More" button to sort replies by Top or Recent.
30. **View activity**: "View activity" button on post detail to see who liked/reposted.
31. **Notification settings**: Per-post notification toggle via "Notification settings" button.
32. **DM requests**: Separate inbox for message requests from non-f followers.
33. **Custom feeds**: Users can create custom feeds and add posts to them via "Add to feed" menu.
34. **Archive**: Hides post from profile without deleting. Different from Delete.
35. **Pin to profile**: Post appears at top of profile grid.
**⚠️ Pitfall: Duplicate image upload**
Patchright `fileChooser.setFiles()` kadang upload 2x sehingga composer punya 2 gambar (2x "Remove" button). **WAJIB cek jumlah Remove buttons setelah upload.** Kalau lebih dari 1 → klik salah satu untuk hapus duplikat. Pattern:
```python
removeButtons = page.getBy_role('button', { name: 'Remove' })
if await removeButtons.count() > 1:
    await removeButtons.first().click()
    await page.wait_for_timeout(500)
```

**⚠️ Pitfall: File upload path restriction**
Patchright hanya bisa upload file dari `/workspaces/patchright-browser/`. File di path lain → "File access denied: outside allowed roots". Copy file ke `/workspaces/patchright-browser/` dulu sebelum upload.

**⚠️ Pitfall: Threads text limit ~500 chars**
Threads composer punya karakter limit (~500). Counter muncul di bawah Post button (misal "-51" = kepanjangan 51 chars). Kalau kepanjangan, post tidak terkirim. Pastikan copywriting di bawah 500 karakter.

36. **CRUD completeness**: When testing any action (like, reply, repost), ALWAYS test the reverse (unlike, delete reply, undo repost). User requires full CRUD coverage.
