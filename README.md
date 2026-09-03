# 🤫 Hush · Midnight Inn

一个面向失眠者的 AI 陪伴应用 —— 通过语音、日记、信件、占卜、音乐等方式，在夜间提供情感支持与陪伴。

## 🌙 核心功能

- **无眼交互模式** - 完全通过语音与虚拟主人对话，可闭眼入睡
- **声音陪伴** - ASMR、雨声、白噪音、自动生成的睡眠音乐
- **表达方式**
  - 📓 **日记** - 记录夜间的想法（仅自己可见）
  - ✉️ **匿名信** - 写给陌生人的信，获得回复
  - 🔮 **占卜** - 通过塔罗反思
- **地图探索** - 虚拟城镇与真实地图切换
- **个性化** - 选择或上传虚拟主人的头像

## 🏗️ 技术架构

```
前端: HTML5 + Web Audio API + Speech Recognition
后端: FastAPI + ElevenLabs TTS + SQLite
LLM: Anthropic Claude / DeepSeek（可选）
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- ElevenLabs API Key（用于 TTS）

### 安装

```bash
cd /Users/ruohanchen/Desktop/Hush

# 安装依赖
pip3 install fastapi uvicorn requests

# 配置 .env（已提供模板）
# ELEVENLABS_API_KEY=xxx
# HUSH_VOICE_ID=xxx
```

### 运行

```bash
# 方式 1：使用启动脚本
./start_server.sh

# 方式 2：直接运行
python3 hush_backend.py
```

然后打开浏览器：**http://localhost:8000/hush_app.html**

## 📋 项目结构

```
Hush/
├── hush_app.html          # 前端应用（完整 UI）
├── hush_backend.py        # 后端服务（FastAPI）
├── hush_server.py         # 简易 TTS 服务器
├── start_server.sh        # 启动脚本
├── .env                   # 环境变量配置
├── .gitignore             # Git 忽略规则
└── web/                   # 其他资源
```

## 🔌 API 端点

### 核心 API
- `POST /api/tts` - 文本转语音（ElevenLabs）
- `POST /api/chat` - 对话回复
- `POST /api/triage` - 意图识别
- `POST /api/tarot` - 占卜
- `POST /api/entries` - 保存日记
- `GET /api/entries` - 获取日记列表

### 信件系统
- `POST /api/letters` - 创建信件
- `GET /api/letters` - 我的信件
- `POST /api/letters/{id}/send` - 发送信件
- `GET /api/box` - 随机阅读匿名信

## 🎯 配置说明

### 必需
- **ELEVENLABS_API_KEY** - ElevenLabs API 密钥
- **HUSH_VOICE_ID** - 虚拟主人的语音 ID

### 可选（用于 AI 对话）
- **ANTHROPIC_API_KEY** - Anthropic Claude API
- **DEEPSEEK_API_KEY** - DeepSeek API

## 💡 开发路线图

- [ ] 云端数据同步
- [ ] 用户认证系统
- [ ] 多语言完整支持
- [ ] 真实地图集成（Google Maps）
- [ ] 社交分享功能
- [ ] 移动应用版本

## 🛡️ 隐私与安全

- API Key 存储在本地 `.env` 文件，不进网络
- 用户数据存储在本地 SQLite 数据库
- 匿名信件系统完全去身份
- 无追踪、无广告

## 📞 需要帮助？

检查终端输出或查看启动脚本中的常见问题解决方案。

---

**Made with 🤍 for sleepless nights**
