# Trae x 豆包：灵感桥接器 (Trae-Doubao Bridge) 开发计划

本计划旨在通过自动化脚本打通“豆包浏览器”与“Trae 编辑器”，利用豆包强大的 AI 总结能力，将有价值的信息一键同步到 Trae 本地环境，作为编程素材使用。

## 1. 架构重构 (Architecture Refactor)

我们将从“主动爬取”模式转变为“被动接收”模式。

*   **数据源 (Source)**: 豆包浏览器 AI 侧边栏 (用户手动触发总结)。
*   **传输层 (Bridge)**: 油猴脚本 (Tampermonkey Script)，注入在网页中，负责提取 AI 总结内容并发送。
*   **接收层 (Server)**: 本地 Python 服务 (基于 FastAPI)，替代原有的 Streamlit 后端逻辑，负责接收数据并保存文件。
*   **展示层 (UI)**:
    *   **Web 端**: Streamlit (保留用于管理/预览文件)。
    *   **Editor 端**: Trae 原生文件引用 (通过 `@` 调用本地 Markdown)。

## 2. 核心模块开发

### 2.1 本地接收服务 (Local Server)
*   **技术栈**: FastAPI + Uvicorn
*   **功能**:
    *   提供 `POST /api/clip` 接口，接收 JSON 数据 `{ "url": "...", "title": "...", "content": "..." }`。
    *   将接收到的内容保存为 Markdown 文件到 `materials/` 目录。
    *   支持 CORS (跨域)，允许浏览器脚本调用。

### 2.2 浏览器注入脚本 (Browser Script)
*   **技术栈**: JavaScript (Tampermonkey / UserScript)
*   **功能**:
    *   **UI 注入**: 在页面右下角悬浮一个 "Save to Trae" 按钮。
    *   **内容获取**:
        *   *自动模式*: 尝试识别豆包侧边栏的 DOM 结构 (需用户协助定位 Class)。
        *   *手动模式 (推荐)*: 监听剪贴板或用户选中的文本。用户在豆包侧边栏复制总结内容，点击按钮即可发送。
    *   **通信**: 使用 `GM_xmlhttpRequest` 或 `fetch` 将数据发送给 `localhost:8000`。

### 2.3 Trae 侧插件 (Trae Extension - MVP)
*   **目标**: 方便用户在 Trae 中查看和插入这些素材。
*   **实现**:
    *   编写一个轻量级的 VS Code Extension (`extension.ts`)。
    *   提供一个 TreeView (侧边栏视图)，列出 `materials/` 下的所有文件。
    *   点击文件名，直接将内容插入到当前光标位置 (Insert Content)。

## 3. 实施步骤

1.  **后端改造**:
    *   创建 `server.py`，实现 FastAPI 服务。
    *   保留 `app.py` 但改为读取本地文件为主的管理台。
2.  **脚本开发**:
    *   编写 `doubao_bridge.user.js`，用户需在豆包浏览器安装 Tampermonkey 插件并导入此脚本。
3.  **插件开发 (VS Code)**:
    *   初始化 `trae-clipper-extension` 目录。
    *   实现 `TreeDataProvider` 读取 `materials` 文件夹。
    *   注册命令 `traeClipper.insertNote`。

## 4. 用户工作流 (User Workflow)

1.  在豆包浏览器打开视频/网页，使用豆包 AI 总结。
2.  觉得内容不错，**复制**总结内容 (或选中)。
3.  点击页面右下角的 **"Save to Trae"** 悬浮球。
4.  回到 Trae，在侧边栏看到新素材，点击即可插入对话或代码中。

## 待确认事项
*   由于豆包侧边栏 DOM 结构封闭且多变，**“复制 + 发送”** 是最稳健的 MVP 方案。您是否接受此交互方式？(即：您复制总结，点一下悬浮球，自动发送剪贴板内容)。
