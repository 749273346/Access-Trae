// ==UserScript==
// @name         Trae-Doubao Bridge
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  将豆包浏览器的总结一键发送到 Trae 本地服务
// @author       Trae Assistant
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setClipboard
// @grant        GM_notification
// @connect      localhost
// ==/UserScript==

(function() {
    'use strict';

    // 配置
    const TRAE_SERVER_URL = "http://localhost:8000/api/clip";

    // 创建悬浮球
    function createFloatingButton() {
        const btn = document.createElement('div');
        btn.id = 'trae-bridge-btn';
        btn.innerHTML = '💾 Trae';
        btn.style.cssText = `
            position: fixed;
            bottom: 100px;
            right: 20px;
            width: 60px;
            height: 60px;
            background: #6200ea;
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 60px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            z-index: 999999;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
            user-select: none;
        `;

        btn.onmouseover = () => btn.style.transform = 'scale(1.1)';
        btn.onmouseout = () => btn.style.transform = 'scale(1)';
        
        btn.onclick = async () => {
            btn.innerHTML = '⏳';
            try {
                // 1. 尝试获取剪贴板内容
                let content = '';
                try {
                    content = await navigator.clipboard.readText();
                } catch (e) {
                    content = window.getSelection().toString();
                }

                if (!content || content.trim().length === 0) {
                    alert('请先复制或选中要发送的内容！');
                    btn.innerHTML = '💾 Trae';
                    return;
                }

                // 2. 发送到 Trae Server
                GM_xmlhttpRequest({
                    method: "POST",
                    url: TRAE_SERVER_URL,
                    headers: {
                        "Content-Type": "application/json"
                    },
                    data: JSON.stringify({
                        title: document.title || "Doubao Clip",
                        url: window.location.href,
                        content: content
                    }),
                    onload: function(response) {
                        if (response.status === 200) {
                            btn.innerHTML = '✅';
                            setTimeout(() => btn.innerHTML = '💾 Trae', 2000);
                        } else {
                            console.error("Trae Bridge Error:", response);
                            btn.innerHTML = '❌';
                            alert('发送失败，请检查 Trae Server 是否运行 (localhost:8000)');
                        }
                    },
                    onerror: function(err) {
                        console.error("Trae Bridge Error:", err);
                        btn.innerHTML = '❌';
                        alert('连接失败，请确保 Trae Server 已启动');
                    }
                });

            } catch (err) {
                console.error(err);
                btn.innerHTML = '❌';
            }
        };

        document.body.appendChild(btn);
    }

    // 初始化
    window.addEventListener('load', createFloatingButton);

})();
