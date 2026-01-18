# 产品说明书：Trae 沉浸式智能浏览与素材采集助手 (Trae Omni-Browser & Clipper)

**版本**: 1.0  
**日期**: 2026-01-18  
**作者**: Trae AI Assistant  
**目标用户**: 开发者、技术自媒体、需要频繁查阅视频资料的学习者

---

## 1. 产品愿景 (Product Vision)

**“消除编辑器与互联网的物理隔离。”**

旨在为 Trae 用户提供一种“人剑合一”的编程体验：在不离开代码编辑器的前提下，能够无障碍地访问任意现代网站（包括抖音、YouTube 等强反爬/强交互网站），并能通过“一键操作”将视频、文章转化为结构化的编程素材（代码片段、摘要、教程），实现从**信息获取**到**代码实现**的毫秒级闭环。

## 2. 核心痛点 (Pain Points)

1.  **信息割裂 (Context Switching)**：
    *   *现状*：写代码时需要频繁 `Alt+Tab` 切换到 Chrome 浏览器查资料、看视频教程。
    *   *后果*：打断心流，窗口管理混乱，复制粘贴效率低下。
2.  **素材整理繁琐 (Inefficient Harvesting)**：
    *   *现状*：看到好的视频教程，需要手动暂停、截图、OCR 代码、自己写笔记。
    *   *后果*：收藏夹吃灰，真正用的时候找不到，知识无法转化为生产力。
3.  **编辑器浏览器兼容性差 (Technical Limitation)**：
    *   *现状*：VS Code/Trae 自带的 Simple Browser 无法打开抖音、B站（黑屏、白屏），受限于 `X-Frame-Options` 和 DRM 保护。

## 3. 解决方案与功能模块 (Solution & Features)

### 3.1 模块一：全栈内置浏览器 (The Omni-Browser)
*   **技术核心**：基于 **Browse Lite** (Headless Chrome) 内核，而非简单的 Webview/Iframe。
*   **功能描述**：
    *   **真实浏览器体验**：支持 Cookies、LocalStorage、插件扩展，完美渲染 React/Vue 动态网页。
    *   **突破限制**：能够正常播放 YouTube、抖音、Bilibili 等流媒体视频，无视 `X-Frame-Options` 限制。
    *   **侧边栏驻留**：默认停靠在编辑器右侧，支持拖拽分屏，实现“左边写代码，右边看视频”。

### 3.2 模块二：“灵感胶囊”采集器 (One-Click Clipper)
*   **技术核心**：Context Menu Extension (右键菜单扩展) + Python Backend。
*   **交互流程**：
    1.  用户在内置浏览器中看到感兴趣的视频。
    2.  点击浏览器工具栏的“**采集素材**”按钮（或右键 -> *Trae Clip This*）。
    3.  系统自动捕获当前 URL 和时间戳。

### 3.3 模块三：AI 智能炼化工厂 (AI Refinery)
*   **技术核心**：**Supadata API** (视频转文字) + **LLM (Claude/GPT)** (内容分析)。
*   **处理逻辑**：
    *   **视频 -> 文本**：自动提取视频字幕（支持中英双语）。
    *   **文本 -> 知识**：
        *   *如果是代码教程*：提取其中的代码逻辑，转换为 Python/JS 代码块。
        *   *如果是概念讲解*：生成 TL;DR 摘要和思维导图。
        *   *如果是口播素材*：生成改写后的口播文案。

### 3.4 模块四：本地资产库 (Local Asset Library)
*   **存储位置**：用户指定的本地目录（如 `E:\Working overseas\AI tools\Materials`）。
*   **输出格式**：
    *   **Markdown 笔记**：包含视频标题、摘要、核心观点。
    *   **Code Snippets**：可直接运行的代码文件。
    *   **Metadata**：原视频链接、采集时间、标签。

## 4. 技术实现路径 (Technical Implementation Path)

### Phase 1: 基础浏览环境搭建 (已完成部分)
- [x] **安装 Browse Lite**：利用其嵌入式 Chromium 内核解决黑屏问题。
- [ ] **配置快捷入口**：设置快捷键 `Ctrl+Shift+B` 直接唤起浏览器并聚焦地址栏。

### Phase 2: 自动化采集脚本 (核心开发)
我们将编写一个 Python 服务 (`video_clipper.py`) 驻留在后台，配合 Trae 的终端使用。

```python
# 伪代码逻辑演示
def on_user_clip(url):
    # 1. 识别 URL 类型 (抖音/YouTube/博客)
    platform = detect_platform(url)
    
    # 2. 调用 Supadata 获取原始内容
    raw_data = supadata.get_transcript(url)
    
    # 3. 调用 AI 进行总结
    summary = llm.analyze(raw_data, output_format="markdown")
    
    # 4. 写入本地知识库
    save_to_markdown(summary, "E:/Working overseas/AI tools/Materials")
```

### Phase 3: 界面集成 (UI Integration)
*   使用 **Streamlit** 构建一个轻量级控制面板，嵌入在 Trae 的 Webview 中，作为“采集控制台”。
*   用户只需把 Browse Lite 里的链接复制到控制台，点击“分析”，即可在当前编辑器内生成结果。

## 5. 用户使用剧本 (User Scenario)

**场景：学习 Python 自动化**

1.  **打开 Trae**，按下快捷键唤起右侧 **Omni-Browser**。
2.  输入抖音网址，刷到一个“5分钟用 Python 操作 Excel”的视频。
3.  **觉得很有用**，想要代码。
4.  **复制链接**，粘贴到下方的 **Trae Clipper 控制台**，点击“提取”。
5.  **10秒后**，左侧项目栏自动生成 `python_excel_automation.md`。
6.  打开文件，里面已经写好了视频里演示的 `pandas` 代码和操作步骤。
7.  **直接复制代码** 到自己的 `main.py` 中运行。

---

**总结**：
本产品将彻底改变用户获取编程知识的方式，从“被动观看”转变为“主动采集与利用”，真正实现信息流到代码流的无缝转换。
