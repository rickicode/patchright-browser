---
name: x-automation
description: "X.com (Twitter) automation via Patchright MCP — post, reply, like, retweet, DM, search, profile. English UI. Part of social-media-browser umbrella."
triggers:
  - "x.com"
  - "twitter"
  - "tweet"
  - "post x"
  - "reply x"
  - "like tweet"
  - "dm x"
  - "retweet"
  - "search x"
  - "profil x"
tools:
  - mcp_patchright_browser_navigate
  - mcp_patchright_browser_click
  - mcp_patchright_browser_type
  - mcp_patchright_browser_snapshot
  - mcp_patchright_browser_run_code
  - mcp_patchright_browser_file_upload
  - mcp_patchright_browser_take_screenshot
---

# X.com (Twitter) Automation via Patchright MCP

## Prerequisites
- Patchright profile must be **already logged in** to X.com
- Use `profile="rickicode"` (default) or whichever profile has X session
- All interactions use `mcp_patchright_*` tools

## Architecture: Fixed Sidebar + Main Content

X.com uses a **fixed sidebar + main content** layout:
- **Left sidebar**: Navigation (fixed, always visible)
- **Center**: Main content (timeline, post detail, profile, DM)
- **Right sidebar**: Trending, Who to follow, Search

---

## Navigation Sidebar

| Item | Label | URL |
|------|-------|-----|
| X logo | `link "X"` | `/home` |
| Home | `link "Home"` | `/home` |
| Search | `link "Search and explore"` | `/explore` |
| Notifications | `link "Notifications"` | `/notifications` |
| Follow | `link "Follow"` | `/i/connect_people` |
| DM | `link "Direct Messages"` | `/i/chat` |
| Grok | `link "Grok"` | `/i/grok` |
| Bookmarks | `link "Bookmarks"` | `/i/bookmarks` |
| Creator Studio | `link "Creator Studio"` | `/i/jf/creators/studio` |
| Premium | `link "Premium"` | `/i/premium_sign_up` |
| Profile | `link "Profile"` | `/<username>` |
| More | `button "More menu items"` | — |
| Post | `link "Post"` | `/compose/post` |
| Account | `button "Account menu"` | — |

---

## 1. Create Post (Tweet)

### Compose Area
Located at top of home timeline:
- `textbox "Post text"` — main input
- `button "Post"` — publish (disabled until text entered)

### Compose Buttons
- `button "Add photos or video"` + `button "Choose File"` — media upload
- `button "Add a GIF"` — GIF picker
- `button "Generate image"` — AI image generation
- `button "Add poll"` — create poll
- `button "Add emoji"` — emoji picker
- `button "Schedule post"` — schedule for later
- `button "Tag location"` — add location
- `button "Content disclosure"` — content warnings

### run_code approach:
```js
async (page) => {
  await page.goto('https://x.com/home');
  await page.waitForTimeout(3000);
  
  // Click compose
  const textbox = page.getByRole('textbox', { name: 'Post text' });
  await textbox.click();
  await textbox.fill('Your tweet text here');
  await page.waitForTimeout(500);
  
  // Click Post
  await page.getByRole('button', { name: 'Post' }).click();
  await page.waitForTimeout(2000);
  return 'posted';
}
```

---

## 2. Like / Unlike Post

**Action bar:** `button "N Likes. Like"` or `button "N Likes. Liked"`
- Click to like → changes to "Liked"
- Click again to unlike → changes to "Like"

**run_code:**
```js
async (page) => {
  const likeBtn = page.getByRole('button', { name: /Likes.*Like/ }).first();
  await likeBtn.click();
  await page.waitForTimeout(500);
  return 'liked';
}
```

---

## 3. Reply to Post

**Action bar:** `button "N Replies. Reply"`
- Click → opens reply compose
- Type reply + click "Post"

**From post detail page:**
- Navigate to `/<username>/status/<id>`
- Reply compose at top

---

## 4. Repost / Quote Repost

**Action bar:** `button "N reposts. Repost"` or `button "N reposts. Reposted"`
- Click → confirm repost
- "Reposted" state shown when already reposted

**Quote Repost:**
- Click "Repost" → select "Quote"
- Add comment + click "Post"

---

## 5. Bookmark Post

**Action bar:** `button "Bookmark"`
- Click to bookmark
- View bookmarks at `/i/bookmarks`

---

## 6. Share Post

**Action bar:** `button "Share post"`
- Opens share options (copy link, DM, etc.)

---

## 7. View Post Analytics

**Action bar:** `link "N views. View post analytics"` → `/<username>/status/<id>/analytics`

---

## 8. Post "More" Menu

### Own Post Menu (`button "More"` on your post)
- `menuitem "Delete"` — delete post
- `menuitem "Pin to your profile"` — pin to top
- `menuitem "Highlight on your profile"` — highlight
- `menuitem "Add/remove from Lists"` — manage lists
- `menuitem "Add/remove content disclosure"` — content warnings
- `menuitem "Change who can reply"` — reply controls
- `menuitem "View post activity"` — engagement details
- `menuitem "Embed post"` — embed code
- `menuitem "View post analytics"` — detailed analytics
- `menuitem "Request Community Note"` — fact-check request

### Other User's Post Menu (`button "More"` on their post)
- `menuitem "Follow @username"` — follow
- `menuitem "Subscribe to @username"` — subscribe
- `menuitem "Add/remove from Lists"` — manage lists
- `menuitem "Mute"` — mute user
- `menuitem "Block @username"` — block user
- `menuitem "View post activity"` — engagement
- `menuitem "Embed post"` — embed code
- `menuitem "Report post"` — report
- `menuitem "Request Community Note"` — fact-check

**run_code to click menu item:**
```js
async (page) => {
  // Click More button on post
  await page.evaluate(() => {
    const articles = document.querySelectorAll('article');
    if (articles.length > 0) {
      const moreBtn = articles[0].querySelector('button[aria-label="More"]');
      if (moreBtn) moreBtn.click();
    }
  });
  await page.waitForTimeout(1000);
  
  // Click menu item
  const menuItem = page.getByRole('menuitem', { name: 'Delete' });
  await menuItem.click();
  await page.waitForTimeout(1000);
  
  // Confirm if dialog
  const confirmBtn = page.getByRole('button', { name: /Delete|Confirm/ });
  if (await confirmBtn.isVisible()) {
    await confirmBtn.click();
  }
  return 'done';
}
```

---

## 9. DM (Direct Messages / X Chat)

```
Navigate: https://x.com/i/chat
```

**IMPORTANT:** X has replaced traditional DMs with **X Chat** featuring end-to-end encryption. Requires passcode setup before use.

### Setup Required
- If not configured: redirects to `/i/chat/pin/new`
- Shows "Welcome to the new X Chat" onboarding
- `data-testid="pin-onboarding-setup-now"` → "Create Passcode"
- Three E2E encryption icons: `icon-dms-lock`, `icon-dms-shield`, `icon-passcode`

### Two Access Modes
1. **Full-page chat** (`/i/chat`) — dedicated page
2. **Chat drawer** — floating button `data-testid="chat-drawer-main"` → slide-out panel

### Chat Structure (after passcode setup)
- **Drawer root**: `data-testid="chat-drawer-root"`
- **Left panel**: conversation list
- **Right panel**: active conversation
- **Input**: message input at bottom

### Chat Features
- Send text message
- Send image/media
- React to message
- Reply to specific message
- Delete message
- E2E encrypted

### Key data-testids
- `data-testid="chat-drawer-main"` — drawer toggle button
- `data-testid="chat-drawer-root"` — drawer container
- `data-testid="pin-onboarding-title"` — onboarding title
- `data-testid="pin-onboarding-setup-now"` — setup button

---

## 10. Search

```
Navigate: https://x.com/explore
```

**Search box:** `combobox "Search query"` in right sidebar or explore page
- Type query + Enter
- Results: Top, Latest, People, Media tabs

**Search URL:** `https://x.com/search?q=<query>&src=typed_query`

---

## 11. Profile

```
Navigate: https://x.com/<username>
```

**Structure:**
- Header: Back button + Display Name + post count + Search button
- Banner image: `a[href*="/header_photo"] img` (600x200)
- Profile photo: `a[href*="/photo"] img` (200x200)
- Display name: `h2` heading + verified badge `svg[data-testid="icon-verified"]`
- Username: `@<username>` in `[data-testid="UserName"]`
- Bio: `[data-testid="UserDescription"]`
- Birthday: text node near join date (e.g., "Born April 16, 1998")
- Join date: `a[href*="/about"]` containing "Joined" (e.g., "Joined July 2013")
- Following: `a[href$="/following"]` (e.g., "86 Following")
- Followers: `a[href$="/verified_followers"]` (e.g., "3,967 Followers")
- Location: `[data-testid="UserLocation"]` (if set)
- Website: `[data-testid="UserUrl"]` (if set)

**Tabs** (`nav[aria-label="Profile timelines"]`):
- Posts (default selected)
- Replies
- Highlights
- Articles
- Media
- Likes

**Action Buttons (own profile):**
- `a[href="/settings/profile"]` → "Edit profile"
- `button[aria-label="Profile Summary"]` → summary
- `button[aria-label="Search"]` → search user's posts

**Action Buttons (other user):**
- `button "Follow @username"` / `button "Following"`
- `button[data-testid="message"]` → DM
- `button[data-testid="userActions"]` → More options

**Post Grid:**
- Posts load as vertical timeline of `article[data-testid="tweet"]`
- Each post contains:
  - `[data-testid="tweetText"]` → post text
  - `time` element → timestamp + post URL (`/<username>/status/<id>`)
  - `img[src*="pbs.twimg.com"]` → images
  - `[data-testid="reply"]` → reply count
  - `[data-testid="retweet"]` → repost count
  - `[data-testid="like"]` → like count

**Image URLs:**
- Profile: `https://pbs.twimg.com/profile_images/<id>_<hash>_<size>.jpg`
- Banner: `https://pbs.twimg.com/profile_banners/<user_id>/<banner_id>/600x200`
- Post media: `https://pbs.twimg.com/media/<id>?format=jpg&name=small`

**Extract profile data:**
```js
async (page) => {
  await page.goto('https://x.com/username');
  await page.waitForTimeout(5000);
  
  return await page.evaluate(() => {
    const result = {};
    result.displayName = document.querySelector('h2')?.textContent;
    result.username = document.querySelector('[data-testid="UserName"]')?.textContent;
    result.bio = document.querySelector('[data-testid="UserDescription"]')?.textContent;
    result.following = document.querySelector('a[href$="/following"]')?.textContent;
    result.followers = document.querySelector('a[href$="/verified_followers"]')?.textContent;
    result.joinDate = document.querySelector('a[href*="/about"]')?.textContent;
    
    // Get posts
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    result.posts = [...articles].map(a => ({
      text: a.querySelector('[data-testid="tweetText"]')?.textContent?.substring(0, 100),
      time: a.querySelector('time')?.getAttribute('datetime'),
      url: a.querySelector('time')?.closest('a')?.href,
      images: [...a.querySelectorAll('img[src*="pbs.twimg.com/media"]')].map(i => i.src)
    }));
    
    return result;
  });
}
```

---

## 12. Notifications

```
Navigate: https://x.com/notifications
```

**Page header:** `h2 "Notifications"` + `a[href="/settings/notifications"]` (Settings gear icon)

**Filter Tabs** (`nav[aria-label="Notifications timelines"]` + `div[role="tablist"]`):
- `a[role="tab"][href="/notifications"]` → **All** (default selected)
- `a[role="tab"][href="/notifications/priority"]` → **Priority** (high-priority accounts)
- `a[role="tab"][href="/notifications/mentions"]` → **Mentions** (only @mentions)

**Notification Types:**

Each notification is an `article[data-testid="notification"]` inside `div[aria-label="Timeline: Notifications"]`.

1. **Activity notifications** (likes, retweets, follows):
   - Type icon: SVG starburst/star icon
   - User avatar: `[data-testid="UserAvatar-Container-{username}"]`
   - Username + timestamp
   - Post text: `[data-testid="tweetText"]`
   - "More" button: `button[aria-label="More"][data-testid="caret"]`

2. **Pinned post notifications** (community):
   - Type icon: SVG pin/thumbtack icon
   - Text: "New pinned post in {community name}"

3. **Mentions** (empty state):
   - "Nothing to see here — yet. When someone mentions you, you'll find it here."

**Action Buttons:**
- `button[aria-label="More"][data-testid="caret"]` — context menu on each notification
- Settings link → `/settings/notifications`

**Key data-testids:**
- `[data-testid="notification"]` — notification article
- `[data-testid="UserAvatar-Container-{username}"]` — user avatar
- `[data-testid="tweetText"]` — post text
- `[data-testid="caret"]` — More button

**DOM Hierarchy:**
```
<main>
  div[aria-label="Home timeline"]
    ├── h2 "Notifications" + Settings link
    ├── nav[aria-label="Notifications timelines"] → tablist (All, Priority, Mentions)
    ├── section[aria-label="Notifications"]
    │     └── div[aria-label="Timeline: Notifications"]
    │           └── article[data-testid="notification"] (×N)
    │                 ├── SVG type icon (star/pin)
    │                 ├── User avatar + username + timestamp
    │                 ├── [data-testid="tweetText"]
    │                 └── button[aria-label="More"][data-testid="caret"]
    └── Right sidebar: Trending, Who to follow
```

---

## 13. Follow / Unfollow

- `button "Follow @username"` → click to follow
- After follow: `button "Following"` → click to unfollow
- `menuitem "Follow @username"` in More menu

---

## 14. Bookmarks

```
Navigate: https://x.com/i/bookmarks
```
- All bookmarked posts
- Remove bookmark by clicking Bookmark button again

---

## 15. Lists

```
Navigate: https://x.com/i/lists
```
- Create, edit, manage lists
- Add/remove users from lists via More menu

---

## 16. Grok AI

```
Navigate: https://x.com/i/grok
```
- AI assistant integrated into X
- `button "Grok actions"` on posts — analyze with Grok

---

## 17. Creator Studio

```
Navigate: https://x.com/i/jf/creators/studio
```
- Analytics, monetization, content management

---

## 18. Premium

```
Navigate: https://x.com/i/premium_sign_up
```
- Subscribe to Premium
- Features: no ads, analytics, boost replies, etc.

---

## URL Reference

| Action | URL |
|--------|-----|
| Home | `https://x.com/home` |
| Explore | `https://x.com/explore` |
| Search | `https://x.com/search?q=<query>&src=typed_query` |
| Notifications | `https://x.com/notifications` |
| Mentions | `https://x.com/notifications/mentions` |
| DM | `https://x.com/i/chat` |
| Bookmarks | `https://x.com/i/bookmarks` |
| Lists | `https://x.com/i/lists` |
| Grok | `https://x.com/i/grok` |
| Creator Studio | `https://x.com/i/jf/creators/studio` |
| Premium | `https://x.com/i/premium_sign_up` |
| Profile | `https://x.com/<username>` |
| Profile Replies | `https://x.com/<username>/replies` |
| Profile Media | `https://x.com/<username>/media` |
| Profile Likes | `https://x.com/<username>/likes` |
| Post Detail | `https://x.com/<username>/status/<id>` |
| Post Analytics | `https://x.com/<username>/status/<id>/analytics` |
| Compose | `https://x.com/compose/post` |
| DM Chat | `https://x.com/i/chat` |
| DM Setup | `https://x.com/i/chat/pin/new` |
| Follow suggestions | `https://x.com/i/connect_people` |

---

## Pitfalls

1. **Loading states**: X.com loads async — use `waitForTimeout(5000-10000)` after navigation.
2. **Ref staleness**: After navigation, always `snapshot` fresh.
3. **English UI**: All labels are English (Like, Reply, Repost, Bookmark, Follow, Post, More).
4. **Button labels with counts**: "704 Likes. Like", "28 Replies. Reply" — counts + state in label.
5. **Liked/Reposted state**: "Liked" / "Reposted" in button label when already engaged.
6. **Post compose**: `textbox "Post text"` + `button "Post"` (disabled until text entered).
7. **More menu**: `button "More"` with `aria-label="More"` on each post.
8. **Grok integration**: `button "Grok actions"` on posts for AI analysis.
9. **Protected accounts**: Some profiles show "These posts are protected" — can't view without follow.
10. **Quote tweets**: Nested structure — outer post + quoted post inside.
11. **Community tabs**: Home timeline may show community tabs (e.g., "Komunitas MARAH MARAH").
12. **Trending sidebar**: Right side shows trending topics + "Who to follow" suggestions.
13. **Post URL pattern**: `/<username>/status/<numeric_id>`
14. **DM URL**: `/i/chat` (not `/messages/` like Threads)
15. **Verified accounts**: Show `img "Verified account"` badge next to name.
16. **Repost indicator**: "You reposted" label above reposted posts.
17. **Schedule post**: `button "Schedule post"` for delayed publishing.
18. **Generate image**: `button "Generate image"` for AI image creation.
19. **X Chat E2E encryption**: DMs now require passcode setup (`/i/chat/pin/new`). Two modes: full-page and floating drawer.
20. **data-testid selectors**: X uses `data-testid` extensively — `tweet`, `tweetText`, `notification`, `caret`, `UserName`, `UserDescription`, `UserAvatar-Container-{username}`, `reply`, `retweet`, `like`.
21. **Profile tabs**: Posts, Replies, Highlights, Articles, Media, Likes (6 tabs for own profile).
22. **Profile images**: `pbs.twimg.com` domain. Profile: `/profile_images/`, Banner: `/profile_banners/`, Media: `/media/`.
23. **Notification Priority tab**: May redirect to home timeline instead of showing filtered notifications.
24. **Mentions empty state**: "Nothing to see here — yet. When someone mentions you, you'll find it here."
25. **Community tabs**: Home timeline may show community tabs in the tablist (e.g., "Komunitas MARAH MARAH").
26. **Grok actions**: `button "Grok actions"` on each post for AI analysis.
27. **Protected accounts**: Show "These posts are protected" — can't view without follow approval.
28. **Repost indicator**: "You reposted" label above reposted posts in feed.
29. **Schedule post**: `button "Schedule post"` for delayed publishing.
30. **Content disclosure**: `button "Content disclosure"` for content warnings.
31. **CRUD completeness**: When testing any action (like, reply, retweet), ALWAYS test the reverse (unlike, delete reply, undo retweet). User requires full CRUD coverage.
