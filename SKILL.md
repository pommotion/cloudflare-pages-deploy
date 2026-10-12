---
name: cloudflare-pages-deploy
description: >-
  Best practices, deployment procedures, and troubleshooting for deploying static web projects,
  code MVs, media sites, and large asset projects to Cloudflare Pages via Direct Upload (Wrangler CLI
  or Dashboard). Use whenever the user wants to upload, deploy, host, optimize, or troubleshoot static web
  projects on Cloudflare Pages, particularly when dealing with large assets (fonts, video/audio), upload
  timeouts (UND_ERR_HEADERS_TIMEOUT), batching limits, CJK font subsetting, caching headers, or domestic network proxies.
  Also use when the user mentions "deploy website", "static site hosting", "publish to Cloudflare",
  "Wrangler deploy", "upload timeout", "font too large", "字体太大", "部署网页", or "上传超时".
---

# Cloudflare Pages 静态项目极速部署与排障指南

本技能总结了将大型静态网站、HTML5 多媒体工程、代码生成 MV 及前端项目部署至 Cloudflare Pages 的全流程最佳实践与实战避坑经验。

---

## 目录结构与规范

```
cloudflare-pages-deploy/
├── SKILL.md
├── scripts/
│   ├── subset_fonts.py      # CJK 中文字库自动提取与极速子集化脚本
│   ├── pack_deploy_zip.py   # 规范打包脚本（根目录对齐与垃圾文件过滤）
│   └── patch_wrangler.py    # 优化 Wrangler 上传并发与超时的自动化补丁脚本
└── references/
    ├── troubleshooting.md       # 常见报错与排障字典（未知错误、超时等）
    ├── headers_guide.md         # _headers 性能缓存与安全配置指南
    └── player_architecture.md   # 富媒体播放器 Web 兼容性指南
```

---

## 核心部署工作流

```
[1. 资产审查与瘦身] ──> [2. 字体子集化] ──> [3. 写入 _headers] ──> [4. 认证与代理配置] ──> [5. 部署发布]
```

### 1. 资产审查与瘦身（Pre-flight Checks）

在部署前，务必审查工程目录，遵循以下硬性限制与建议：

1. **单文件限制**：Cloudflare Pages 免费/付费版均限制**单文件最大不超过 25 MiB**。
   - 检查是否有大视频、大 PSD 或全量字库超过 25 MB。
2. **剔除非网页运行文件**：
   - 移除开发阶段的离线渲染脚本（`tools/`、`analysis/`、`docs/`）。
   - 移除离线生图底图（例如原始 PNG、中间帧），只保留网页实际引用的生产素材（如 `media/clips/*.mp4`）。
   - 检查并移除 `.DS_Store`、`.git/`、`node_modules/`、`.bak` 等临时文件。
3. **音频/视频格式精简**：
   - 如果代码只引用 `.mp3`，无需同时上传未引用的 `.m4a` 或备份音轨。

---

### 2. CJK 中文字体极速子集化（Font Subsetting）

#### 为什么必须子集化？
完整的开源思源宋体/黑体（`Noto Serif SC` / `Noto Sans SC`）单字库包含 30,000+ 字符，体积高达 **17~25 MB**。若直接上线：
- 首次加载需要耗费几十秒下载 40MB 字体，用户体验极差。
- 在上传阶段也会因为巨型单文件容易触发网络超时。

#### 解决方案：提取工程字符并子集化
静态网页、动态代码 MV 或歌词项目的文本是有限且确定的。利用 Python 的 `fontTools.subset`，可将字库从 **25 MB 压缩到 300~600 KB**（缩减 98%），实现毫秒级秒开：

```bash
# 运行配套脚本自动扫描工程所有文本并子集化全部 .ttf/.otf 字库：
python3 ~/.gemini/config/skills/cloudflare-pages-deploy/scripts/subset_fonts.py \
  --project-dir <工程根目录> \
  --all-fonts
# 或仅子集化指定字体：
# python3 ...subset_fonts.py -d <工程根目录> --font <字体路径>
```

> **注意**：子集化时务必包含：
> 1. 项目内所有 `.js`、`.json`、`.html`、`.lrc` 中的实际文本；
> 2. 界面公共提示词（如“点击播放”、“载入中”、“暂停”等）；
> 3. 常见数字、英文字母、全半角标点符号及特殊数学/箭头符号。

---

### 3. 配置 `_headers` 长期缓存

Cloudflare Pages 会自动读取部署根目录下的 `_headers` 文件。对于音频、视频切片和静态字体，必须注入长期强缓存策略，否则重复访问会重新请求源站：

在项目**根目录**创建 `_headers`（详见 `references/headers_guide.md`）：
```ini
# 字体 1 年不可变缓存
/*.ttf
  Cache-Control: public, max-age=31536000, immutable
/*.woff2
  Cache-Control: public, max-age=31536000, immutable

# 音视频 7 天缓存
/*.mp4
  Cache-Control: public, max-age=604800
/*.mp3
  Cache-Control: public, max-age=604800

# HTML 禁止缓存旧版
/*.html
  Cache-Control: public, max-age=0, must-revalidate
```

---

### 4. 部署途径与避坑指南

Cloudflare Pages 提供两种直接部署方式（Direct Upload）：

#### 方式 A：Wrangler CLI（推荐，全自动）

1. **环境代理设置**（国内网络必需，端口号请根据本地代理软件实际配置替换）：
   ```bash
   export https_proxy=http://127.0.0.1:<代理端口> http_proxy=http://127.0.0.1:<代理端口>
   ```
2. **账号认证**：
   - 首次在终端执行 `npx wrangler login` 完成 OAuth 授权。
   - 或配置环境变量 `CLOUDFLARE_API_TOKEN`。
3. **预先创建项目**（防止交互式中断）：
   ```bash
   npx wrangler pages project create <project-name> --production-branch=main --force
   ```
4. **一键部署**：
   ```bash
   npx wrangler pages deploy <工程绝对路径> --project-name=<project-name> --branch=main --commit-dirty=true
   ```

##### 遇到 `HeadersTimeoutError` / `UND_ERR_HEADERS_TIMEOUT` 的彻底解法：
Wrangler 默认采用并发 3 通道、单包 40MB 的 Base64 上传机制，并且 Node.js 底层 `undici` 有 5 分钟硬超时。大文件在弱网环境下容易超时断连。
运行配套优化补丁脚本即可根除：
```bash
python3 ~/.gemini/config/skills/cloudflare-pages-deploy/scripts/patch_wrangler.py
```
*(将桶大小由 40MB 优化为 4MB 单通道串行，并将超时放宽至 30 分钟)*

---

#### 方式 B：控制台网页拖拽（Dashboard Drag-and-Drop）

如果使用网页端直接拖拽，**严禁直接全选文件拖入**，必须使用规范的单文件 `.zip` 包：

1. **为什么不能全选文件拖拽？**
   - 浏览器拖拽散落文件时无法递归保留子目录，导致所有文件扁平化在根目录，发生 `index.html` 同名冲突；
   - 浏览器并发请求上百个文件易被网络瞬时拦截，抛出“**128/129 个文件无法上传：未知**”。
2. **正确做法：单文件 `.zip` 根目录对齐**：
   - 使用打包脚本生成 `.zip`：确保 `index.html` 和 `_headers` 直接位于 `.zip` 内部根目录，不能多嵌套一层同名父级文件夹。
   - 直接把单个 `.zip` 文件拖入 Cloudflare 控制台，Cloudflare 云端会在服务端自动解压并完整保留目录层级。

---

## 富媒体播放器适配

如果部署的项目包含音视频播放器（代码 MV、切片视频合成等），请阅读 `references/player_architecture.md` 了解 `file://` CORS 限制、音频自动播放策略解耦、流式分段加载等关键兼容性要求。
