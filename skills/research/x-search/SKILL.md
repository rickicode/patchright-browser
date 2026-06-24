---
name: x-search
description: "X.com (Twitter) search & data extraction — cari post dengan advanced operators, extract replies, scroll pagination. Browser-based via Patchright MCP."
triggers:
  - "cari di x"
  - "search x"
  - "search twitter"
  - "x search"
  - "twitter search"
  - "research x"
  - "cari data x"
  - "cari tweet"
  - "x-research"
tools:
  - mcp_patchright_browser_navigate
  - mcp_patchright_browser_click
  - mcp_patchright_browser_snapshot
  - mcp_patchright_browser_run_code
  - mcp_patchright_browser_wait_for
  - mcp_patchright_browser_scroll
  - mcp_patchright_browser_tabs
---

# X.com Search & Data Extraction

Search X.com (Twitter), extract posts with full reply threads via Patchright MCP.

## Prerequisites
- Patchright daemon running (port 9877)
- Profile logged in to X.com
- Default profile: `rickicode`

## Search URL Patterns

| Filter | URL |
|--------|-----|
| Top | `https://x.com/search?q={query}&src=typed_query` |
| Latest | `https://x.com/search?q={query}&src=typed_query&f=live` |
| People | `https://x.com/search?q={query}&src=typed_query&f=user` |
| Media | `https://x.com/search?q={query}&src=typed_query&f=image` |

## Advanced Search Operators
- `"exact phrase"` — exact match
- `from:username` — posts by specific user
- `to:username` — replies to specific user
- `since:2026-01-01` / `until:2026-06-30` — date range
- `min_faves:1000` / `min_retweets:100` / `min_replies:50` — engagement threshold
- `filter:links` / `filter:images` / `filter:videos` — content type
- `filter:verified` — only verified accounts
- `-filter:replies` — exclude replies
- `lang:id` / `lang:en` — language filter

## Extract Posts with Card Links (run_code) — VERIFIED WORKING
```js
async (page) => {
  await page.waitForTimeout(5000);
  return await page.evaluate(() => {
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    return [...articles].slice(0, 10).map(article => {
      const userNameEl = article.querySelector('[data-testid="User-Name"]');
      const links = userNameEl?.querySelectorAll('a') || [];
      const textEl = article.querySelector('[data-testid="tweetText"]');
      const timeEl = article.querySelector('time');
      // Extract card links (link preview cards) — these have actual external URLs
      const cards = article.querySelectorAll('[data-testid="card.wrapper"]');
      const cardLinks = [...cards].map(c => {
        const a = c.querySelector('a');
        return a ? a.href : null;
      }).filter(Boolean);
      return {
        authorHandle: links[1]?.textContent?.trim() || '',
        text: textEl?.textContent?.trim() || '',
        tweetUrl: timeEl?.closest('a')?.href || '',
        cardLinks: cardLinks,
      };
    });
  });
}
```

**Important:** Most X posts about "AI free credits" don't have direct URLs in text. The actual external links are in **card preview links** (`[data-testid="card.wrapper"]`). These are t.co shortened URLs that redirect to the real destination. Always extract `cardLinks` for research/promo hunting.
```js
async (page) => {
  await page.waitForTimeout(5000);
  return await page.evaluate(() => {
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    return [...articles].map(article => {
      const userNameEl = article.querySelector('[data-testid="User-Name"]');
      const links = userNameEl?.querySelectorAll('a') || [];
      const textEl = article.querySelector('[data-testid="tweetText"]');
      const timeEl = article.querySelector('time');
      const replyBtn = article.querySelector('[data-testid="reply"]');
      const retweetBtn = article.querySelector('[data-testid="retweet"]');
      const likeBtn = article.querySelector('[data-testid="like"]');
      const viewsEl = article.querySelector('a[href*="/analytics"]');
      const imgs = article.querySelectorAll('img[src*="pbs.twimg.com/media"]');

      return {
        authorName: links[0]?.textContent?.trim() || '',
        authorHandle: links[1]?.textContent?.trim() || '',
        authorUrl: links[0]?.href || '',
        verified: !!article.querySelector('img[alt="Verified account"]'),
        text: textEl?.textContent?.trim() || '',
        timestamp: timeEl?.getAttribute('datetime') || '',
        timeDisplay: timeEl?.textContent?.trim() || '',
        url: timeEl?.closest('a')?.href || '',
        replies: replyBtn?.getAttribute('aria-label') || '',
        retweets: retweetBtn?.getAttribute('aria-label') || '',
        likes: likeBtn?.getAttribute('aria-label') || '',
        views: viewsEl?.textContent?.trim() || '',
        images: [...imgs].map(i => i.src),
        hasVideo: !!article.querySelector('video, [data-testid="videoPlayer"]'),
        hasQuote: !!article.querySelector('[data-testid="quoteTweet"]'),
      };
    });
  });
}
```

## Extract Replies from Post Detail — VERIFIED WORKING
Navigate to post URL, then extract main post + replies:
```js
async (page) => {
  // Navigate to post first, then:
  await page.waitForTimeout(5000);
  // Scroll to load more replies
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => window.scrollBy(0, 1000));
    await page.waitForTimeout(2000);
  }
  return await page.evaluate(() => {
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    return [...articles].map((article, idx) => {
      const userNameEl = article.querySelector('[data-testid="User-Name"]');
      const links = userNameEl?.querySelectorAll('a') || [];
      const textEl = article.querySelector('[data-testid="tweetText"]');
      const timeEl = article.querySelector('time');
      const likeBtn = article.querySelector('[data-testid="like"]');
      const viewsEl = article.querySelector('a[href*="/analytics"]');
      return {
        authorName: links[0]?.textContent?.trim() || '',
        authorHandle: links[1]?.textContent?.trim() || '',
        verified: !!article.querySelector('img[alt="Verified account"]'),
        text: textEl?.textContent?.trim() || '',
        timestamp: timeEl?.getAttribute('datetime') || '',
        likes: likeBtn?.getAttribute('aria-label') || '',
        views: viewsEl?.textContent?.trim() || '',
        isMainPost: idx === 0,
      };
    });
  });
}
```

## Scroll Pagination — VERIFIED WORKING
```js
async (page, maxScrolls = 5) => {
  let allTweets = [];
  const seen = new Set();
  for (let i = 0; i < maxScrolls; i++) {
    const tweets = await page.evaluate(() => {
      return [...document.querySelectorAll('article[data-testid="tweet"]')].map(a => ({
        url: a.querySelector('time')?.closest('a')?.href || '',
        text: a.querySelector('[data-testid="tweetText"]')?.textContent?.trim()?.substring(0, 100) || '',
      }));
    });
    for (const t of tweets) {
      if (t.url && !seen.has(t.url)) {
        seen.add(t.url);
        allTweets.push(t);
      }
    }
    await page.evaluate(() => window.scrollBy(0, 2000));
    await page.waitForTimeout(2000);
  }
  return { total: allTweets.length, tweets: allTweets };
}
```

## Pitfalls
1. **Rate limiting**: X may show "Rate limit exceeded". Wait 3-5s between navigations.
2. **Login wall**: Search requires login. Profile must be logged in.
3. **Ref staleness**: After navigation, always get fresh snapshot.
4. **Infinite scroll**: Use `window.scrollBy()` to load more results.
5. **Verified badge**: `img[alt="Verified account"]`.
6. **Post URL**: `/{user}/status/{id}`.
7. **Engagement labels**: "291 Replies. Reply", "4781 reposts. Repost", "27692 Likes. Like".
8. **Quote tweets**: Nested structure — extract both outer and inner.
9. **t.co link resolution**: Card links use t.co shortened URLs. Always resolve with `requests.head(url, allow_redirects=True)` to get the actual destination URL. Filter out t.co/twitter.com/x.com from final candidates.
10. **Card link extraction**: Use `[data-testid="card.wrapper"]` selector for link preview cards. These contain the actual external URLs behind t.co shortlinks.
11. **Tab loading**: After navigate, X takes 3-5s to load. Use `waitForTimeout(5000)`.
12. **Tab title mismatch**: Snapshot may show wrong page title initially — wait for load.
13. **Tab selection**: If multiple tabs open, use `tabs(action='select')` to switch.
14. **MCP client from Python**: Use `mcp.client.streamable_http.streamablehttp_client` + `ClientSession` — NOT raw HTTP POST. See `patchright-browser` skill for full pattern.
9. **Quote tweets**: Nested structure — extract both outer and inner.
10. **Tab loading**: After navigate, X takes 3-5s to load. Use `waitForTimeout(5000)`.
11. **Page title mismatch**: Snapshot may show wrong page title initially — wait for load.
12. **Tab selection**: If multiple tabs open, use `tabs(action='select')` to switch.
