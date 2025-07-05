# NagaAgent 3.0

> 智能对话助手，支持多MCP服务、流式语音交互、GRAG知识图谱记忆系统、RESTful API接口、极致精简代码风格。

---

## ⚡ 快速开始
1. 克隆项目
   ```bash
   git clone [项目地址]
   cd NagaAgent
   ```
2. 一键配置

   **Windows:**
   ```powershell
   .\setup.ps1
   ```
   **Mac:**
   ```bash
   chmod +x quick_deploy_mac.sh
   ./quick_deploy_mac.sh
   ```
   - 自动创建虚拟环境并安装依赖
   - 配置支持toolcall的LLM，推荐DeepSeekV3
   - 初始化GRAG知识图谱记忆系统
3. 启动

   **Windows:**
   ```powershell
   .\start.bat
   ```
   **Mac:**
   ```bash
   ./start_mac.sh
   ```

启动后将自动开启PyQt5界面和RESTful API服务器，可同时使用界面对话和API接口。

---

## 🖥️ 系统要求
- **Windows:** Windows 10/11 + PowerShell 5.1+
- **Mac:** macOS 10.15 (Catalina) 或更高版本 + Homebrew
- **通用:** Python 3.8+ (推荐 3.11)

---

## 🛠️ 依赖安装与环境配置

### Windows 环境
- 所有依赖见`pyproject.toml`
- 推荐使用 `uv` 作为包管理器，自动处理依赖安装和虚拟环境
- 如遇`greenlet`、`pyaudio`等安装失败，需先装[Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)，勾选C++ build tools
- 浏览器自动化需`playwright`，首次用需`python -m playwright install chromium`
- 依赖安装命令：
  ```powershell
  # 推荐使用 uv（现代化包管理器）
  uv sync
  python -m playwright install chromium
  
  # 或者使用传统 pip
  python -m venv .venv
  .venv\Scripts\Activate
  pip install -e .
  python -m playwright install chromium
  ```

### Mac 环境
- 系统依赖通过Homebrew安装：
  ```bash
  # 安装基础依赖
  brew install python@3.11 portaudio
  brew install --cask google-chrome
  ```
- Python依赖安装：
  ```bash
  # 推荐使用 uv（现代化包管理器）
  uv sync
  python -m playwright install chromium
  
  # 或者使用传统 pip
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e .
  python -m playwright install chromium
  ```
- 如遇PyAudio安装失败：
  ```bash
  brew install portaudio
  uv sync --extra audio  # 或 pip install pyaudio
  ```

### 环境检查（跨平台通用）
```bash
python check_env.py
```

---

## ⚙️ 配置说明

### API 密钥配置
直接修改 `config.py` 文件中的配置：
```python
API_KEY = "<your_deepseek_api>"
```

### API服务器配置
在 `config.py` 中可配置API服务器相关参数：
```python
API_SERVER_ENABLED = True  # 是否启用API服务器
API_SERVER_HOST = "127.0.0.1"  # API服务器主机
API_SERVER_PORT = 8000  # API服务器端口
API_SERVER_AUTO_START = True  # 启动时自动启动API服务器
```

### GRAG知识图谱记忆系统配置
在 `config.py` 中可配置GRAG记忆系统：
```python
GRAG_ENABLED = True  # 是否启用GRAG记忆系统
GRAG_AUTO_EXTRACT = True  # 是否自动提取对话中的三元组
GRAG_CONTEXT_LENGTH = 5  # 记忆上下文长度
GRAG_SIMILARITY_THRESHOLD = 0.6  # 记忆检索相似度阈值
GRAG_NEO4J_URI = "neo4j://127.0.0.1:7687"  # Neo4j连接URI
GRAG_NEO4J_USER = "neo4j"  # Neo4j用户名
GRAG_NEO4J_PASSWORD = "your_password"  # Neo4j密码
```

### 获取 DeepSeek API 密钥
1. 访问 [DeepSeek 官网](https://platform.deepseek.com/)
2. 注册账号并创建 API 密钥
3. 将密钥填入 `config.py` 或 `.env` 文件

---

## 🌟 主要特性
- **全局变量/路径/密钥统一`config.py`管理**，支持.env和环境变量，所有变量唯一、无重复定义
- **RESTful API接口**，自动启动HTTP服务器，支持完整对话功能和流式输出，可集成到任何前端或服务
- DeepSeek流式对话，支持上下文召回与GRAG知识图谱检索
- **GRAG知识图谱记忆系统**，基于Neo4j的三元组知识图谱，自动提取对话中的实体关系，支持记忆查询和管理
- **TOOL_REQUEST工具调用循环**，自动解析和执行LLM返回的工具调用，支持多轮递归调用
- **多Agent能力扩展：浏览器、文件、代码等多种Agent即插即用，所有Agent均可通过工具调用循环机制统一调用**
- **跨平台兼容：Windows/Mac自动适配，浏览器路径自动检测，依赖智能安装**
- 代码极简，注释全中文，组件解耦，便于扩展
- PyQt5动画与UI，支持PNG序列帧，loading动画极快
- 日志/检索/索引/主题/参数全部自动管理
- 记忆权重动态调整，支持AI/人工标记important，权重/阈值/清理策略全部在`config.py`统一管理
- **所有前端UI与后端解耦，前端只需解析后端JSON，自动适配message/data.content等多种返回结构**
- **前端换行符自动适配，无论后端返回`\n`还是`\\n`，PyQt界面都能正确分行显示**
- **所有Agent的注册元数据已集中在`mcpserver/mcp_registry.py`，主流程和管理器极简，扩展维护更方便。只需维护一处即可批量注册/扩展所有Agent服务。**
- **自动注册/热插拔Agent机制，新增/删除Agent只需增删py文件，无需重启主程序**
- 聊天窗口支持**Markdown语法**，包括标题、粗体、斜体、代码块、表格、图片等。

---

## 🗂️ 目录结构
```
NagaAgent/
├── main.py                     # 主入口
├── config.py                   # 全局配置
├── conversation_core.py        # 对话核心（含工具调用循环主逻辑）
├── apiserver/                  # API服务器模块
│   ├── api_server.py           # FastAPI服务器
│   ├── start_server.py         # 启动脚本
│   └── README.md               # API文档
├── agent/                      # 预处理系统模块
│   ├── preprocessor.py         # 消息预处理
│   ├── plugin_manager.py       # 插件管理
│   ├── api_server.py           # 代理API服务器
│   ├── image_processor.py      # 图片处理
│   ├── start_server.py         # 启动脚本
│   └── README.md               # 预处理系统文档
├── mcpserver/
│   ├── mcp_manager.py          # MCP服务管理
│   ├── mcp_registry.py         # Agent注册与schema元数据
│   ├── agent_xxx/              # 各类自定义Agent（如file、coder、browser等）
├── pyproject.toml              # 项目配置和依赖
├── setup.ps1                   # Windows配置脚本
├── start.bat                   # Windows启动脚本
├── setup_mac.sh                # Mac配置脚本
├── quick_deploy_mac.sh         # Mac一键部署脚本
├── check_env.py                # 跨平台环境检查
├── summer_memory/              # GRAG知识图谱记忆系统
│   ├── memory_manager.py       # 记忆管理器
│   ├── extractor_ds_tri.py     # 三元组提取器
│   ├── graph.py                # Neo4j图谱操作
│   ├── rag_query_tri.py        # 记忆查询
│   ├── visualize.py            # 图谱可视化
│   ├── main.py                 # 独立运行入口
│   └── triples.json            # 三元组缓存
├── logs/                       # 日志（含历史txt对话）
│   ├── 2025-04-27.txt
│   ├── 2025-05-05.txt
│   └── ...
├── voice/                      # 语音相关
│   ├── voice_config.py
│   └── voice_handler.py
├── ui/                         # 前端UI
│   ├── pyqt_chat_window.py     # PyQt聊天窗口
│   └── response_utils.py       # 前端通用响应解析工具
├── models/                     # 模型等
├── README.md                   # 项目说明
└── ...
```

---

## 🔧 工具调用循环机制

### TOOL_REQUEST格式
系统仅支持如下格式的工具调用：

```
<<<[TOOL_REQUEST]>>>
tool_name: 「始」服务名称「末」
param1: 「始」参数值1「末」
param2: 「始」参数值2「末」
<<<[END_TOOL_REQUEST]>>>
```

### 工具调用流程
1. **LLM输出TOOL_REQUEST格式**：LLM根据用户需求输出工具调用请求
2. **自动解析工具调用**：系统自动解析TOOL_REQUEST块，提取工具名称和参数
3. **执行工具调用**：调用对应的MCP服务执行具体任务
4. **结果返回LLM**：将工具执行结果返回给LLM
5. **循环处理**：重复步骤2-4，直到LLM输出普通文本或无工具调用

### 配置参数
```python
# config.py中的工具调用循环配置
MAX_handoff_LOOP_STREAM = 5      # 流式模式最大工具调用循环次数
MAX_handoff_LOOP_NON_STREAM = 5  # 非流式模式最大工具调用循环次数
SHOW_handoff_OUTPUT = False      # 是否显示工具调用输出
```

### 使用示例
```python
# 浏览器操作
await mcp.handoff(
    service_name="playwright",
    task={"action": "open_browser", "url": "https://www.bilibili.com"}
)

# 文件操作
await mcp.handoff(
    service_name="file",
    task={"action": "read", "path": "test.txt"}
)

# 代码执行
await mcp.handoff(
    service_name="coder",
    task={"action": "run", "file": "main.py"}
)
```

---

## 🌐 多Agent与MCP服务
- **所有Agent的注册、schema、描述均集中在`mcpserver/mcp_registry.py`，批量管理，极简扩展**
- 支持浏览器、文件、代码等多种Agent，全部可通过工具调用循环机制统一调用
- Agent能力即插即用，自动注册/热插拔，无需重启主程序
- 典型用法示例：

```python
# 读取文件内容
await s.mcp.handoff(
  service_name="file",
  task={"action": "read", "path": "test.txt"}
)
# 运行Python代码
await s.mcp.handoff(
  service_name="coder",
  task={"action": "run", "file": "main.py"}
)
```

---

## 📝 前端UI与响应适配
- **所有后端返回均为结构化JSON，前端通过`ui/response_utils.py`的`extract_message`方法自动适配多种返回格式**
- 优先显示`data.content`，其次`message`，最后原样返回，兼容所有Agent
- PyQt前端自动将所有`\n`和`\\n`换行符转为`<br>`，多行内容显示无障碍
- UI动画、主题、昵称、透明度等全部可在`config.py`和`pyqt_chat_window.py`灵活配置

---

## 🔊 流式语音交互
- 支持语音输入（流式识别，自动转文字）与语音输出（流式合成，边播边出）
- 依赖与配置详见`voice/voice_config.py`和README相关章节

---

## 📝 其它亮点
- 记忆权重、遗忘阈值、冗余去重、短期/长期记忆容量等全部在`config.py`统一管理，便于灵活调整
- 主题归类、召回、权重提升、清理等全部自动化，AI/人工可标记important内容，重要内容一年内不会被清理
- 检索日志自动记录，参数可调，GRAG配置示例见`config.py`
- 聊天窗口背景透明度、用户名、主题树召回、流式输出、侧栏动画等全部可自定义
- 支持历史对话一键导入GRAG知识图谱记忆系统，兼容主题、分层、三元组等所有新特性
- **工具调用循环自动执行机制，支持多轮递归调用，最大循环次数可配置**

---

## 🆙 历史对话兼容升级
- 支持将旧版txt对话内容一键导入GRAG知识图谱记忆系统，兼容主题、分层、三元组等所有新特性。
- 激活指令：
  ```
  #夏园系统兼容升级
  ```
  - 系统会自动遍历logs目录下所有txt日志，列出所有历史对话内容并编号，输出到终端和`summer_memory/history_dialogs.json`。
- 用户可查看编号后，选择导入方式：
  - 全部导入：
    ```
    python summer_memory/main.py import all
    ```
  - 选择性导入（如第1、3、5-8条）：
    ```
    python summer_memory/main.py import 1,3,5-8
    ```
- 兼容过程自动判重，已入库内容不会重复导入，支持断点续跑。
- 兼容内容全部走AI自动主题归类与分层，完全与新系统一致。
- 详细进度、结果和异常均有反馈，安全高效。

---

## ❓ 常见问题

- 环境检查：`python check_env.py`

### Windows 环境
- Python版本/依赖/虚拟环境/浏览器驱动等问题，详见`setup.ps1`与本README
- IDE报import错误，重启并选择正确解释器
- 语音依赖安装失败，先装C++ Build Tools

### Mac 环境
- Python版本过低：`brew install python@3.11`
- PyAudio安装失败：`brew install portaudio && pip install pyaudio`
- 权限问题：`chmod +x *.sh`

### API服务器问题
- 端口占用：修改`config.py`中的`API_SERVER_PORT`
- 代理干扰：临时禁用代理 `unset ALL_PROXY http_proxy https_proxy`
- 依赖缺失：确保安装了FastAPI和Uvicorn `pip install fastapi uvicorn[standard]`
- 无法访问：检查防火墙设置，确保端口未被阻塞

### 工具调用问题
- 工具调用循环次数过多：调整`config.py`中的`MAX_handoff_LOOP_STREAM`和`MAX_handoff_LOOP_NON_STREAM`
- 工具调用失败：检查MCP服务是否正常运行，查看日志输出
- 格式错误：确保LLM输出严格遵循TOOL_REQUEST格式

### GRAG记忆系统问题
- Neo4j连接失败：检查Neo4j服务是否启动，确认连接参数正确
- 记忆查询无结果：检查三元组是否正确提取和存储
- 性能问题：调整`config.py`中的GRAG相关参数

### 通用问题
- 浏览器无法启动，检查playwright安装与网络
- 主题树/索引/参数/密钥全部在`config.py`统一管理
- 聊天输入`#devmode`进入开发者模式，后续对话不写入GRAG记忆，仅用于工具调用测试

---

## 📝 许可证
MIT License

---

如需详细功能/API/扩展说明，见各模块注释与代码，所有变量唯一、注释中文、极致精简。

## 聊天窗口自定义
1. 聊天窗口背景透明度由`config.BG_ALPHA`统一控制，取值0~1，默认0.4。
2. 用户名自动识别电脑名，变量`config.USER_NAME`，如需自定义可直接修改该变量。

## 智能历史召回机制
1. 默认按主题分片检索历史，极快且相关性高。
2. 若分片查不到，自动兜底遍历所有主题分片模糊检索，话题跳跃也能召回历史。
3. GRAG知识图谱查询支持直接调用，返回全局最相关历史。
4. 兜底逻辑已集成主流程，无需手动切换。

## ⚡️ 全新流式输出机制
- AI回复支持前后端全链路流式输出，边生成边显示，极致丝滑。
- 后端采用async生成器yield分段内容，前端Worker线程streaming信号实时追加到对话框。
- 彻底无终端print污染，支持大文本不卡顿。
- 如遇依赖包冲突，建议彻底清理全局PYTHONPATH和环境变量，仅用虚拟环境。

## 侧栏与主聊天区动画优化说明
- 侧栏点击切换时，侧栏宽度、主聊天区宽度、输入框高度均采用同步动画，提升视觉流畅度。
- 输入框隐藏采用高度动画，动画结束后自动清除焦点，避免输入法残留。
- 线程处理增加自动释放，避免内存泄漏。
- 相关动画效果可在`ui/pyqt_chat_window.py`的`toggle_full_img`方法中自定义。

### 使用方法
- 点击侧栏即可切换立绘展开/收起，主聊天区和输入框会自动让位并隐藏/恢复。
- 动画时长、缓动曲线等可根据需要调整源码参数。

## 工具调用循环机制详解

### 核心特性
- **自动解析**：系统自动解析LLM返回的TOOL_REQUEST格式工具调用
- **递归执行**：支持多轮工具调用循环，最大循环次数可配置
- **错误处理**：完善的错误处理和回退机制
- **流式支持**：支持流式和非流式两种模式

### 工具调用格式
LLM必须严格按照以下格式输出工具调用：

```
<<<[TOOL_REQUEST]>>>
tool_name: 「始」服务名称「末」
param1: 「始」参数值1「末」
param2: 「始」参数值2「末」
<<<[END_TOOL_REQUEST]>>>
```

### 执行流程
1. **接收用户消息**
2. **调用LLM API**
3. **解析TOOL_REQUEST格式工具调用**
4. **执行工具调用（通过MCP服务）**
5. **将结果返回给LLM**
6. **重复步骤2-5直到无工具调用或达到最大循环次数**

### 配置参数
```python
# config.py中的工具调用循环配置
MAX_handoff_LOOP_STREAM = 5      # 流式模式最大工具调用循环次数
MAX_handoff_LOOP_NON_STREAM = 5  # 非流式模式最大工具调用循环次数
SHOW_handoff_OUTPUT = False      # 是否显示工具调用输出
```

### 错误处理
- 工具调用失败时会记录错误信息并继续执行
- 达到最大循环次数时会停止
- 支持回退到原始处理方式

### 扩展开发
如需添加新的工具调用处理逻辑，可以：
1. 在`mcpserver/`目录下添加新的Agent
2. 在`mcpserver/mcp_registry.py`中注册新Agent
3. 更新API接口以支持新的功能

---

## 🌐 RESTful API 服务

NagaAgent内置完整的RESTful API服务器，启动时自动开启，支持所有对话功能：

### API接口说明

- **基础地址**: `http://127.0.0.1:8000` (可在config.py中配置)
- **交互式文档**: `http://127.0.0.1:8000/docs`
- **OpenAPI规范**: `http://127.0.0.1:8000/openapi.json`

### 主要接口

#### 健康检查
```bash
GET /health
```

#### 对话接口
```bash
# 普通对话
POST /chat
{
  "message": "你好，娜迦",
  "session_id": "optional-session-id"
}

# 流式对话 (Server-Sent Events)
POST /chat/stream
{
  "message": "请介绍一下人工智能的发展历程"
}
```

#### 系统管理接口
```bash
# 获取系统信息
GET /system/info

# 切换开发者模式
POST /system/devmode

# 获取记忆统计
GET /memory/stats
``` 

## MCP服务Agent化升级说明

- 所有MCP服务（如文件、代码、浏览器、应用启动、系统控制、天气等）已全部升级为标准Agent风格：
  - 统一继承自`agents.Agent`，具备`name`、`instructions`属性和`handle_handoff`异步方法
  - 变量全部走`config.py`统一管理，避免重复定义
  - 注释全部中文，文件/类/函数注释一行，变量注释右侧#
  - 支持多agent协作，ControllerAgent可智能分配任务给BrowserAgent、ContentAgent等
  - 注册中心`mcp_registry.py`自动发现并注册所有实现了`handle_handoff`的Agent实例，支持热插拔
  - 注册时自动输出所有已注册agent的名称和说明，便于调试

- handoff机制全部通过`handle_handoff`异步方法调度，兼容TOOL_REQUEST和handoff两种格式

- 新增/删除agent只需增删py文件，无需重启主程序

- 详细接口和参数请参考各Agent代码注释与`config.py`配置 
