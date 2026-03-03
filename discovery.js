(async () => {
  // =========================================================
  // BinBaz "Everything scrapable" inventory (console script)
  // - Sitemap recursion (robots + common candidates + DOM)
  // - Light BFS crawl (same-origin)
  // - Network capture (fetch + XHR + performance)
  // - Auto-download JSON report
  // =========================================================

  const ORIGIN = location.origin;

  const CFG = {
    // Politeness + limits
    concurrency: 4,
    delayMsBetweenRequests: 120,
    timeoutMs: 15000,

    // Crawl fallback (HTML fetches). Keep this modest: sitemap already gives most.
    maxPagesToFetch: 80,
    maxDepth: 2,

    // Sitemap processing caps
    maxSitemapsToProcess: 120,
    maxUrlsToCollectFromSitemaps: 250000,

    // How long to wait to capture late network requests before exporting
    captureWaitMs: 2500,

    // Output
    examplesPerPattern: 8,
    keepQueryInUniq: false, // false = treat /x?a=1 and /x?a=2 as one for uniqueness

    // Standard sitemap candidates (NOT site-specific; just conventions)
    sitemapCandidates: [
      "/sitemap.xml",
      "/sitemap_index.xml",
      "/sitemap-index.xml",
      "/sitemapindex.xml",
      "/sitemaps/sitemap.xml",
      "/sitemaps/sitemap_index.xml",
      "/sitemaps/sitemap-index.xml",
      "/sitemaps/sitemapindex.xml",
      // also try root-level index that many sites use (works on binbaz):
      "/sitemap-index.xml",
    ],
  };

  // ---------- utils ----------
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const norm = (s) => (s || "").replace(/\s+/g, " ").trim();

  const safeUrlObj = (u, base = ORIGIN) => {
    try {
      const url = new URL(u, base);
      if (url.origin !== ORIGIN) return null;
      url.hash = "";
      return url;
    } catch {
      return null;
    }
  };

  const uniqKey = (urlObj) => {
    if (!urlObj) return null;
    return CFG.keepQueryInUniq ? urlObj.pathname + urlObj.search : urlObj.pathname;
  };

  const classifyExt = (urlObj) => {
    const p = (urlObj.pathname || "").toLowerCase();
    const exts = [
      ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
      ".mp3", ".m4a", ".wav", ".ogg",
      ".mp4", ".webm", ".m3u8",
      ".zip", ".rar", ".7z",
      ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg",
      ".css", ".js", ".json", ".xml",
    ];
    for (const e of exts) if (p.endsWith(e)) return e;
    return "(no-ext)";
  };

  const urlToPattern = (urlObj) => {
    const segs = urlObj.pathname.split("/").filter(Boolean).map((s) => decodeURIComponent(s));
    const mapped = segs.map((s) => {
      if (/^\d+$/.test(s)) return "{id}";
      if (s.length >= 16 && /[-_%]/.test(s)) return "{slug}";
      if (s.length >= 24) return "{slug}";
      return s;
    });
    return "/" + mapped.join("/");
  };

  const fetchText = async (urlStr, opts = {}) => {
    const u = safeUrlObj(urlStr);
    if (!u) return { ok: false, status: 0, url: urlStr, error: "not same-origin/invalid" };

    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), CFG.timeoutMs);

    try {
      const res = await fetch(u.toString(), { credentials: "include", signal: ac.signal, ...opts });
      const text = await res.text();
      return { ok: res.ok, status: res.status, url: u.toString(), text, headers: res.headers };
    } catch (e) {
      return { ok: false, status: 0, url: u.toString(), error: String(e) };
    } finally {
      clearTimeout(t);
    }
  };

  const isXmlish = (text, ct = "") => {
    const t = (text || "").trim();
    const c = (ct || "").toLowerCase();
    return c.includes("xml") || t.startsWith("<?xml") || t.includes("<urlset") || t.includes("<sitemapindex");
  };

  const parseXml = (xmlText) => {
    const doc = new DOMParser().parseFromString(xmlText, "text/xml");
    const root = doc.documentElement?.nodeName?.toLowerCase() || "";
    const locEls = Array.from(doc.getElementsByTagName("loc"));
    const locs = locEls.map((el) => (el.textContent || "").trim()).filter(Boolean);
    return { root, locs };
  };

  const dedup = (arr) => Array.from(new Set(arr));

  const extractFromHtml = (html, baseUrl) => {
    const doc = new DOMParser().parseFromString(html, "text/html");

    const out = {
      pageLinks: [],
      assetLinks: [],
      resourceLinks: [],
      sitemapLinks: [],
      forms: [],
      meta: [],
    };

    const push = (arr, u) => {
      const uu = safeUrlObj(u, baseUrl);
      if (!uu) return;
      arr.push(uu.toString());
    };

    // page links
    doc.querySelectorAll("a[href]").forEach((a) => push(out.pageLinks, a.getAttribute("href")));

    // assets
    doc.querySelectorAll("img[src], source[src], audio[src], video[src]").forEach((el) => {
      push(out.assetLinks, el.getAttribute("src"));
    });
    doc.querySelectorAll("a[href]").forEach((a) => {
      const href = a.getAttribute("href");
      const u = safeUrlObj(href, baseUrl);
      if (!u) return;
      const ext = classifyExt(u);
      if (ext !== "(no-ext)" && ext !== ".html") out.assetLinks.push(u.toString());
    });

    // resources: scripts + styles + iframes
    doc.querySelectorAll("script[src]").forEach((s) => push(out.resourceLinks, s.getAttribute("src")));
    doc.querySelectorAll('link[rel="stylesheet"][href]').forEach((l) => push(out.resourceLinks, l.getAttribute("href")));
    doc.querySelectorAll("iframe[src]").forEach((i) => push(out.resourceLinks, i.getAttribute("src")));

    // forms
    doc.querySelectorAll("form[action]").forEach((f) => {
      const action = f.getAttribute("action");
      const method = (f.getAttribute("method") || "GET").toUpperCase();
      const u = safeUrlObj(action, baseUrl);
      if (u) out.forms.push({ method, action: u.toString() });
    });

    // meta/canonical/alternate
    const canon = doc.querySelector('link[rel="canonical"][href]')?.getAttribute("href");
    if (canon) push(out.meta, canon);

    doc.querySelectorAll('link[rel="alternate"][href]').forEach((l) => push(out.meta, l.getAttribute("href")));

    // sitemap links discovered in page
    doc.querySelectorAll("a[href], link[href]").forEach((el) => {
      const href = el.getAttribute("href");
      const u = safeUrlObj(href, baseUrl);
      if (!u) return;
      const p = u.pathname.toLowerCase();
      if (p.includes("sitemap") && p.endsWith(".xml")) out.sitemapLinks.push(u.toString());
      if (p.includes("/sitemaps/") && p.endsWith(".xml")) out.sitemapLinks.push(u.toString());
    });

    // light heuristic: find absolute/relative urls in inline scripts (cheap regex, capped)
    const inlineScripts = Array.from(doc.querySelectorAll("script:not([src])")).slice(0, 40);
    const urlRx = /(https?:\/\/binbaz\.org\.sa\/[^\s"'<>]+|\/[a-zA-Z0-9_\-\/%]+(?:\?[^\s"'<>]+)?)/g;
    inlineScripts.forEach((s) => {
      const txt = s.textContent || "";
      let m;
      let count = 0;
      while ((m = urlRx.exec(txt)) && count < 200) {
        const candidate = m[1];
        const u = safeUrlObj(candidate, baseUrl);
        if (u) out.resourceLinks.push(u.toString());
        count++;
      }
    });

    out.pageLinks = dedup(out.pageLinks);
    out.assetLinks = dedup(out.assetLinks);
    out.resourceLinks = dedup(out.resourceLinks);
    out.sitemapLinks = dedup(out.sitemapLinks);
    out.meta = dedup(out.meta);

    return out;
  };

  // ---------- Network capture ----------
  const capture = {
    startedAt: new Date().toISOString(),
    fetch: [],
    xhr: [],
    performance: [],
    stoppedAt: null,
  };

  const origFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    try {
      const u = safeUrlObj(args[0]?.toString?.() || args[0], location.href);
      if (u) capture.fetch.push({ url: u.toString(), ts: Date.now() });
    } catch {}
    return origFetch(...args);
  };

  const origXHROpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    try {
      const u = safeUrlObj(url, location.href);
      if (u) capture.xhr.push({ method: String(method || "").toUpperCase(), url: u.toString(), ts: Date.now() });
    } catch {}
    return origXHROpen.call(this, method, url, ...rest);
  };

  const perfEntries = () => {
    const entries = performance.getEntriesByType("resource") || [];
    const out = [];
    for (const e of entries) {
      const u = safeUrlObj(e.name);
      if (!u) continue;
      out.push({
        url: u.toString(),
        initiatorType: e.initiatorType || "",
        durationMs: Math.round(e.duration || 0),
        transferSize: e.transferSize || 0,
      });
    }
    // dedup by url
    const m = new Map();
    out.forEach((x) => m.set(x.url, x));
    return Array.from(m.values());
  };

  // ---------- Collectors ----------
  const sets = {
    urlsAll: new Set(),
    urlsFromSitemaps: new Set(),
    urlsPages: new Set(),
    urlsAssets: new Set(),
    urlsResources: new Set(),
    urlsMeta: new Set(),
    sitemaps: new Set(),
  };

  const forms = [];
  const sitemapStats = [];

  const addUrl = (set, urlStr) => {
    const u = safeUrlObj(urlStr, ORIGIN);
    if (!u) return;
    const key = uniqKey(u);
    if (!key) return;
    set.add(u.toString());
    sets.urlsAll.add(u.toString());
  };

  // seed from current DOM
  (() => {
    const html = document.documentElement.outerHTML || "";
    const parts = extractFromHtml(html, location.href);

    parts.pageLinks.forEach((u) => addUrl(sets.urlsPages, u));
    parts.assetLinks.forEach((u) => addUrl(sets.urlsAssets, u));
    parts.resourceLinks.forEach((u) => addUrl(sets.urlsResources, u));
    parts.meta.forEach((u) => addUrl(sets.urlsMeta, u));
    parts.sitemapLinks.forEach((u) => sets.sitemaps.add(u));

    forms.push(...parts.forms);
  })();

  // seed performance resources
  capture.performance = perfEntries();
  capture.performance.forEach((p) => addUrl(sets.urlsResources, p.url));

  // seed: current page
  addUrl(sets.urlsPages, location.href);

  // ---------- Sitemap discovery (robots + candidates + discovered) ----------
  const seedSitemaps = async () => {
    // from robots.txt sitemap lines
    const r = await fetchText("/robots.txt");
    if (r.ok) {
      const lines = r.text.split("\n").map((s) => s.trim());
      for (const line of lines) {
        const m = line.match(/^sitemap:\s*(.+)$/i);
        if (m && m[1]) {
          const u = safeUrlObj(m[1]);
          if (u) sets.sitemaps.add(u.toString());
        }
      }
    }

    // candidates
    for (const p of CFG.sitemapCandidates) {
      const u = safeUrlObj(p);
      if (u) sets.sitemaps.add(u.toString());
    }
  };

  const processSitemaps = async () => {
    const queue = Array.from(sets.sitemaps);
    const seen = new Set();
    let processed = 0;

    while (queue.length && processed < CFG.maxSitemapsToProcess && sets.urlsFromSitemaps.size < CFG.maxUrlsToCollectFromSitemaps) {
      const sm = queue.shift();
      if (!sm || seen.has(sm)) continue;
      seen.add(sm);
      processed++;

      const r = await fetchText(sm);
      if (!r.ok) {
        sitemapStats.push({ url: sm, ok: false, status: r.status, type: "error", urlsFound: 0, error: r.error || "" });
        await sleep(CFG.delayMsBetweenRequests);
        continue;
      }

      const ct = (r.headers?.get?.("content-type") || "");
      if (!isXmlish(r.text, ct)) {
        sitemapStats.push({ url: sm, ok: true, status: r.status, type: "not-xml", urlsFound: 0 });
        await sleep(CFG.delayMsBetweenRequests);
        continue;
      }

      let parsed;
      try {
        parsed = parseXml(r.text);
      } catch (e) {
        sitemapStats.push({ url: sm, ok: false, status: r.status, type: "xml-parse-error", urlsFound: 0, error: String(e) });
        await sleep(CFG.delayMsBetweenRequests);
        continue;
      }

      const root = parsed.root || "";
      const locs = parsed.locs || [];

      if (root.includes("sitemapindex")) {
        let pushed = 0;
        for (const loc of locs) {
          const u = safeUrlObj(loc);
          if (!u) continue;
          const s = u.toString();
          if (!seen.has(s)) {
            queue.push(s);
            pushed++;
          }
        }
        sitemapStats.push({ url: sm, ok: true, status: r.status, type: "sitemapindex", urlsFound: locs.length, pushed });
      } else if (root.includes("urlset")) {
        let added = 0;
        for (const loc of locs) {
          const u = safeUrlObj(loc);
          if (!u) continue;
          const key = uniqKey(u);
          if (!key) continue;
          const s = u.toString();
          if (!sets.urlsFromSitemaps.has(s) && sets.urlsFromSitemaps.size < CFG.maxUrlsToCollectFromSitemaps) {
            sets.urlsFromSitemaps.add(s);
            sets.urlsAll.add(s);
            added++;
          }
        }
        sitemapStats.push({ url: sm, ok: true, status: r.status, type: "urlset", urlsFound: locs.length, added });
      } else {
        sitemapStats.push({ url: sm, ok: true, status: r.status, type: `xml(${root || "unknown"})`, urlsFound: locs.length });
      }

      await sleep(CFG.delayMsBetweenRequests);
    }

    return { processed, seenCount: seen.size, remainingInQueue: queue.length };
  };

  // ---------- BFS crawl fallback ----------
  const crawl = async () => {
    const queue = [];
    const seen = new Set();

    const enqueue = (u, depth) => {
      const uu = safeUrlObj(u, ORIGIN);
      if (!uu) return;
      const key = uniqKey(uu);
      if (!key || seen.has(key)) return;
      seen.add(key);
      queue.push({ url: uu.toString(), depth });
    };

    // seeds: some pages already discovered
    enqueue(location.href, 0);

    // seed from pages known so far (cap)
    Array.from(sets.urlsPages).slice(0, 100).forEach((u) => enqueue(u, 1));
    Array.from(sets.urlsFromSitemaps).slice(0, 120).forEach((u) => enqueue(u, 1)); // only a small slice; sitemap is huge

    let fetched = 0;
    let active = 0;

    const worker = async () => {
      while (true) {
        if (fetched >= CFG.maxPagesToFetch) return;
        const item = queue.shift();
        if (!item) return;
        if (item.depth > CFG.maxDepth) continue;

        fetched++;
        active++;

        const r = await fetchText(item.url);
        if (r.ok) {
          addUrl(sets.urlsPages, r.url);

          const ct = (r.headers?.get?.("content-type") || "").toLowerCase();
          const looksHtml = ct.includes("text/html") || r.text.includes("<html") || r.text.trim().startsWith("<!doctype");

          if (looksHtml) {
            const parts = extractFromHtml(r.text, r.url);

            parts.pageLinks.forEach((u) => {
              addUrl(sets.urlsPages, u);
              enqueue(u, item.depth + 1);
            });
            parts.assetLinks.forEach((u) => addUrl(sets.urlsAssets, u));
            parts.resourceLinks.forEach((u) => addUrl(sets.urlsResources, u));
            parts.meta.forEach((u) => addUrl(sets.urlsMeta, u));
            parts.sitemapLinks.forEach((u) => sets.sitemaps.add(u));
            parts.forms.forEach((f) => forms.push(f));
          }
        }

        active--;
        await sleep(CFG.delayMsBetweenRequests);
      }
    };

    const workers = Array.from({ length: CFG.concurrency }, () => worker());
    await Promise.all(workers);

    return { fetched, queueRemaining: queue.length };
  };

  // ---------- Run ----------
  console.groupCollapsed("🔎 BinBaz inventory: running…");
  console.log("CFG:", CFG);
  console.log("Seeded from DOM/pages/assets/resources/forms");
  console.groupEnd();

  await seedSitemaps();
  const sitemapRun1 = await processSitemaps();

  // crawl a bit to discover any sitemap xml links not in index + any buckets missing from sitemaps
  const crawlRun = await crawl();

  // process any newly discovered sitemaps (if crawl found more)
  const sitemapRun2 = await processSitemaps();

  // wait a bit for lazy network calls to show up in fetch/xhr hooks + performance
  await sleep(CFG.captureWaitMs);
  capture.performance = perfEntries();

  // ---------- Build report ----------
  // Merge captured network urls into resources
  capture.fetch.forEach((x) => addUrl(sets.urlsResources, x.url));
  capture.xhr.forEach((x) => addUrl(sets.urlsResources, x.url));
  capture.performance.forEach((x) => addUrl(sets.urlsResources, x.url));

  // Tables
  const allUrls = Array.from(sets.urlsAll);

  const segCounts = new Map();
  const extCounts = new Map();
  const patterns = new Map();

  const addPattern = (uStr) => {
    const u = safeUrlObj(uStr);
    if (!u) return;

    const seg0 = u.pathname.split("/").filter(Boolean)[0] || "/";
    segCounts.set(seg0, (segCounts.get(seg0) || 0) + 1);

    const ext = classifyExt(u);
    extCounts.set(ext, (extCounts.get(ext) || 0) + 1);

    const pat = urlToPattern(u);
    const e = patterns.get(pat) || { count: 0, examples: [] };
    e.count++;
    if (e.examples.length < CFG.examplesPerPattern) e.examples.push(u.toString());
    patterns.set(pat, e);
  };

  allUrls.forEach(addPattern);

  const topSegments = Array.from(segCounts.entries())
    .map(([segment, count]) => ({ segment, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 40);

  const topExts = Array.from(extCounts.entries())
    .map(([ext, count]) => ({ ext, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 40);

  const topPatterns = Array.from(patterns.entries())
    .map(([pattern, v]) => ({ pattern, count: v.count, examples: v.examples.join(" | ") }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 80);

  const report = {
    origin: ORIGIN,
    generatedAt: new Date().toISOString(),
    config: CFG,

    totals: {
      uniqueAllUrls: sets.urlsAll.size,
      uniquePages: sets.urlsPages.size,
      uniqueAssets: sets.urlsAssets.size,
      uniqueResources: sets.urlsResources.size,
      uniqueMeta: sets.urlsMeta.size,
      uniqueSitemapsSeen: sets.sitemaps.size,
      uniqueUrlsFromSitemaps: sets.urlsFromSitemaps.size,
      formsFound: forms.length,
      uniquePatterns: patterns.size,
    },

    runs: {
      sitemapRun1,
      crawlRun,
      sitemapRun2,
    },

    sitemaps: {
      discovered: Array.from(sets.sitemaps),
      stats: sitemapStats,
    },

    forms: dedup(forms.map((f) => JSON.stringify(f))).map((s) => JSON.parse(s)),

    capture: {
      ...capture,
      stoppedAt: new Date().toISOString(),
      fetch: dedup(capture.fetch.map((x) => x.url)).slice(0, 5000),
      xhr: dedup(capture.xhr.map((x) => x.url)).slice(0, 5000),
      performance: capture.performance.slice(0, 5000),
    },

    summaryTables: {
      topSegments,
      topExts,
      topPatterns,
    },

    samples: {
      pages: Array.from(sets.urlsPages).slice(0, 200),
      assets: Array.from(sets.urlsAssets).slice(0, 200),
      resources: Array.from(sets.urlsResources).slice(0, 200),
      meta: Array.from(sets.urlsMeta).slice(0, 200),
      urlsFromSitemapsSample: Array.from(sets.urlsFromSitemaps).slice(0, 300),
    },
  };

  // ---------- Save to file ----------
  const pad = (n) => String(n).padStart(2, "0");
  const d = new Date();
  const stamp = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  const filename = `binbaz_inventory_${stamp}.json`;

  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);

  // expose for inspection
  window.__BINBAZ_INVENTORY__ = report;

  // ---------- Console output ----------
  console.group("✅ BinBaz inventory complete");
  console.log("Saved:", filename);
  console.log("Full report also available as window.__BINBAZ_INVENTORY__");
  console.table([report.totals]);

  console.groupCollapsed("Top segments");
  console.table(topSegments.slice(0, 15));
  console.groupEnd();

  console.groupCollapsed("Top URL patterns");
  console.table(topPatterns.slice(0, 20));
  console.groupEnd();

  console.groupCollapsed("Sitemaps stats");
  console.table(sitemapStats);
  console.groupEnd();

  console.groupEnd();
})();