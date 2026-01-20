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

async function setToast(tabId, { text, type = 'info', ttlMs }) {
  try {
    // 1. Inject Navigation Hook in MAIN world (for SPA support)
    chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      func: () => {
        if (window.__traeMainNavHooked) return;
        window.__traeMainNavHooked = true;
        
        const suppressAndRemoveToast = () => {
          try {
            document.documentElement.dataset.traeToastSuppressed = "1";
          } catch (_) {}
          const t = document.getElementById("trae-processing-toast");
          if (t) t.remove();
        };

        const h = window.history;
        const push = h.pushState;
        const rep = h.replaceState;
        
        h.pushState = function(...args) {
          const res = push.apply(this, args);
          suppressAndRemoveToast();
          return res;
        };
        
        h.replaceState = function(...args) {
          const res = rep.apply(this, args);
          suppressAndRemoveToast();
          return res;
        };

        let lastHref = location.href;
        window.setInterval(() => {
          const cur = location.href;
          if (cur !== lastHref) {
            lastHref = cur;
            suppressAndRemoveToast();
          }
        }, 250);
      }
    }).catch(() => {});

    // 2. Inject Toast UI in ISOLATED world
    await chrome.scripting.executeScript({
      target: { tabId },
      func: ({ text, type, ttlMs }) => {
        const toastId = "trae-processing-toast";
        const styleId = "trae-toast-styles";

        const removeToastNow = () => {
          const t = document.getElementById(toastId);
          if (t) t.remove();
        };

        if (!window.__traeToastNavHooked) {
          window.__traeToastNavHooked = true;
          const suppressAndRemove = () => {
            try {
              document.documentElement.dataset.traeToastSuppressed = "1";
            } catch (_) {}
            removeToastNow();
          };
          window.addEventListener("hashchange", suppressAndRemove, true);
          window.addEventListener("popstate", suppressAndRemove, true);
          window.addEventListener("pagehide", suppressAndRemove, true);
        }
        
        const suppressed = document.documentElement?.dataset?.traeToastSuppressed === "1";
        if (suppressed) {
          removeToastNow();
          return;
        }

        // 1. Inject Styles (Idempotent)
        const styleText = `
            @keyframes traeSlideIn {
              from { transform: translateY(-20px) scale(0.8); opacity: 0; }
              to { transform: translateY(0) scale(1); opacity: 1; }
            }
            @keyframes traeFadeOut {
              from { opacity: 1; transform: scale(1); }
              to { opacity: 0; transform: scale(0.8); }
            }
            @keyframes traePulse {
              0% { transform: scale(1); opacity: 1; }
              50% { transform: scale(1.15); opacity: 0.8; }
              100% { transform: scale(1); opacity: 1; }
            }
            .trae-toast {
              position: fixed;
              top: 24px;
              right: 24px;
              z-index: 2147483647;
              display: flex;
              align-items: center;
              justify-content: center;
              pointer-events: none; /* Let clicks pass through */
              transition: all 0.3s ease;
            }
            .trae-toast-icon {
              width: 32px;
              height: 32px;
              display: flex;
              align-items: center;
              justify-content: center;
              filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
            }
            .trae-toast-icon svg {
              width: 100%;
              height: 100%;
            }
            .trae-toast.show {
              animation: traeSlideIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
            }
            .trae-toast.hiding {
              animation: traeFadeOut 0.3s ease forwards;
            }
            
            /* Theme Colors */
            .trae-icon-loading { color: #3b82f6; /* Blue */ }
            .trae-icon-success { color: #22c55e; /* Green */ }
            .trae-icon-error   { color: #ef4444; /* Red */ }
            .trae-icon-warning { color: #f59e0b; /* Amber */ }

            /* Pulse Animation for Loading */
            .trae-pulse {
              animation: traePulse 1.5s infinite ease-in-out;
            }
          `;
        let style = document.getElementById(styleId);
        if (!style) {
          style = document.createElement("style");
          style.id = styleId;
          document.head.appendChild(style);
        }
        if (style.textContent !== styleText) style.textContent = styleText;

        // 2. Icons (SVG)
        const icons = {
          // Funnel / Filter Icon for Loading
          loading: `<svg class="trae-icon-loading trae-pulse" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 18H14V16H10V18ZM3 6V8H21V6H3ZM6 13H18V11H6V13Z" />
          </svg>`,
          // Minimal Check
          success: `<svg class="trae-icon-success" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M9 16.17L4.83 12L3.41 13.41L9 19L21 7L19.59 5.59L9 16.17Z" />
          </svg>`,
          // Minimal Alert
          error: `<svg class="trae-icon-error" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
             <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM13 17H11V15H13V17ZM13 13H11V7H13V13Z" />
          </svg>`,
          warning: `<svg class="trae-icon-warning" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M1 21H23L12 2L1 21ZM13 18H11V16H13V18ZM13 14H11V10H13V14Z" />
          </svg>`
        };

        // 3. Create or Get Toast
        let toast = document.getElementById(toastId);
        if (!toast) {
          toast = document.createElement("div");
          toast.id = toastId;
          toast.className = "trae-toast";
          // Only Icon, No Text
          toast.innerHTML = `<div class="trae-toast-icon"></div>`;
          document.body.appendChild(toast);
        }

        // 4. Update Content
        const iconEl = toast.querySelector('.trae-toast-icon');
        const nextType = (icons[type] ? type : "loading");
        if (toast.dataset.traeToastType !== nextType) {
          toast.dataset.traeToastType = nextType;
          iconEl.innerHTML = icons[nextType] || icons.loading;
        }
        
        // Remove hiding class if present
        toast.classList.remove('hiding');
        toast.classList.add('show');
        
        // 5. Timer Logic
        if (toast.dismissTimeout) clearTimeout(toast.dismissTimeout);

        function hideToast() {
           toast.classList.add('hiding');
           toast.addEventListener('animationend', () => {
             if (toast.classList.contains('hiding')) {
                toast.remove();
             }
           }, { once: true });
        }

        if (typeof ttlMs === "number" && ttlMs > 0) {
           toast.dismissTimeout = setTimeout(() => {
              hideToast();
           }, ttlMs);
        }

        if (!window.__traeToastWheelHooked) {
          window.__traeToastWheelHooked = true;
          window.addEventListener(
            "wheel",
            () => {
              const host = location.hostname || "";
              const shouldDismiss =
                host.endsWith("douyin.com") || host.endsWith("bilibili.com") || host.endsWith("youtube.com");
              if (shouldDismiss) {
                try {
                  document.documentElement.dataset.traeToastSuppressed = "1";
                } catch (_) {}
                removeToastNow();
              }
            },
            { passive: true, capture: true }
          );
        }
      },
      args: [{ text, type, ttlMs }]
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
      await setToast(tabId, { text: "", type: "loading", ttlMs: 300 });
      return;
    }

    const status = data?.status;
    if (status === "queued" || status === "processing") {
      await setToast(tabId, { text: "", type: "loading" });
      await new Promise((r) => setTimeout(r, 900));
      continue;
    }

    if (status === "saved") {
      await setToast(tabId, { text: "", type: "loading", ttlMs: 300 });
      return;
    }

    if (status === "error") {
      await setToast(tabId, { text: "", type: "loading", ttlMs: 300 });
      return;
    }

    await setToast(tabId, { text: "", type: "loading", ttlMs: 300 });
    return;
  }

  await setToast(tabId, { text: "", type: "loading", ttlMs: 300 });
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
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        try {
          document.documentElement.dataset.traeToastSuppressed = "0";
        } catch (_) {}
      }
    }).catch(() => {});

    await setToast(tab.id, { text: "", type: "loading" });

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
        await setToast(tab.id, { text: "", type: "loading", ttlMs: 300 });
        return;
      }
      await pollTask({ serverUrl, taskId, tabId: tab.id });
    } else {
      throw new Error('Server returned ' + response.status);
    }
  } catch (error) {
    console.error(error);
    await setToast(tab.id, { text: "", type: "loading", ttlMs: 300 });
  }
}
