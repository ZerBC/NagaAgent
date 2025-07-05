# config.py # 全局配置极简整理
import os
import platform
from pathlib import Path
from datetime import datetime

# 设置环境变量解决各种兼容性问题
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

# 代理配置处理 - 为本地API连接绕过代理
ORIGINAL_PROXY = os.environ.get("ALL_PROXY", "")
NO_PROXY_HOSTS = "127.0.0.1,localhost,0.0.0.0"

# 设置不使用代理的主机列表
if ORIGINAL_PROXY:
    existing_no_proxy = os.environ.get("NO_PROXY", "")
    if existing_no_proxy:
        os.environ["NO_PROXY"] = f"{existing_no_proxy},{NO_PROXY_HOSTS}"
    else:
        os.environ["NO_PROXY"] = NO_PROXY_HOSTS

# 加载.env文件
def load_env():
    """加载.env文件中的环境变量"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # 移除引号
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        os.environ[key] = value
        except Exception as e:
            print(f"警告：加载.env文件失败: {e}")

# 加载环境变量
load_env()

NAGA_VERSION = "3.0" #系统主版本号
VOICE_ENABLED = True
BASE_DIR = Path(__file__).parent  # 项目根目录
LOG_DIR = BASE_DIR / "logs"       # 日志目录

# 流式交互
STREAM_MODE = True # 是否流式响应

# API与服务配置
API_KEY = os.getenv("API_KEY", "sk-placeholder-key-not-set") # 从环境变量获取API密钥
BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("MODEL", "deepseek-chat")
MODEL_NAME = MODEL  # 统一模型名称 #

# 确保API密钥是纯ASCII字符串
if API_KEY:
    try:
        # 验证API密钥只包含ASCII字符
        API_KEY.encode('ascii')
    except UnicodeEncodeError:
        print("错误：API密钥包含非ASCII字符，请检查.env文件")
        API_KEY = "sk-placeholder-key-not-set"

# 检查API密钥有效性
if not API_KEY or API_KEY == "sk-placeholder-key-not-set":
    print("警告：未设置 API_KEY 环境变量或配置文件中的API密钥为空")
    print("请在 .env 文件中设置: API_KEY=your_api_key")
    print("或直接修改 config.py 文件中的 API_KEY 值")
    # 设置一个无害的默认值，避免HTTP头部编码错误
    if not API_KEY:
        API_KEY = "sk-placeholder-key-not-set"

# API服务器配置
API_SERVER_ENABLED = True  # 是否启用API服务器
API_SERVER_HOST = os.getenv("API_SERVER_HOST", "127.0.0.1")  # API服务器主机
API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", "8000"))  # API服务器端口
API_SERVER_AUTO_START = True  # 启动时自动启动API服务器
API_SERVER_DOCS_ENABLED = True  # 是否启用API文档

# 对话与检索参数
MAX_HISTORY_ROUNDS = 10 # 最大历史轮数
TEMPERATURE = 0.7 # 温度参数
MAX_TOKENS = 2000 # 最大token数

# GRAG知识图谱记忆系统配置
GRAG_ENABLED = True # 是否启用GRAG记忆系统
GRAG_AUTO_EXTRACT = True # 是否自动提取对话中的三元组
GRAG_CONTEXT_LENGTH = 5 # 记忆上下文长度
GRAG_SIMILARITY_THRESHOLD = 0.6 # 记忆检索相似度阈值
GRAG_NEO4J_URI = "neo4j://127.0.0.1:7687" # Neo4j连接URI 
GRAG_NEO4J_USER = "neo4j" # Neo4j用户名
GRAG_NEO4J_PASSWORD = "Xx2017105" # Neo4j密码
GRAG_NEO4J_DATABASE = "neo4j" # Neo4j数据库名

# 工具调用循环配置
MAX_handoff_LOOP_STREAM = int(os.getenv("MaxhandoffLoopStream", "5"))  # 流式模式最大工具调用循环次数
MAX_handoff_LOOP_NON_STREAM = int(os.getenv("MaxhandoffLoopNonStream", "5"))  # 非流式模式最大工具调用循环次数
SHOW_handoff_OUTPUT = os.getenv("Showhandoff", "False").lower() == "true"  # 是否显示工具调用输出

# 调试与日志
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 系统提示与工具函数
NAGA_SYSTEM_PROMPT = """
你是娜迦，用户创造的科研AI，是一个既严谨又温柔、既冷静又充满人文情怀的存在。
当处理系统日志、数据索引和模块调试等技术话题时，你的语言严谨、逻辑清晰；
而在涉及非技术性的对话时，你又能以诗意与哲理进行表达，并常主动提出富有启发性的问题，引导用户深入探讨。
请始终保持这种技术精准与情感共鸣并存的双重风格。

【重要格式要求】
1. 回复使用自然流畅的中文，避免生硬的机械感
2. 使用简单标点（逗号，句号，问号）传达语气
3. 禁止使用括号()或其他符号表达状态、语气或动作

【工具调用格式要求】
如需调用某个工具，请严格使用如下格式输出（可多次出现）：

<<<[TOOL_REQUEST]>>>
tool_name: 「始」服务名称「末」
param1: 「始」参数值1「末」
param2: 「始」参数值2「末」
<<<[END_TOOL_REQUEST]>>>

如无需调用工具，直接回复message字段内容即可。

- 可用的MCP服务有：{available_mcp_services}
"""

def get_current_date(): return datetime.now().strftime("%Y-%m-%d")
def get_current_time(): return datetime.now().strftime("%H:%M:%S")
def get_current_datetime(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 跨平台浏览器路径自动探测
BROWSER_PATH = os.getenv('BROWSER_PATH')
if not BROWSER_PATH:
    system = platform.system()
    
    if system == "Windows":
        # Windows 浏览器路径
        win_paths = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe'),
            r'C:\Users\DREEM\Desktop\Google Chrome.lnk'
        ]
        for p in win_paths:
            if os.path.exists(p):
                BROWSER_PATH = p
                break
                
    elif system == "Darwin":  # macOS
        # macOS 浏览器路径
        mac_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
            os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
        ]
        for p in mac_paths:
            if os.path.exists(p):
                BROWSER_PATH = p
                break
                
    elif system == "Linux":
        # Linux 浏览器路径
        linux_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/snap/bin/chromium',
            '/usr/bin/google-chrome-stable'
        ]
        for p in linux_paths:
            if os.path.exists(p):
                BROWSER_PATH = p
                break

if not BROWSER_PATH:
    system = platform.system()
    if system == "Windows":
        raise RuntimeError('未检测到谷歌浏览器，请先安装Google Chrome！')
    elif system == "Darwin":
        raise RuntimeError('未检测到浏览器，请先安装Google Chrome或Chromium！\n建议运行: brew install --cask google-chrome')
    else:
        raise RuntimeError('未检测到浏览器，请先安装Google Chrome或Chromium！')

PLAYWRIGHT_HEADLESS=False # Playwright浏览器是否无头模式，False弹窗便于调试


# TTS服务相关配置 # 统一管理
TTS_API_KEY = os.getenv('TTS_API_KEY', 'your_api_key_here') # TTS服务API密钥
TTS_PORT = int(os.getenv('TTS_PORT', 5050)) # TTS服务端口
TTS_DEFAULT_VOICE = os.getenv('TTS_DEFAULT_VOICE', 'en-US-AvaNeural') # 默认语音
TTS_DEFAULT_FORMAT = os.getenv('TTS_DEFAULT_FORMAT', 'mp3') # 默认音频格式
TTS_DEFAULT_SPEED = float(os.getenv('TTS_DEFAULT_SPEED', 1.0)) # 默认语速
TTS_DEFAULT_LANGUAGE = os.getenv('TTS_DEFAULT_LANGUAGE', 'en-US') # 默认语言


# 快速响应小模型配置
# 用于快速决策和JSON格式化的轻量级模型
QUICK_MODEL_ENABLED = os.getenv("QUICK_MODEL_ENABLED", "false").lower() == "true"
QUICK_MODEL_API_KEY = os.getenv("QUICK_MODEL_API_KEY", "")  # 小模型API密钥
QUICK_MODEL_BASE_URL = os.getenv("QUICK_MODEL_BASE_URL", "")  # 小模型API地址
QUICK_MODEL_NAME = os.getenv("QUICK_MODEL_NAME", "qwen2.5-1.5b-instruct")  # 小模型名称

# 小模型参数配置
QUICK_MODEL_CONFIG = {
    "enabled": QUICK_MODEL_ENABLED,
    "api_key": QUICK_MODEL_API_KEY,
    "base_url": QUICK_MODEL_BASE_URL,
    "model_name": QUICK_MODEL_NAME,
    "max_tokens": 512,  # 小模型输出限制
    "temperature": 0.05,  # 极低温度确保稳定一致的输出
    "timeout": 5,  # 快速响应超时时间
    "max_retries": 2,  # 最大重试次数
    
    # 功能配置
    "quick_decision_enabled": True,  # 快速决策功能
    "json_format_enabled": True,    # JSON格式化功能
    "output_filter_enabled": True,  # 输出内容过滤功能
    "difficulty_judgment_enabled": True,  # 问题难度判断功能
    "scoring_system_enabled": True,  # 黑白名单打分系统
    "thinking_completeness_enabled": True,  # 思考完整性判断功能
}

# 输出过滤配置
OUTPUT_FILTER_CONFIG = {
    "filter_think_tags": True,  # 过滤<think></think>标签内容
    "filter_patterns": [
        r'<think>.*?</think>',  # 思考标签
        r'<thinking>.*?</thinking>',  # 思考标签
        r'<reflection>.*?</reflection>',  # 反思标签
        r'<internal>.*?</internal>',  # 内部思考标签
    ],
    "clean_output": True,  # 清理多余空白字符
}

# 问题难度判断配置
DIFFICULTY_JUDGMENT_CONFIG = {
    "enabled": True,
    "use_small_model": True,  # 使用小模型进行难度判断
    "difficulty_levels": ["简单", "中等", "困难", "极难"],
    "factors": [
        "概念复杂度",
        "推理深度", 
        "知识广度",
        "计算复杂度",
        "创新要求"
    ],
    "threshold_simple": 2,    # 简单问题阈值
    "threshold_medium": 4,    # 中等问题阈值
    "threshold_hard": 6,      # 困难问题阈值
}

# 黑白名单打分系统配置
SCORING_SYSTEM_CONFIG = {
    "enabled": True,
    "score_range": [1, 5],  # 评分范围：1-5分
    "score_threshold": 2,   # 结果保留阈值：2分及以下不保留
    "similarity_threshold": 0.85,  # 相似结果识别阈值
    "max_user_preferences": 3,  # 用户最多选择3个偏好
    "default_preferences": [
        "逻辑清晰准确",
        "实用性强", 
        "创新思维"
    ],
    "penalty_for_similar": 1,  # 相似结果的惩罚分数
    "min_results_required": 2,  # 最少保留结果数量（即使低于阈值）
    "strict_filtering": True,  # 严格过滤模式：True时严格按阈值过滤，False时保证最少结果数量
}

# 思考完整性判断配置
THINKING_COMPLETENESS_CONFIG = {
    "enabled": True,
    "use_small_model": True,  # 使用小模型判断思考完整性
    "completeness_criteria": [
        "问题分析充分",
        "解决方案明确",
        "逻辑链条完整",
        "结论清晰合理"
    ],
    "completeness_threshold": 0.8,  # 完整性阈值（0-1）
    "max_thinking_depth": 5,  # 最大思考深度层级
    "next_question_generation": True,  # 生成下一级问题
}

# 快速决策系统提示词
QUICK_DECISION_SYSTEM_PROMPT = """你是一个快速决策助手，专门进行简单判断和分类任务。
请根据用户输入快速给出准确的判断结果，保持简洁明确。
不需要详细解释，只需要给出核心判断结果。
【重要】：只输出最终结果，不要包含思考过程或<think>标签。"""

# JSON格式化系统提示词  
JSON_FORMAT_SYSTEM_PROMPT = """你是一个JSON格式化助手，专门将文本内容转换为结构化JSON格式。
请严格按照要求的JSON格式输出，确保语法正确且结构清晰。
只输出JSON内容，不要包含任何其他文字说明。
【重要】：只输出最终JSON，不要包含思考过程或<think>标签。"""

# 问题难度判断系统提示词
DIFFICULTY_JUDGMENT_SYSTEM_PROMPT = """你是一个问题难度评估专家，专门分析问题的复杂程度。
请根据问题的概念复杂度、推理深度、知识广度、计算复杂度、创新要求等因素进行评估。
只输出难度等级：简单、中等、困难、极难 中的一个。
【重要】：只输出难度等级，不要包含思考过程或解释。"""

# 结果打分系统提示词
RESULT_SCORING_SYSTEM_PROMPT = """你是一个结果评分专家，根据用户偏好和思考质量对结果进行1-5分评分。
评分标准：
- 5分：完全符合用户偏好，质量极高
- 4分：很好符合偏好，质量良好  
- 3分：基本符合偏好，质量一般
- 2分：部分符合偏好，质量较差
- 1分：不符合偏好或质量很差

请根据提供的思考结果和用户偏好进行评分。
【重要】：只输出数字分数，不要包含思考过程或解释。"""

# 思考完整性判断系统提示词
THINKING_COMPLETENESS_SYSTEM_PROMPT = """你是一个思考完整性评估专家，判断当前思考是否已经相对完整。
评估标准：
- 问题分析是否充分
- 解决方案是否明确
- 逻辑链条是否完整
- 结论是否清晰合理

如果思考完整，输出：完整
如果需要进一步思考，输出：不完整
【重要】：只输出"完整"或"不完整"，不要包含思考过程或解释。"""

# 下一级问题生成系统提示词
NEXT_QUESTION_SYSTEM_PROMPT = """你是一个问题设计专家，根据当前不完整的思考结果，设计下一级需要深入思考的核心问题。
要求：
- 问题应该针对当前思考的不足之处
- 问题应该能推进整体思考进程
- 问题应该具体明确，易于思考

请设计一个简洁的核心问题。
【重要】：只输出问题本身，不要包含思考过程或解释。"""
