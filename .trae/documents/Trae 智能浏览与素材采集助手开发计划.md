# Trae 智能浏览与素材采集助手 (Trae Omni-Browser & Clipper) 开发计划

根据产品说明书，我们将分阶段构建此软件。核心将由 Python 后端驱动逻辑处理，并使用 Streamlit 构建交互界面，配合 VS Code 的 Browse Lite 插件实现完整体验。

## 1. 项目初始化与环境搭建 (Phase 0)
*   **目标**: 建立项目基础结构，配置依赖管理。
*   **任务**:
    *   创建项目目录结构：
        *   `src/`: 核心源代码
        *   `app/`: Streamlit 前端代码
        *   `materials/`: 默认的本地资产库（存放生成的笔记）
    *   创建 `requirements.txt`: 包含 `streamlit`, `requests`, `python-dotenv`, `openai` 等依赖。
    *   创建 `.env.example`: 配置文件模板，用于存放 Supadata API Key 和 LLM API Key。
    *   更新 `README.md`: 添加开发与使用指南。

## 2. 核心功能开发：后端逻辑 (Phase 1 & 2)
*   **目标**: 实现视频采集与内容转化的核心逻辑。
*   **任务**:
    *   **采集模块 (`src/clipper.py`)**:
        *   实现 `VideoClipper` 类。
        *   集成 Supadata API (或模拟接口) 用于获取视频字幕。
        *   实现 URL 类型检测 (YouTube/Bilibili/TikTok)。
    *   **AI 炼化模块 (`src/refinery.py`)**:
        *   集成 LLM 调用 (支持 OpenAI/Claude 格式)。
        *   实现 Prompt Engineering：针对代码教程、概念讲解等不同类型生成特定的 Markdown 模板。
    *   **文件存储模块 (`src/storage.py`)**:
        *   将生成的 Markdown 和代码片段自动保存到 `materials/` 目录。

## 3. 界面集成：Streamlit 控制台 (Phase 3)
*   **目标**: 提供可视化的操作界面，嵌入 Trae/VS Code 中使用。
*   **任务**:
    *   开发 `app.py`:
        *   **输入区**: 接收视频 URL。
        *   **配置区**: 设置 API Keys 和保存路径。
        *   **状态显示**: 显示采集进度和处理日志。
        *   **预览区**: 即时预览生成的 Markdown 内容。

## 4. 插件配置与文档
*   **目标**: 指导用户完成 Browse Lite 的环境配置。
*   **任务**:
    *   编写“Browse Lite 集成指南”，指导用户安装推荐的 VS Code 浏览器插件。
    *   提供快捷键配置建议 (`keybindings.json` 片段)。

## 待确认事项
*   您是否已有 Supadata 和 LLM (如 OpenAI/Claude) 的 API Key？如果没有，开发阶段将提供 Mock (模拟) 模式以供测试。
