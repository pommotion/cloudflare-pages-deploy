# Cloudflare Pages Deploy 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Cloudflare Pages](https://img.shields.io/badge/Cloudflare-Pages-F38020?logo=cloudflare&logoColor=white)](https://pages.cloudflare.com/)
[![Wrangler](https://img.shields.io/badge/CLI-Wrangler-orange)](https://developers.cloudflare.com/workers/wrangler/)

> **一站式 Cloudflare Pages 静态项目极速部署、性能优化与排障工具箱 / AI Agent Skill**

本仓库总结并封装了将大型静态网站、HTML5 多媒体工程、代码生成 MV 及前端产物通过 **Direct Upload（Wrangler CLI / Web 控制台）** 部署至 Cloudflare Pages 的全流程自动化脚本、排障字典与最佳实践。

无论是作为独立命令行工具使用，还是作为 **AI Coding Agent（Google Antigravity, Cursor, Claude Code, Windsurf 等）** 的 Skill 载入，均能极大提升静态工程的上线效率与稳定性。

---

## 🎯 解决的核心痛点

| 痛点场景 | 根本原因 | 解决方案与工具 |
| :--- | :--- | :--- |
| **中文字库加载极慢 (25MB+)** | 思源宋体/黑体全量字库含 30,000+ 字形，耗时几十秒且易触发上传超时 | `subset_fonts.py`：自动扫描工程所有源码与歌词文本，无损裁剪保留排版轴，**体积缩减 98%（瘦身至 300~600KB）** |
| **Wrangler 部署超时断连** | Wrangler 默认并发 3 通道、单包 40MB Base64 负载，在代理/弱网下触发 Node.js `undici` 5分钟 `UND_ERR_HEADERS_TIMEOUT` | `patch_wrangler.py`：智能定位并热修 Wrangler 运行时，单包缩减为 4MB 串行，超时放宽至 30 分钟 |
| **控制台批量拖拽报错“未知”** | 浏览器扁平化拖拽导致目录结构丢失同名冲突，或并发请求数超限 | `pack_deploy_zip.py`：根目录层级对齐打包，自动拦截超限大文件，智能注入 `_headers` |
| **音视频重复拉取与卡顿** | 静态站点未针对多媒体文件配置长期不可变缓存与 CDN 策略 | `references/headers_guide.md`：生产级 `_headers` 长期缓存与 CORS 配置模板 |
| **本地双击黑屏与音视频报错** | 浏览器严格禁止 `file://` 协议下的 ES Module (`import`) 与未交互音频自动播放 | `references/player_architecture.md`：本地微服务调试与多媒体架构解耦指南 |

---

## 📁 目录结构

```text
cloudflare-pages-deploy/
├── SKILL.md                 # AI Agent 技能定义文件（规范、上下文与自动化指令）
├── README.md                # 详细使用说明与实战文档
├── LICENSE                  # MIT 开源许可证
├── scripts/                 # 核心自动化工具脚本
│   ├── subset_fonts.py      # CJK 中文字库自动提取与极速子集化脚本
│   ├── patch_wrangler.py    # 优化 Wrangler 上传并发与超时的自动化补丁脚本
│   └── pack_deploy_zip.py   # 生产级打包脚本（根目录对齐、大小预检与 _headers 注入）
└── references/              # 专项参考手册与排障字典
    ├── troubleshooting.md   # 常见报错与排障字典（超时、并发、限制规则）
    ├── headers_guide.md     # _headers 性能缓存、不可变策略与 CORS 指南
    └── player_architecture.md # Web 富媒体播放器、流式分段与兼容性架构指南
```

---

## 🛠️ 核心脚本使用指南

### 1. CJK 中文字体极速子集化 (`subset_fonts.py`)

完整的开源中文字体（如 `Noto Serif SC` / `Noto Sans SC`）单文件高达 **17~25 MB**。本项目脚本能够递归扫描工程内所有 HTML、JS、JSON、LRC 歌词，提取实际用到的汉字、标点与常用符号进行定向裁剪：

```bash
# 安装依赖
pip3 install fonttools brotli

# 自动扫描工程文本并对目录内所有 .ttf / .otf 执行子集化瘦身
python3 scripts/subset_fonts.py --project-dir /path/to/your-project --all-fonts

# 或者仅裁剪指定字体文件
python3 scripts/subset_fonts.py --project-dir /path/to/your-project --font /path/to/font.ttf
```

> **压缩效果**：原字体 24.5 MB $\to$ 子集化后约 400 KB，秒开加载，完整保留可变字体轴（`fvar`, `gvar`）。

---

### 2. Wrangler 上传超时与并发优化补丁 (`patch_wrangler.py`)

在使用 `npx wrangler pages deploy` 时，国内网络或代理环境常遇到：
```text
TypeError: fetch failed
  [cause]: HeadersTimeoutError: Headers Timeout Error
    code: 'UND_ERR_HEADERS_TIMEOUT'
```
运行本补丁自动检测当前全局或当前项目的 Wrangler 安装，并将单包上传限制调整为 4MB 串行，超时放宽至 30 分钟：

```bash
python3 scripts/patch_wrangler.py
```

执行后直接重新运行 `npx wrangler pages deploy` 即可丝滑上传大体积工程。

---

### 3. 部署打包与预检工具 (`pack_deploy_zip.py`)

当选择通过 Cloudflare 控制台网页拖拽上传时，必须确保 `.zip` 包直接以 `index.html` 为根目录，且过滤无用开发文件：

```bash
# 规范打包
python3 scripts/pack_deploy_zip.py --source /path/to/dist --output ./deploy.zip
```

**脚本自动执行：**
- ✅ 检查根目录下是否存在 `index.html`。
- ✅ 检查是否存在超过 Cloudflare Pages 单文件上限（25 MiB）的文件。
- ✅ 过滤 `.DS_Store`、`.git`、`node_modules`、开发切片等垃圾文件。
- ✅ 若项目中缺少 `_headers`，自动生成并注入长期强缓存配置。

---

## 🚀 部署全流程最佳实践

### 流程概览

```mermaid
flowchart LR
    A[1. 资产清理与瘦身] --> B[2. 字体提取子集化]
    B --> C[3. 注入 _headers 缓存]
    C --> D[4. 终端代理与账号认证]
    D --> E[5. 一键发布上线]
```

### 推荐：Wrangler CLI 全自动部署

1. **设置终端代理**（国内环境必需）：
   ```bash
   export http_proxy="http://127.0.0.1:7897"
   export https_proxy="http://127.0.0.1:7897"
   ```
2. **账号认证**：
   ```bash
   npx wrangler login
   ```
3. **预先创建项目**（避免交互式中断）：
   ```bash
   npx wrangler pages project create <项目名> --production-branch=main --force
   ```
4. **一键上传部署**：
   ```bash
   npx wrangler pages deploy <构建目录绝对路径> --project-name=<项目名> --branch=main --commit-dirty=true
   ```

---

## ⚡ HTTP 响应头配置 (`_headers`)

Cloudflare Pages 会自动解析部署根目录下的 `_headers`。在项目根目录下放置如下配置：

```text
# 字体 1 年不可变强缓存
/*.ttf
  Cache-Control: public, max-age=31536000, immutable
  Access-Control-Allow-Origin: *
/*.otf
  Cache-Control: public, max-age=31536000, immutable
  Access-Control-Allow-Origin: *
/*.woff2
  Cache-Control: public, max-age=31536000, immutable
  Access-Control-Allow-Origin: *

# 音视频媒体 7 天缓存
/*.mp4
  Cache-Control: public, max-age=604800
/*.mp3
  Cache-Control: public, max-age=604800

# HTML 入口禁止陈旧缓存（发布后立即生效）
/*.html
  Cache-Control: public, max-age=0, must-revalidate
```

---

## 🤖 作为 AI Agent Skill 安装

### Google Antigravity / Gemini CLI
将本目录克隆或软链接至 Agent 的 skills 目录：
```bash
ln -s /path/to/cloudflare-pages-deploy ~/.gemini/config/skills/cloudflare-pages-deploy
```

### Claude / Cursor / Windsurf
直接在项目 `.cursorrules`、`.claude/skills` 或系统提示词中引用 `SKILL.md`，Agent 将自动在涉及 Cloudflare Pages 部署、静态优化、字体裁剪、排障时调用对应流程与脚本。

---

## 📄 许可协议

本项目基于 [MIT 许可证](LICENSE) 开源。
