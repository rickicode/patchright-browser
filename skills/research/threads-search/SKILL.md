---
name: threads-search
description: "Threads (threads.com) search & data extraction — cari post, extract comments/replies, scroll pagination. Browser-based via Patchright MCP."
triggers:
  - "cari di threads"
  - "search threads"
  - "threads search"
  - "research threads"
  - "cari data threads"
  - "threads-research"
  - "cari post threads"
  - "cari utas"
tools:
  - mcp_patchright_browser_navigate
  - mcp_patchright_browser_click
  - mcp_patchright_browser_snapshot
  - mcp_patchright_browser_run_code
  - mcp_patchright_browser_wait_for
  - mcp_patchright_browser_scroll
  - mcp_patchright_browser_tabs
---

# Threads Search & Data Extraction

Search Threads (threads.com), extract posts with full reply/comment threads via Patchright MCP.

## Prerequisites
- Patchright daemon running (port 9877)
- Profile logged in to Threads (shared with Instagram)
- Default profile: `rickicode`

## Search URL Patterns

| Filter | URL |
|--------|-----|
| Top (default) | `https://www.threads.com/search?q={query}` |
| Recent | `https://www.threads.com/search?q={query}&filter=recent` |
| Profiles | `https://www.threads.com/search?q={query}&filter=profiles` |
| Author posts | `https://www.threads.com/search?from_author={username}` |
| Tag search | `https://www.threads.com/search?q={tag}&serp_type=tags&tag_id={id}` |

## Extract Search Results — VERIFIED WORKING
```js
async (page) => {
  await page.waitForTimeout(5000);
  return await page.evaluate(() => {
    const results = [];
    const seen = new Set();
    const links = document.querySelectorAll('a[href*="/post/"]');

    for (const link of links) {
      const postUrl = link.href;
      if (seen.has(postUrl)) continue;
      seen.add(postUrl);

      // Walk up to find the containing post block
      const container = link.closest('[data-pressable-container]') || link.closest('div[class*="post"]') || link.parentElement?.parentElement?.parentElement;
      if (!container) continue;

      const text = container.innerText || '';
      const timeEl = container.querySelector('time');
      const authorLink = container.querySelector('a[href^="/@"]');

      results.push({
        authorHandle: authorLink?.textContent?.trim() || '',
        authorUrl: authorLink?.href || '',
        text: text.split('\n').filter(l => l.length > 10).slice(0, 3).join(' | ').substring(0, 500),
        postUrl,
        timestamp: timeEl?.getAttribute('datetime') || '',
        timeDisplay: timeEl?.textContent?.trim() || '',
      });
    }
    return results;
  });
}
```

## Extract Post with Replies (Detail Page) — VERIFIED WORKING
Navigate to post URL, then extract:
```js
async (page, postUrl) => {
  await page.goto(postUrl);
  await page.waitForTimeout(5000);

  // Scroll to load more replies
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => window.scrollBy(0, 800));
    await page.waitForTimeout(2000);
  }

  return await page.evaluate(() => {
    const results = { post: null, replies: [] };
    const items = document.querySelectorAll('[data-pressable-container="true"]');

    for (const item of items) {
      const links = item.querySelectorAll('a');
      const authorLink = [...links].find(a => a.href?.includes('/@') && !a.href?.includes('/post/'));
      const timeEl = item.querySelector('time');
      const text = item.innerText || '';

      // Parse engagement counts from buttons
      const btns = item.querySelectorAll('button');
      let likeCount = '', replyCount = '', repostCount = '';
      for (const btn of btns) {
        const label = btn.getAttribute('aria-label') || btn.textContent || '';
        if (label.startsWith('Like') && /\d/.test(label)) likeCount = label.replace('Like', '').trim();
        if (label.startsWith('Reply') && /\d/.test(label)) replyCount = label.replace('Reply', '').trim();
        if (label.startsWith('Repost') && /\d/.test(label)) repostCount = label.replace('Repost', '').trim();
      }

      const entry = {
        authorHandle: authorLink?.textContent?.trim() || '',
        authorUrl: authorLink?.href || '',
        text: text.split('\n').filter(l => l.length > 10).slice(0, 3).join(' | ').substring(0, 500),
        postUrl: [...links].find(a => a.href?.includes('/post/'))?.href || '',
        timestamp: timeEl?.getAttribute('datetime') || '',
        timeDisplay: timeEl?.textContent?.trim() || '',
        likes: likeCount,
        replies: replyCount,
        reposts: repostCount,
      };

      if (!results.post) {
        results.post = entry;
      } else if (entry.text.length > 5) {
        results.replies.push(entry);
      }
    }

    return results;
  });
}
```

## Extract Profile Posts — VERIFIED WORKING
```js
async (page, username) => {
  await page.goto(`https://www.threads.com/@${username}`);
  await page.waitForTimeout(5000);

  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => window.scrollBy(0, 1000));
    await page.waitForTimeout(2000);
  }

  return await page.evaluate(() => {
    const followerText = document.body.innerText.match(/(\d[\d,.]*[KMB]?)\s*followers/i);

    const postLinks = document.querySelectorAll('a[href*="/post/"]');
    const seen = new Set();
    const posts = [];

    for (const link of postLinks) {
      if (seen.has(link.href)) continue;
      seen.add(link.href);

      const container = link.closest('[data-pressable-container]') || link.parentElement?.parentElement;
      const text = container?.innerText || '';
      const timeEl = container?.querySelector('time');

      posts.push({
        text: text.split('\n').filter(l => l.length > 10).slice(0, 3).join(' | ').substring(0, 300),
        postUrl: link.href,
        timestamp: timeEl?.getAttribute('datetime') || '',
        timeDisplay: timeEl?.textContent?.trim() || '',
      });
    }

    return {
      followers: followerText?.[1] || '',
      posts
    };
  });
}
```

## Scroll Pagination — VERIFIED WORKING
```js
async (page, maxScrolls = 5) => {
  let allPosts = [];
  const seen = new Set();

  for (let i = 0; i < maxScrolls; i++) {
    const posts = await page.evaluate(() => {
      const links = document.querySelectorAll('a[href*="/post/"]');
      return [...links].map(l => ({
        url: l.href,
        text: (l.closest('[data-pressable-container]')?.innerText || '').substring(0, 100),
      }));
    });

    for (const p of posts) {
      if (p.url && !seen.has(p.url)) {
        seen.add(p.url);
        allPosts.push(p);
      }
    }

    await page.evaluate(() => window.scrollBy(0, 1500));
    await page.waitForTimeout(2000);
  }

  return { total: allPosts.length, posts: allPosts };
}
```

## Pitfalls
1. **Column layout**: Threads uses columns, not full pages. Content loads in active column.
2. **English UI**: All labels in English (Like, Reply, Repost, Share, Follow, Post).
3. **Ref staleness**: After navigation, always get fresh snapshot.
4. **Post URL format**: `/@{user}/post/{shortcode}`.
5. **Engagement counts**: In button text — "Like 36", "Reply 6", "Repost 4".
6. **"Show more"**: Long posts have expand button — click to get full text.
7. **DM URL**: `/messages/t/{thread_id}/` — different from Instagram.
8. **Shared auth**: Threads shares login with Instagram.
9. **Rate limiting**: Add `waitForTimeout(3000)` between navigations.
10. **No views count on search**: Only visible on post detail page.
11. **Post detail selector**: `[data-pressable-container="true"]` — first item is main post, rest are replies.
12. **Media URL**: Images from `cdninstagram` domain.
13. **Translate button**: Non-English posts show "Translate" button.
14. **"No replies yet"**: New posts show "No replies yet" text — replies array will be empty.
15. **View count**: Post detail shows "1 view", "2.5K views" in column header area.
16. **Fediverse indicator**: Some posts show "Post will be shared to Fediverse" icon.
17. **Tab loading**: After navigate, Threads takes 3-6s to load. Use `waitForTimeout(5000)`.
18. **Post link dedup**: Search results may include `/post/xxx/media` URLs — deduplicate by base post URL.
19. **File upload path**: Patchright only allows files from `/workspaces/patchright-browser/`. Copy files there before uploading.
20. **Duplicate image upload**: `fileChooser.setFiles()` sometimes uploads 2 copies. Check `Remove` button count after upload.
21. **Character limit ~500**: Posts over ~500 chars show negative counter and won't publish.
22. **MCP client from Python**: Use `mcp.client.streamable_http.streamablehttp_client` + `ClientSession` — NOT raw HTTP POST. See `patchright-browser` skill for full pattern.
19. **Image upload duplication**: When uploading images to Threads composer via Patchright, the file chooser can trigger twice, creating 2 copies. After upload, check for duplicate "Remove" buttons — if 2 exist, click one to remove the duplicate before posting.
