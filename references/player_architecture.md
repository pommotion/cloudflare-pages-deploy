# 富媒体 Web 播放器架构与兼容性指南

多媒体工程（代码 MV、切片视频合成等）在 Web 端上线时，需要注意以下关键兼容性问题。

---

## 1. 禁止在本地 `file://` 下直接双击运行

浏览器安全策略严格禁止 `file://` 协议加载 ES Module（`type="module"`）和执行 Fetch API。

**现象**：
- 控制台报错：`Access to script at '...' from origin 'null' has been blocked by CORS policy`
- 音频报错：`NotAllowedError: play() failed because the user didn't interact with the document first`

**解决方案**：本地预览必须启动 HTTP 服务：
```bash
npx serve -l 3000
# 或
python3 -m http.server 8080
```

---

## 2. 避免前置阻塞式 Promise.all 预载大量视频

### 错误实践
```javascript
// 危险：不要在播放前将所有片段转为 Blob URL
const allBlobs = await Promise.all(videoUrls.map(url => fetch(url).then(r => r.blob())));
```
**后果**：内存溢出崩溃、首屏卡死几十秒无法进入。

### 正确实践
应优先建立按需 URL 映射，让 `<video>` 元素通过 HTTP Range 流式按需起播：
```javascript
URLS[c] = 'media/clips/' + c + '.mp4';
// <video src="..."> 原生支持 Range 分块流式拉取
```

---

## 3. 音频自动播放策略（Autoplay Policy）解耦

浏览器限制未交互音频自动播放。不要让 `audio.play().catch(...)` 直接终止整个画面渲染。

**正确做法**：
- 动画与时钟正常推进，音频捕获失败时优雅降级并允许后续点击恢复。
- 页面首屏必须提供"点击开始 / 点击播放"按钮，触发 `audio.play()`。

---

## 4. 全屏点击监听

为整个舞台/遮罩层挂载播放监听，避免用户必须精确点击小按钮才能触发播放。

---

## 5. Canvas 动效与音视频解耦架构

将 Canvas 动效主循环与音视频解码解耦：
1. 音频负责时钟参考（时间轴驱动）
2. 渲染循环通过 `requestAnimationFrame` 依据当前音频时间轴渲染
3. 即使单帧掉帧也不会中断音频播放
