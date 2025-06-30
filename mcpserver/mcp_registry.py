# mcp_registry.py # 自动注册所有MCP服务和handoff schema
import importlib, inspect, os
from pathlib import Path
import concurrent.futures # 新增线程池支持

MCP_REGISTRY = {} # 全局MCP服务池

def is_concrete_class(cls):
    # 过滤掉抽象基类
    if hasattr(cls, '__abstractmethods__') and len(cls.__abstractmethods__) > 0:
        return False
    # 彻底过滤所有名为Agent或ComputerTool的类（无论在哪个模块）
    if cls.__name__ in ['Agent', 'ComputerTool']:
        return False
    return True

def auto_register_mcp(mcp_dir='mcpserver'):
    d = Path(mcp_dir)
    agent_classes = [] # 需要初始化的Agent/Tool类列表
    for f in d.glob('**/*.py'):
        if f.stem.startswith('__'): continue
        m = importlib.import_module(f'{f.parent.as_posix().replace("/", ".")}.{f.stem}')
        for n, o in inspect.getmembers(m, inspect.isclass):
            if (n.endswith('Agent') or n.endswith('Tool')) and is_concrete_class(o):
                agent_classes.append((n, o))

    def init_agent(n_o):
        n, o = n_o
        try:
            instance = o()
            key = getattr(instance, 'name', n)
            MCP_REGISTRY[key] = instance # 用name属性作为key，保证与handoff一致
            return f"{key} 初始化成功"
        except Exception as e:
            return f"{n} 初始化失败: {e}"

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_class = {executor.submit(init_agent, n_o): n_o for n_o in agent_classes}
        for future in concurrent.futures.as_completed(future_to_class):
            result = future.result()
            results.append(result)
    return results

auto_register_mcp()

# handoff注册schema集中管理
HANDOFF_SCHEMAS = [
    {
        "service_name": "playwright",
        "tool_name": "browser_handoff",
        "tool_description": "处理所有浏览器相关操作",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要访问的URL"},
                "query": {"type": "string", "description": "原始查询文本"},
                "messages": {"type": "array", "description": "对话历史"},
                "source": {"type": "string", "description": "请求来源"}
            },
            "required": ["query", "messages"]
        },
        "agent_name": "Playwright Browser Agent",
        "strict_schema": False
    },
    {
        "service_name": "file",
        "tool_name": "file_handoff",
        "tool_description": "文件读写与管理",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（read/write/append/delete/mkdir等）"},
                "path": {"type": "string", "description": "文件或目录路径"},
                "content": {"type": "string", "description": "写入内容", "default": ""},
                "append": {"type": "boolean", "description": "是否追加", "default": False},
                "recursive": {"type": "boolean", "description": "递归删除", "default": False}
            },
            "required": ["action", "path"]
        },
        "agent_name": "File Agent",
        "strict_schema": False
    },
    {
        "service_name": "coder",
        "tool_name": "coder_handoff",
        "tool_description": "代码编辑与运行",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（edit/read/run/shell等）"},
                "file": {"type": "string", "description": "代码文件路径"},
                "code": {"type": "string", "description": "代码内容", "default": ""},
                "mode": {"type": "string", "description": "写入模式", "default": "w"}
            },
            "required": ["action", "file"]
        },
        "agent_name": "Coder Agent",
        "strict_schema": False
    },
    {
        "service_name": "app_launcher",
        "tool_name": "app_launcher_handoff",
        "tool_description": "本地应用启动与管理",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（open/list/refresh）"},
                "app": {"type": "string", "description": "应用名或路径"},
                "args": {"type": "array", "description": "启动参数", "items": {"type": "string"}, "default": []}
            },
            "required": ["action"]
        },
        "agent_name": "AppLauncher Agent",
        "strict_schema": False
    },
    {
        "service_name": "weather_time",
        "tool_name": "weather_time_handoff",
        "tool_description": "天气和时间查询",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（weather/time）"},
                "ip": {"type": "string", "description": "用户IP，可选，自动获取"},
                "city": {"type": "string", "description": "城市名，可选，自动识别"}
            },
            "required": ["action"]
        },
        "agent_name": "WeatherTime Agent",
        "strict_schema": False
    },
    {
        "service_name": "grag_memory",
        "tool_name": "grag_memory_handoff",
        "tool_description": "GRAG知识图谱记忆管理",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（query/stats/clear/extract）"},
                "question": {"type": "string", "description": "查询问题（query操作需要）"},
                "text": {"type": "string", "description": "要提取的文本（extract操作需要）"}
            },
            "required": ["action"]
        },
        "agent_name": "GRAG Memory Agent",
        "strict_schema": False
    },
]

# 删除shell相关schema
HANDOFF_SCHEMAS = [
    s for s in HANDOFF_SCHEMAS if s.get('service_name') != 'shell'
]

def register_all_handoffs(mcp_manager):
    """批量注册所有handoff服务"""
    registered = []
    for schema in HANDOFF_SCHEMAS:
        mcp_manager.register_handoff(
            service_name=schema["service_name"],
            tool_name=schema["tool_name"],
            tool_description=schema["tool_description"],
            input_schema=schema["input_schema"],
            agent_name=schema["agent_name"],
            strict_schema=schema.get("strict_schema", False)
        )
        registered.append(schema["service_name"])
    import sys
    sys.stderr.write(f'当前已注册服务: {registered}\n')