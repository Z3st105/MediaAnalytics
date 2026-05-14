# MediaAnalytics

B 站视频内容提取工具 — 从视频链接到文字转录，一键完成。

## 功能

- 输入 B 站视频链接，自动下载音频
- Whisper ASR 语音转录（GPU 加速）
- 浏览器插件管理视频列表，支持一键复制转录文本
- 支持手动粘贴 AI 分析结果

## 架构

```
浏览器插件 (Edge, Manifest V3)
    ↕  HTTP REST API
Python 后端 (FastAPI + uvicorn)
    ↕
yt-dlp 下载音频 → Whisper 转录 → SQLite 存储
```

### 后端

| 文件 | 说明 |
|------|------|
| `backend/api.py` | FastAPI 主服务，REST API 端点 |
| `backend/asr_service.py` | Whisper ASR 语音转录 |
| `backend/database.py` | SQLite 数据库管理 |
| `backend/downloader.py` | yt-dlp 音频下载 |

### 浏览器插件

| 文件 | 说明 |
|------|------|
| `extension/manifest.json` | Manifest V3 配置 |
| `extension/popup.html` | 插件 UI 界面 |
| `extension/popup.js` | 交互逻辑 |

## 安装

### 1. 后端依赖

```bash
cd backend
pip install -r requirements.txt
```

**额外依赖：**
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 视频音频下载
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — ASR 转录引擎
- ffmpeg — 音频处理（需在 PATH 中或配置路径）

### 2. 配置

当前配置硬编码在各模块中，需根据实际环境修改：

- `backend/asr_service.py` — Whisper 模型路径、Python 运行时路径
- `backend/downloader.py` — ffmpeg 路径
- `backend/database.py` — SQLite 数据库路径

### 3. 启动后端

```bash
# Windows
start.bat

# 或手动启动
cd backend
python -m uvicorn api:app --host 127.0.0.1 --port 8765 --log-level info
```

后端运行在 `http://127.0.0.1:8765`。

### 4. 安装浏览器插件

1. 打开 Edge，访问 `edge://extensions/`
2. 开启「开发者模式」
3. 点击「加载已解压的扩展」，选择 `extension/` 目录

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/videos` | 提交视频链接 |
| `GET` | `/api/videos` | 获取视频列表 |
| `GET` | `/api/videos/{id}` | 获取单个视频 |
| `PUT` | `/api/videos/{id}/analysis` | 保存 AI 分析 |
| `DELETE` | `/api/videos/{id}` | 删除视频 |

## 使用流程

1. 在浏览器打开 B 站视频页面
2. 点击插件图标，视频链接自动填入
3. 点击「添加」，后端自动下载音频并转录
4. 转录完成后，点击「复制」获取文本
5. 可将 AI 分析结果粘贴回插件保存

## 项目结构

```
MediaAnalytics/
├── backend/                # Python 后端
│   ├── api.py              # FastAPI 主服务
│   ├── asr_service.py      # ASR 转录服务
│   ├── database.py         # 数据库管理
│   ├── downloader.py       # 音频下载器
│   └── requirements.txt    # Python 依赖
├── extension/              # Edge 浏览器插件
│   ├── manifest.json       # 插件配置
│   ├── popup.html          # UI 界面
│   └── popup.js            # 交互逻辑
├── start.bat               # Windows 启动脚本
└── README.md
```

## License

MIT
