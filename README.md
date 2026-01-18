# Trae Omni-Browser Toolkit 🚀

Trae 沉浸式智能浏览与素材采集助手 (Trae Omni-Browser & Clipper) 是一个旨在消除代码编辑器与互联网物理隔离的工具集。它结合了 VS Code 的内置浏览器能力与 Python 自动化脚本，让你在不离开编辑器的情况下，将视频教程和技术文章转化为结构化的编程素材。

## ✨ 核心功能

*   **全栈内置浏览器**: 在 Trae/VS Code 侧边栏浏览 YouTube、Bilibili、抖音等视频网站。
*   **一键素材采集**: 输入视频 URL，自动提取字幕和关键信息。
*   **AI 智能炼化**: 利用 LLM (GPT/Claude) 将视频内容转化为 Markdown 笔记和可运行的代码片段。
*   **本地资产库**: 所有生成的素材自动保存到本地 `materials/` 目录。

## 🛠️ 安装与配置

### 1. Python 环境配置

确保已安装 Python 3.8+。

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
# 复制 .env.example 为 .env，并填入你的 API Key (如果没有 Key，默认使用 Mock 模式)
cp .env.example .env
```

### 2. 启动控制台

在 Trae 的终端中运行以下命令启动采集助手界面：

```bash
streamlit run app.py
```

### 3. 安装内置浏览器 (Browse Lite)

为了获得最佳体验，请在 Trae (或 VS Code) 中安装 **Browse Lite** 扩展。

1.  打开扩展商店 (Extensions)。
2.  搜索并安装 **Browse Lite** (ID: `antfu.browse-lite`)。
3.  **推荐配置**:
    *   按 `Ctrl+Shift+P` 打开命令面板。
    *   输入 `Browse Lite: Open` 即可打开内置浏览器。

**快捷键配置建议**:
打开 `keybindings.json`，添加以下配置以便快速唤起：

```json
{
    "key": "ctrl+shift+b",
    "command": "browse-lite.open",
    "when": "editorTextFocus"
}
```

## 📖 使用指南

1.  **打开浏览器**: 使用 `Ctrl+Shift+B` 唤起右侧 Browse Lite 浏览器，找到你感兴趣的技术视频。
2.  **复制链接**: 复制视频的 URL。
3.  **粘贴采集**: 在 `Streamlit` 控制台 (运行在 Trae 的 Webview 或终端中) 粘贴 URL。
4.  **生成素材**: 点击 "Analyze & Clip"。
5.  **查看结果**: 生成的 Markdown 笔记会自动保存在 `materials/` 文件夹，并显示在控制台预览中。

## 📂 目录结构

*   `src/`: 核心逻辑代码 (Clipper, Refinery, Storage)。
*   `app.py`: Streamlit 前端界面入口。
*   `materials/`: 存放生成的笔记文件。
*   `.env`: 配置文件 (API Keys)。

## ⚠️ 注意事项

*   默认开启 **Mock Mode** (模拟模式)，无需 API Key 即可体验流程。
*   如需真实数据，请在 `.env` 中配置 `SUPADATA_API_KEY` (用于视频转文字) 和 `OPENAI_API_KEY` (用于内容总结)。
