const DEFAULT_SERVER_URL = "http://127.0.0.1:18000";

async function resolveBestUrl(tab) {
  if (!tab?.id) return tab?.url;

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const currentHref = location.href;
        const canonicalHref = document.querySelector('link[rel="canonical"]')?.href;
        const ogUrl =
          document.querySelector('meta[property="og:url"]')?.content ||
          document.querySelector('meta[name="og:url"]')?.content;

        let best = currentHref;

        try {
          const u = new URL(currentHref);

          if (u.hostname.endsWith("douyin.com")) {
            const modalId = u.searchParams.get("modal_id");
            if (modalId && !u.pathname.startsWith("/video/")) {
              return { best: `https://www.douyin.com/video/${modalId}` };
            }
            if (u.pathname === "/" || u.pathname.startsWith("/user/")) {
               const renderEl = document.querySelector("#RENDER_DATA");
               if (renderEl) {
                 const raw = decodeURIComponent(renderEl.textContent || "");
                 const m = raw.match(/"aweme_id"\s*:\s*"(\d+)"/) || raw.match(/"awemeId"\s*:\s*"(\d+)"/);
                 if (m?.[1]) return { best: `https://www.douyin.com/video/${m[1]}` };
               }

               const candidates = new Set();
               for (const a of document.querySelectorAll("a[href]")) {
                 const href = a.getAttribute("href");
                 if (!href) continue;
                 let abs;
                 try {
                   abs = new URL(href, location.href).href;
                 } catch (_) {
                   continue;
                 }
                 if (abs.includes("douyin.com/video/") || abs.includes("live.douyin.com/")) {
                   candidates.add(abs);
                 }
               }
               if (candidates.size > 0) {
                 const sorted = Array.from(candidates).sort((a, b) => b.length - a.length);
                 return { best: sorted[0] };
               }
            }
          }

          if (u.hostname.endsWith("bilibili.com")) {
            if (u.pathname.startsWith("/video/")) {
              return { best: u.origin + u.pathname };
            }
          }

          if (ogUrl && ogUrl.length > currentHref.length && ogUrl.includes("/video/")) {
            best = ogUrl;
          } else if (canonicalHref && canonicalHref.length > currentHref.length && canonicalHref.includes("/video/")) {
            best = canonicalHref;
          }
        } catch (_) {}

        return { best };
      }
    });

    const resolved = results?.[0]?.result;
    const best = resolved?.best;
    if (typeof best === "string" && /^https?:\/\//i.test(best)) return best;
  } catch (_) {}

  return tab?.url;
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command === "save-page") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab) {
      let targetUrl = await resolveBestUrl(tab);

      if (!targetUrl) {
        if (tab.id != null) {
          chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => alert("❌ 无法获取当前页面链接（可能是浏览器内置页面或权限不足）")
          }).catch(() => {});
        }
        return;
      }

      handleClip(targetUrl, tab);
    }
  }
});

async function setToast(tabId, { text, background, ttlMs }) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: ({ text, background, ttlMs }) => {
        const toastId = "trae-processing-toast";
        let toast = document.getElementById(toastId);
        if (!toast) {
          toast = document.createElement("div");
          toast.id = toastId;
          toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #2196F3;
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            z-index: 999999;
            font-family: sans-serif;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: opacity 0.5s;
            max-width: 360px;
            line-height: 1.3;
            word-break: break-word;
          `;
          document.body.appendChild(toast);
        }
        if (background) toast.style.background = background;
        toast.textContent = text || "";
        toast.style.opacity = "1";
        if (typeof ttlMs === "number" && ttlMs > 0) {
          setTimeout(() => {
            toast.style.opacity = "0";
            setTimeout(() => toast.remove(), 500);
          }, ttlMs);
        }
      },
      args: [{ text, background, ttlMs }]
    });
  } catch (_) {}
}

async function pollTask({ serverUrl, taskId, tabId }) {
  const start = Date.now();
  const timeoutMs = 60000;
  while (Date.now() - start < timeoutMs) {
    let data = null;
    try {
      const r = await fetch(`${serverUrl}/api/task/${encodeURIComponent(taskId)}`, { cache: "no-store" });
      if (!r.ok) throw new Error("Task status " + r.status);
      data = await r.json();
    } catch (e) {
      await setToast(tabId, { text: "❌ Error: " + (e?.message || "poll failed"), background: "#f44336", ttlMs: 6000 });
      return;
    }

    const status = data?.status;
    if (status === "queued" || status === "processing") {
      await setToast(tabId, { text: "⏳ Processing with Trae...", background: "#2196F3" });
      await new Promise((r) => setTimeout(r, 900));
      continue;
    }

    if (status === "saved") {
      const warning = data?.warning ? `\n${data.warning}` : "";
      await setToast(tabId, { text: "✅ Saved to Trae!" + warning, background: warning ? "#FF9800" : "#4CAF50", ttlMs: 4500 });
      return;
    }

    if (status === "error") {
      await setToast(tabId, { text: "❌ Error: " + (data?.error || "unknown"), background: "#f44336", ttlMs: 6500 });
      return;
    }

    await setToast(tabId, { text: "❌ Error: Unknown task status", background: "#f44336", ttlMs: 6500 });
    return;
  }

  await setToast(tabId, { text: "❌ Error: Timeout waiting for result", background: "#f44336", ttlMs: 6500 });
}

async function handleClip(targetUrl, tab) {
  const settings = await chrome.storage.local.get({
    mode: 'raw',
    model: 'gpt-3.5-turbo',
    apiKey: '',
    baseUrl: '',
    savePath: '',
    backendUrl: DEFAULT_SERVER_URL
  });
  const serverUrl = (settings.backendUrl || DEFAULT_SERVER_URL).trim().replace(/\/+$/, '');

  const payload = {
    url: targetUrl,
    mode: settings.mode,
    model: settings.model,
    api_key: settings.apiKey,
    base_url: settings.baseUrl,
    save_path: settings.savePath
  };

  try {
    await setToast(tab.id, { text: "⏳ Processing with Trae...", background: "#2196F3" });

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 20000);

    const response = await fetch(`${serverUrl}/api/clip`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload),
      signal: controller.signal
    }).finally(() => clearTimeout(timeoutId));

    if (response.ok) {
      const data = await response.json().catch(() => ({}));
      const taskId = data?.task_id;
      if (!taskId) {
        await setToast(tab.id, { text: "✅ Saved to Trae!", background: "#4CAF50", ttlMs: 3500 });
        return;
      }
      await pollTask({ serverUrl, taskId, tabId: tab.id });
    } else {
      throw new Error('Server returned ' + response.status);
    }
  } catch (error) {
    console.error(error);
    await setToast(tab.id, { text: "❌ Error: " + (error?.message || "unknown"), background: "#f44336", ttlMs: 6500 });
  }
}
