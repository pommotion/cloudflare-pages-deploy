# Cloudflare Pages 故障排除与常见问题全解析 (Troubleshooting Guide)

本参考文档汇总了在将富媒体/静态网页项目部署至 Cloudflare Pages 过程中可能遇到的关键问题、底层原理与最佳解决方案。

---

## 1. Web 控制台拖拽上传报错：“XXX 个文件无法上传：未知”

### 现象
在 Cloudflare Pages 的 Web 控制台页面（Direct Upload）选择上传文件夹或批量拖拽文件时，提示类似：
- `128/129 个文件无法上传：128 未知`
- `166/167 个文件无法上传：166 未知`
列表里只有第一个文件上传成功，其余全部报错“未知”。

### 原因分析
1. **路径结构扁平化冲突**：浏览器在批量拖拽或选择多个文件夹时，部分环境不会保留相对子路径，导致同名文件（如多个子目录下的 `index.html` 或资源文件）发生路径碰撞覆盖。
2. **根目录索引缺失**：Cloudflare 要求包内必须直接包含根目录的 `index.html`。如果用户拖拽的是包含外层包装文件夹的目录，会导致根路径判定异常。
3. **HTTP 批量请求并发被拦截**：大量小文件连续发起单次 API 调用，受本地代理软件或网络波动干扰中断。

### 解决方案
- **必须上传根对齐的 `.zip` 压缩包**：不要在网页端直接选择成百上千个散装文件，使用 `scripts/pack_deploy_zip.py` 或系统命令将项目根目录（直接包含 `index.html` 的层级）打成单个 `.zip` 包后再拖拽上传。
- 确认 `.zip` 解压时第一层就是 `index.html`，没有多余的外层包装目录。

---

## 2. Wrangler CLI 部署超时：`UND_ERR_HEADERS_TIMEOUT`

### 现象
执行 `npx wrangler pages deploy` 时，进度条卡在 `Uploading... (x/y)`，等待约 5 分钟后抛出异常：
```text
TypeError: fetch failed
  [cause]: HeadersTimeoutError: Headers Timeout Error
    code: 'UND_ERR_HEADERS_TIMEOUT'
```

### 底层机理
1. **Base64 膨胀与超大分块**：Wrangler 源码中默认 `MAX_BUCKET_SIZE = 50 * 1024 * 1024`（50MB）。Wrangler 将静态资源转成 Base64 编码的 JSON 发送给 Cloudflare API，体积增加约 33%（实际达 65MB 左右）。
2. **多线程并发堵塞**：默认 `BULK_UPLOAD_CONCURRENCY = 3`，同时上传 3 个超大分块。
3. **Node.js undici 5分钟超时限制**：Node 内部 HTTP 客户端 `undici` 默认硬编码 `headersTimeout = 300000`（5分钟）。在本地代理（如 Clash 7897 端口）或国内跨境上传带宽有限时，5分钟内无法传输完成 65MB 的 payload，导致强制断开。

### 解决方案
1. **使用自动化补丁脚本**：
   ```bash
   python3 scripts/patch_wrangler.py
   ```
   该脚本会将 `MAX_BUCKET_SIZE` 缩减为 4MB，并发设为 1，并将 `headersTimeout` 放宽至 30 分钟（1800000ms）。
2. **配置终端代理环境变量**（端口号请替换为本地代理软件实际端口）：
   ```bash
   export http_proxy="http://127.0.0.1:<代理端口>"
   export https_proxy="http://127.0.0.1:<代理端口>"
   export all_proxy="socks5://127.0.0.1:<代理端口>"
   ```

---

## 3. Cloudflare Pages 限制规则

| 限制项 | 免费版 / 付费版上限 | 规避方案 |
| :--- | :--- | :--- |
| **单个文件最大体积** | 25 MiB | 压缩视频至 1080p/720p，或将大视频托管至 R2 / Stream |
| **单次部署文件总数** | 20,000 个 | 移除不必要的开发中间产物、临时切片、文档源码 |
| **单次部署总大小** | 无严格硬性限制，但单文件 <= 25MB | 提前提取字体子集，压缩音频/视频 |
| **自定义路由重写规则** | 100 条 (`_routes.json`) | 静态网站通常无需重写，SPA 使用单页 fallback |

---

## 4. CJK 中文字体导致网页加载极慢

### 现象
页面首次打开需要等待数十秒甚至一分钟，背景音乐或动效播放卡顿，开发者工具 Network 面板显示 `NotoSerifSC.ttf` 或 `NotoSansSC.ttf` 下载体积高达 17MB~25MB。

### 解决方案
使用 `fonttools` 提取项目字符子集：
```bash
# 自动扫描项目中所有 .html, .js, .json, .lrc 文件并裁剪字体
python3 scripts/subset_fonts.py --project-dir ./my-project --all-fonts
```
- **效果**：字体文件从 24.5 MB 裁剪至 400~600 KB（压缩率 97%+）。
- **保留特性**：保留可变字体轴（`fvar`, `gvar`, `STAT`）及 OpenType 排版特性，字形与动态效果完全一致。

---

## 5. 本地预览无法播放音视频或黑屏

### 现象
双击 `index.html`（通过 `file:///` 协议打开）时：
- 控制台报错：`Access to script at '...' from origin 'null' has been blocked by CORS policy`。
- 音频报错：`NotAllowedError: play() failed because the user didn't interact with the document first`。
- 视频黑屏或控制面板不可点击。

### 解决方案
1. **切勿使用 `file://` 双击打开**：ES Modules (`import`) 和 `fetch()` 请求在本地文件协议下会被浏览器同源策略拦截。
2. **使用简易本地 HTTP 服务器**：
   ```bash
   npx serve -l 3000
   # 或
   python3 -m http.server 8000
   ```
3. **音频自动播放策略**：现代浏览器强制要求用户在页面上有过交互（点击、按键）后才允许播放声音。页面首屏必须提供“点击开始 / 点击播放”按钮，触发 `audio.play()`。

---

## 6. 富媒体播放器架构设计坑点

### 错误实践（全量预加载）
```javascript
// 危险：不要在播放前将所有片段转为 Blob URL
const allBlobs = await Promise.all(videoUrls.map(url => fetch(url).then(r => r.blob())));
```
**后果**：内存溢出崩溃、首屏卡死几十秒无法进入。

### 正确实践（流式分段播放 + 异步解耦）
1. 直接让 `<video src="V01.mp4">` 进行原生 Range 分块流式拉取。
2. 将 Canvas 动效主循环与音视频解码解耦：音频负责时钟参考（时间轴驱动），渲染循环通过 `requestAnimationFrame` 依据当前音频时间轴渲染，即使单帧掉帧也不会中断音频播放。
