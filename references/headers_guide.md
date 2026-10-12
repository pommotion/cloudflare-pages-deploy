# Cloudflare Pages `_headers` 缓存与性能配置指南

Cloudflare Pages 支持在发布目录的根目录下放置名为 `_headers` 的纯文本文件，用于为静态资源精确控制 HTTP 响应标头（如 `Cache-Control`、CORS、安全策略）。

---

## 推荐生产级 `_headers` 配置模板

将以下内容保存为项目根目录下的 `_headers`：

```text
# 1. 字体文件缓存：极长缓存（1年）且不可变
/*.ttf
  Cache-Control: public, max-age=31536000, immutable
  Access-Control-Allow-Origin: *
/*.otf
  Cache-Control: public, max-age=31536000, immutable
  Access-Control-Allow-Origin: *
/*.woff2
  Cache-Control: public, max-age=31536000, immutable
  Access-Control-Allow-Origin: *

# 2. 多媒体音视频：7 天缓存
/*.mp4
  Cache-Control: public, max-age=604800
/*.mp3
  Cache-Control: public, max-age=604800
/*.m4a
  Cache-Control: public, max-age=604800

# 3. 静态图片：7 天缓存
/*.jpg
  Cache-Control: public, max-age=604800
/*.png
  Cache-Control: public, max-age=604800
/*.webp
  Cache-Control: public, max-age=604800
/*.svg
  Cache-Control: public, max-age=604800

# 4. JavaScript 与 CSS 样式脚本：1 天缓存
/*.js
  Cache-Control: public, max-age=86400
/*.css
  Cache-Control: public, max-age=86400

# 5. HTML 入口页面：禁止旧版本缓存（确保每次发布立即可见）
/*.html
  Cache-Control: public, max-age=0, must-revalidate
```

> **注意**：Cloudflare CDN 默认对所有静态资源自动支持 Range 请求（`Accept-Ranges: bytes`），无需在 `_headers` 中手动声明。

---

## 配置生效规则与说明

1. **放置位置**：必须位于最终上传包的根目录，即与 `index.html` 同级。
2. **通配符语义**：
   - `/*.ttf` 匹配所有路径中以 `.ttf` 结尾的 URL（包括子目录），例如 `/fonts/Noto.ttf` 和 `/sub/dir/file.ttf` 都会被匹配。
   - `*` 匹配任意数量的任意字符（包括 `/`）。
   - 参考 [Cloudflare 官方文档](https://developers.cloudflare.com/pages/configuration/headers/)。
3. **`immutable` 指令的作用**：告知现代浏览器该字体文件在缓存有效期内永不更改，即使刷新页面也不会向服务器发送 304 协商请求，瞬间完成字体渲染。
4. **HTML 必须配置 `must-revalidate`**：避免浏览器强缓存旧版 `index.html` 导致用户看不到刚发布的新功能。

