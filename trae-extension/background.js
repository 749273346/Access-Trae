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
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const toastId = 'trae-processing-toast';
        let toast = document.getElementById(toastId);
        if (!toast) {
          toast = document.createElement('div');
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
          `;
          document.body.appendChild(toast);
        }
        toast.textContent = "⏳ Processing with Trae...";
        toast.style.opacity = '1';
      }
    }).catch(() => {});

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
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          const toast = document.getElementById('trae-processing-toast');
          if (toast) {
            toast.style.background = '#4CAF50';
            toast.textContent = "✅ Saved to Trae!";
            setTimeout(() => {
              toast.style.opacity = '0';
              setTimeout(() => toast.remove(), 500);
            }, 3000);
          } else {
            alert("✅ Saved to Trae!");
          }
        }
      });
    } else {
      throw new Error('Server returned ' + response.status);
    }
  } catch (error) {
    console.error(error);
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (msg) => {
        const toast = document.getElementById('trae-processing-toast');
        if (toast) {
          toast.style.background = '#f44336';
          toast.textContent = "❌ Error: " + msg;
          setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 500);
          }, 5000);
        } else {
          alert("❌ Error: " + msg + "\nIs server.py running?");
        }
      },
      args: [error.message]
    });
  }
}
