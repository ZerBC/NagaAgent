# OpenAI兼容的 Edge-TTS API 🗣️

![GitHub stars](https://img.shields.io/github/stars/travisvn/openai-edge-tts?style=social)
![GitHub forks](https://img.shields.io/github/forks/travisvn/openai-edge-tts?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/travisvn/openai-edge-tts)
![GitHub top language](https://img.shields.io/github/languages/top/travisvn/openai-edge-tts)
![GitHub last commit](https://img.shields.io/github/last-commit/travisvn/openai-edge-tts?color=red)
[![Discord](https://img.shields.io/badge/Discord-Voice_AI_%26_TTS_Tools-blue?logo=discord&logoColor=white)](https://discord.gg/GkFbBCBqJ6)
[![LinkedIn](https://img.shields.io/badge/Connect_on_LinkedIn-%230077B5.svg?logo=linkedin&logoColor=white)](https://linkedin.com/in/travisvannimwegen)

本项目提供了一个本地的、OpenAI兼容的文本转语音（TTS）API，基于 `edge-tts`。它模拟了 OpenAI 的 TTS 接口（`/v1/audio/speech`），让用户可以像使用 OpenAI API 一样，通过多种语音和播放速度将文本转为语音。

`edge-tts` 使用微软 Edge 的在线文本转语音服务，完全免费。

[在 Docker Hub 查看本项目](https://hub.docker.com/r/travisvn/openai-edge-tts)

# 如果觉得有用请点个⭐️

## 功能特性

- **OpenAI兼容接口**：`/v1/audio/speech`，请求结构和行为与OpenAI类似。
- **支持多种语音**：将OpenAI语音（alloy, echo, fable, onyx, nova, shimmer）映射到`edge-tts`语音。
- **多音频格式**：支持多种音频格式（mp3, opus, aac, flac, wav, pcm）。
- **可调节语速**：支持0.25x到4.0x的播放速度。
- **可选直接指定edge-tts语音**：既可用OpenAI语音映射，也可直接指定任意edge-tts语音。

## 快速开始

### 前置条件

- **Docker**（推荐）：建议用 Docker 和 Docker Compose 部署。
- **Python**（可选）：本地开发可用，需安装 `pyproject.toml` 中的依赖。
- **ffmpeg**（可选）：音频格式转换需要。只用mp3可不装。

### 安装步骤

1. **克隆仓库**：
```bash
git clone https://github.com/travisvn/openai-edge-tts.git
cd openai-edge-tts
```

2. **环境变量**：在根目录创建 `.env` 文件，内容如下：
```
API_KEY=your_api_key_here
PORT=5050

DEFAULT_VOICE=en-US-AvaNeural
DEFAULT_RESPONSE_FORMAT=mp3
DEFAULT_SPEED=1.0

DEFAULT_LANGUAGE=en-US

REQUIRE_API_KEY=True
REMOVE_FILTER=False
EXPAND_API=True
```

或直接复制默认 `.env.example`：
```bash
cp .env.example .env
```

## 用 Python 运行

如需直接用 Python 运行，按以下步骤配置虚拟环境、安装依赖并启动服务。

### 1. 克隆仓库

```bash
git clone https://github.com/travisvn/openai-edge-tts.git
cd openai-edge-tts
```

### 2. 创建虚拟环境

建议用虚拟环境隔离依赖：

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. 安装依赖

用 `pip` 安装依赖：

```bash
uv sync --extra audio  # 或 pip install -e .
```

### 4. 配置环境变量

在根目录创建 `.env` 文件，内容如下：

```plaintext
API_KEY=your_api_key_here
PORT=5050

DEFAULT_VOICE=en-US-AvaNeural
DEFAULT_RESPONSE_FORMAT=mp3
DEFAULT_SPEED=1.0

DEFAULT_LANGUAGE=en-US

REQUIRE_API_KEY=True
REMOVE_FILTER=False
EXPAND_API=True
```

### 5. 启动服务

配置好后，运行：

```bash
python app/server.py
```

服务将运行在 `http://localhost:5050`。

### 6. 测试API

现在可以通过 `http://localhost:5050/v1/audio/speech` 及其它接口访问API。请求示例见[用法](#usage)部分。

### 用法

#### 接口：`/v1/audio/speech`

将输入文本转为音频。可用参数：

**必填参数：**

- **input** (string)：要转为音频的文本（最多4096字符）。

**可选参数：**

- **model** (string)："tts-1" 或 "tts-1-hd"（默认：`tts-1`）。
- **voice** (string)：OpenAI兼容语音（alloy, echo, fable, onyx, nova, shimmer）或任意`edge-tts`语音（默认：`en-US-AvaNeural`）。
- **response_format** (string)：音频格式。可选：`mp3`、`opus`、`aac`、`flac`、`wav`、`pcm`（默认：`mp3`）。
- **speed** (number)：播放速度（0.25~4.0），默认`1.0`。

curl请求示例，保存为mp3：

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello, I am your AI assistant! Just let me know how I can help bring your ideas to life.",
    "voice": "echo",
    "response_format": "mp3",
    "speed": 1.1
  }' \
  --output speech.mp3
```

或与OpenAI参数一致的写法：

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "model": "tts-1",
    "input": "Hello, I am your AI assistant! Just let me know how I can help bring your ideas to life.",
    "voice": "alloy"
  }' \
  --output speech.mp3
```

其它语言示例：

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "model": "tts-1",
    "input": "じゃあ、行く。電車の時間、調べておくよ。",
    "voice": "ja-JP-KeitaNeural"
  }' \
  --output speech.mp3
```

### 其它接口

- **POST/GET /v1/models**：获取可用TTS模型列表。
- **POST/GET /v1/voices**：按语言/地区获取`edge-tts`语音。
- **POST/GET /v1/voices/all**：获取所有`edge-tts`语音及支持信息。

### 贡献

欢迎贡献代码！请fork本仓库并提交PR。

### 许可证

本项目采用GNU GPL v3.0协议，仅限个人用途。如需企业或非个人用途，请联系 tts@travisvn.com

___

## 示例用法

> [!TIP]
> 如果访问有问题，将 `localhost` 换成本机IP（如 `192.168.0.1`）
> 
> _当你在其它服务器/电脑或用Open WebUI等工具访问时，可能需要将URL中的`localhost`换为本机IP（如`192.168.0.1`）_

# Open WebUI

打开管理面板，进入 设置 -> Audio

下图为正确配置本项目替代OpenAI接口的截图：

![Open WebUI管理设置音频接口配置截图](https://utfs.io/f/MMMHiQ1TQaBo9GgL4WcUbjSRlqi86sV3TXh47KYBJCkdQ20M)

如果Open WebUI和本项目都用Docker运行，API地址一般为 `http://host.docker.internal:5050/v1`

> [!NOTE]
> 查看[Open WebUI官方文档关于Edge TTS集成](https://docs.openwebui.com/tutorials/text-to-speech/openai-edge-tts-integration)
___

# 语音示例 🎙️
[试听语音样例及全部Edge TTS语音](https://tts.travisvn.com/)
