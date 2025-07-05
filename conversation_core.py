import logging
import os
# import asyncio # 日志与系统
from datetime import datetime # 时间
from mcpserver.mcp_manager import get_mcp_manager # 多功能管理
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX # handoff提示词
# from mcpserver.agent_playwright_master import ControllerAgent, BrowserAgent, ContentAgent # 导入浏览器相关类
from openai import OpenAI,AsyncOpenAI # LLM
# import difflib # 模糊匹配
import sys
import json
import traceback
import time # 时间戳打印
from mcpserver.mcp_registry import register_all_handoffs # 导入批量注册方法
import websockets 
import re # 添加re模块导入
from typing import List, Dict # 修复List未导入
from thinking import TreeThinkingEngine # 树状思考引擎
from thinking.config import COMPLEX_KEYWORDS # 复杂关键词
from config import config

# GRAG记忆系统导入
if config.grag.enabled:
    try:
        from summer_memory.memory_manager import memory_manager

    except Exception as e:
        logger = logging.getLogger("NagaConversation")
        logger.error(f"夏园记忆系统加载失败: {e}")
        memory_manager = None
else:
    memory_manager = None

def now():
    return time.strftime('%H:%M:%S:')+str(int(time.time()*1000)%10000) # 当前时间
_builtin_print=print
def print(*a, **k):
    return sys.stderr.write('[print] '+(' '.join(map(str,a)))+'\n')

# 配置日志 - 使用统一配置系统的日志级别
log_level = getattr(logging, config.system.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

# 特别设置httpcore和openai的日志级别，减少连接异常噪音
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)
logger = logging.getLogger("NagaConversation")

_MCP_HANDOFF_REGISTERED=False
_TREE_THINKING_SUBSYSTEMS_INITIALIZED=False

class NagaConversation: # 对话主类
    def __init__(self):
        self.mcp = get_mcp_manager()
        self.messages = []
        self.dev_mode = False
        self.client = OpenAI(api_key=config.api.api_key, base_url=config.api.base_url.rstrip('/') + '/')
        self.async_client = AsyncOpenAI(api_key=config.api.api_key, base_url=config.api.base_url.rstrip('/') + '/')
        
        # 初始化GRAG记忆系统（只在首次初始化时显示日志）
        self.memory_manager = memory_manager
        if self.memory_manager and not hasattr(self.__class__, '_memory_initialized'):
            logger.info("夏园记忆系统已初始化")
            self.__class__._memory_initialized = True
        
        # 集成树状思考系统（参考handoff的全局变量保护机制）
        global _TREE_THINKING_SUBSYSTEMS_INITIALIZED
        if not _TREE_THINKING_SUBSYSTEMS_INITIALIZED:
            try:
                self.tree_thinking = TreeThinkingEngine(api_client=self, memory_manager=self.memory_manager)
                print("[TreeThinkingEngine] ✅ 树状外置思考系统初始化成功")
                _TREE_THINKING_SUBSYSTEMS_INITIALIZED = True
            except Exception as e:
                logger.warning(f"树状思考系统初始化失败: {e}")
                self.tree_thinking = None
        else:
            # 如果子系统已经初始化过，创建新实例但不重新初始化子系统（静默处理）
            try:
                self.tree_thinking = TreeThinkingEngine(api_client=self, memory_manager=self.memory_manager)
            except Exception as e:
                logger.warning(f"树状思考系统实例创建失败: {e}")
                self.tree_thinking = None
        
        global _MCP_HANDOFF_REGISTERED
        if not _MCP_HANDOFF_REGISTERED:
            try:
                logger.info("开始注册所有Agent handoff处理器...")
                register_all_handoffs(self.mcp)  # 一键注册所有Agent
                logger.info("成功注册所有Agent handoff处理器")
                _MCP_HANDOFF_REGISTERED = True
            except Exception as e:
                logger.error(f"注册Agent handoff处理器失败: {e}")
                traceback.print_exc(file=sys.stderr)

    async def _init_websocket(self):
        """初始化WebSocket管理器"""
        try:
            await self.mcp.initialize_websocket(host=config.api_server.host, port=8081)
            logger.info("WebSocket管理器初始化完成")
        except Exception as e:
            logger.error(f"WebSocket管理器初始化失败: {e}")

    def save_log(self, u, a):  # 保存对话日志
        if self.dev_mode:
            return  # 开发者模式不写日志
        d = datetime.now().strftime('%Y-%m-%d')
        t = datetime.now().strftime('%H:%M:%S')
        
        # 确保日志目录存在
        log_dir = config.system.log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            logger.info(f"已创建日志目录: {log_dir}")
        
        f = os.path.join(log_dir, f'{d}.txt')
        with open(f, 'a', encoding='utf-8') as w:
            w.write('-'*50 + f'\n时间: {d} {t}\n用户: {u}\n娜迦: {a}\n\n')

    async def _call_llm(self, messages: List[Dict]) -> Dict:
        """调用LLM API"""
        try:
            resp = await self.async_client.chat.completions.create(
                model=config.api.model, 
                messages=messages, 
                temperature=config.api.temperature, 
                max_tokens=config.api.max_tokens, 
                stream=False  # 工具调用循环中不使用流式
            )
            return {
                'content': resp.choices[0].message.content,
                'status': 'success'
            }
        except RuntimeError as e:
            if "handler is closed" in str(e):
                logger.debug(f"忽略连接关闭异常: {e}")
                # 重新创建客户端并重试
                self.async_client = AsyncOpenAI(api_key=config.api.api_key, base_url=config.api.base_url.rstrip('/') + '/')
                resp = await self.async_client.chat.completions.create(
                    model=config.api.model, 
                    messages=messages, 
                    temperature=config.api.temperature, 
                    max_tokens=config.api.max_tokens, 
                    stream=False
                )
                return {
                    'content': resp.choices[0].message.content,
                    'status': 'success'
                }
            else:
                raise
        except Exception as e:
            logger.error(f"LLM API调用失败: {e}")
            return {
                'content': f"API调用失败: {str(e)}",
                'status': 'error'
            }

    # 工具调用循环相关方法
    def _parse_tool_calls(self, content: str) -> list:
        """解析TOOL_REQUEST格式的工具调用"""
        tool_calls = []
        tool_request_start = "<<<[TOOL_REQUEST]>>>"
        tool_request_end = "<<<[END_TOOL_REQUEST]>>>"
        start_index = 0
        while True:
            start_pos = content.find(tool_request_start, start_index)
            if start_pos == -1:
                break
            end_pos = content.find(tool_request_end, start_pos)
            if end_pos == -1:
                start_index = start_pos + len(tool_request_start)
                continue
            tool_content = content[start_pos + len(tool_request_start):end_pos].strip()
            tool_name = None
            tool_args = {}
            param_pattern = r'(\w+)\s*:\s*「始」([\s\S]*?)「末」'
            for match in re.finditer(param_pattern, tool_content):
                key = match.group(1)
                value = match.group(2).strip()
                if key == 'tool_name':
                    tool_name = value
                else:
                    tool_args[key] = value
            if tool_name:
                tool_calls.append({'name': tool_name, 'args': tool_args})
            start_index = end_pos + len(tool_request_end)
        return tool_calls

    async def _execute_tool_calls(self, tool_calls: list) -> str:
        """执行工具调用"""
        results = []
        for tool_call in tool_calls:
            try:
                result = await self.mcp.handoff(
                    service_name=tool_call['name'],
                    task=tool_call['args']
                )
                results.append(f"来自工具 \"{tool_call['name']}\" 的结果:\n{result}")
            except Exception as e:
                error_result = f"执行工具 {tool_call['name']} 时发生错误：{str(e)}"
                results.append(error_result)
        return "\n\n---\n\n".join(results)

    async def handle_tool_call_loop(self, messages: List[Dict], is_streaming: bool = False) -> Dict:
        """处理工具调用循环"""
        recursion_depth = 0
        max_recursion = config.handoff.max_loop_stream if is_streaming else config.handoff.max_loop_non_stream
        current_messages = messages.copy()
        current_ai_content = ''
        while recursion_depth < max_recursion:
            try:
                resp = await self._call_llm(current_messages)
                current_ai_content = resp.get('content', '')
                tool_calls = self._parse_tool_calls(current_ai_content)
                if not tool_calls:
                    break
                tool_results = await self._execute_tool_calls(tool_calls)
                current_messages.append({'role': 'assistant', 'content': current_ai_content})
                current_messages.append({'role': 'user', 'content': tool_results})
                recursion_depth += 1
            except Exception as e:
                print(f"工具调用循环错误: {e}")
                break
        return {
            'content': current_ai_content,
            'recursion_depth': recursion_depth,
            'messages': current_messages
        }

    def handle_llm_response(self, a, mcp):
        # 只保留普通文本流式输出逻辑 #
        async def text_stream():
            for line in a.splitlines():
                yield ("娜迦", line)
        return text_stream()

    async def process(self, u, is_voice_input=False):  # 添加is_voice_input参数
        try:
            # 开发者模式优先判断
            if u.strip() == "#devmode":
                self.dev_mode = True
                yield ("娜迦", "已进入开发者模式")
                return

            # 只在语音输入时显示处理提示
            if is_voice_input:
                print(f"开始处理用户输入：{now()}")  # 语音转文本结束，开始处理
            
            # GRAG记忆查询
            # memory_context = ""
            if self.memory_manager:
                try:
                    memory_result = await self.memory_manager.query_memory(u)
                    if memory_result:
                        # memory_context = f"\n[记忆检索结果]: {memory_result}\n"
                        logger.info("从GRAG记忆中检索到相关信息")
                except Exception as e:
                    logger.error(f"GRAG记忆查询失败: {e}")
            
            # 添加handoff提示词
            system_prompt = f"{RECOMMENDED_PROMPT_PREFIX}\n{config.prompts.naga_system_prompt}"
            sysmsg = {"role": "system", "content": system_prompt.format(available_mcp_services=self.mcp.format_available_services())}  # 直接使用系统提示词
            msgs = [sysmsg] if sysmsg else []
            msgs += self.messages[-20:] + [{"role": "user", "content": u}]

            print(f"GTP请求发送：{now()}")  # AI请求前
            
            # 树状思考系统控制指令
            if u.strip().startswith("#tree"):
                if self.tree_thinking is None:
                    yield ("娜迦", "树状思考系统未初始化，无法使用该功能")
                    return
                command = u.strip().split()
                if len(command) == 2:
                    if command[1] == "on":
                        self.tree_thinking.enable_tree_thinking(True)
                        yield ("娜迦", "🌳 树状外置思考系统已启用")
                        return
                    elif command[1] == "off":
                        self.tree_thinking.enable_tree_thinking(False)
                        yield ("娜迦", "树状思考系统已禁用，恢复普通对话模式")
                        return
                    elif command[1] == "status":
                        status = self.tree_thinking.get_system_status()
                        enabled_status = "启用" if status["enabled"] else "禁用"
                        yield ("娜迦", f"🌳 树状思考系统状态：{enabled_status}\n当前会话：{status['current_session']}\n历史会话数：{status['total_sessions']}")
                        return
                yield ("娜迦", "用法：#tree on/off/status")
                return
            
            # 检查是否需要自动触发树状思考
            tree_thinking_enabled = False
            if hasattr(self, 'tree_thinking') and self.tree_thinking and getattr(self.tree_thinking, 'is_enabled', False):
                question_lower = u.lower()
                complex_count = sum(1 for keyword in COMPLEX_KEYWORDS if keyword in question_lower)
                if complex_count >= 1 or len(u) > 50:
                    tree_thinking_enabled = True
                    logger.info(f"检测到复杂问题，启用树状思考 - 复杂关键词: {complex_count}, 长度: {len(u)}")
                    matched_keywords = [keyword for keyword in COMPLEX_KEYWORDS if keyword in question_lower]
                    logger.info(f"匹配的关键词: {matched_keywords}")
                else:
                    logger.info(f"未触发树状思考 - 复杂关键词: {complex_count}, 长度: {len(u)}")

            # 新增：树状思考处理
            if tree_thinking_enabled:
                try:
                    yield ("娜迦", "🌳 检测到复杂问题，启动树状外置思考系统...")
                    thinking_result = await self.tree_thinking.think_deeply(u)
                    if thinking_result and "answer" in thinking_result:
                        process_info = thinking_result.get("thinking_process", {})
                        difficulty = process_info.get("difficulty", {})
                        yield ("娜迦", "\n🧠 深度思考完成：")
                        yield ("娜迦", f"• 问题难度：{difficulty.get('difficulty', 'N/A')}/5")
                        yield ("娜迦", f"• 思考路线：{process_info.get('routes_generated', 0)}条 → {process_info.get('routes_selected', 0)}条")
                        yield ("娜迦", f"• 处理时间：{process_info.get('processing_time', 0):.2f}秒")
                        yield ("娜迦", f"\n{thinking_result['answer']}")
                        final_answer = thinking_result['answer']
                        self.messages += [{"role": "user", "content": u}, {"role": "assistant", "content": final_answer}]
                        self.save_log(u, final_answer)

                        # GRAG记忆存储（开发者模式不写入）
                        if self.memory_manager and not self.dev_mode:
                            try:
                                await self.memory_manager.add_conversation_memory(u, final_answer)
                            except Exception as e:
                                logger.error(f"GRAG记忆存储失败: {e}")
                        return
                    else:
                        yield ("娜迦", "🌳 树状思考处理异常，切换到普通模式...")
                except Exception as e:
                    logger.error(f"树状思考处理失败: {e}")
                    yield ("娜迦", f"🌳 树状思考系统出错，切换到普通模式: {str(e)}")
                    
            # 只走工具调用循环
            try:
                result = await self.handle_tool_call_loop(msgs, is_streaming=True)
                final_content = result['content']
                recursion_depth = result['recursion_depth']
                
                if recursion_depth > 0:
                    print(f"工具调用循环完成，共执行 {recursion_depth} 轮")
                
                # 流式输出最终结果
                for line in final_content.splitlines():
                    yield ("娜迦", line)
                
                # 保存对话历史
                self.messages += [{"role": "user", "content": u}, {"role": "assistant", "content": final_content}]
                self.save_log(u, final_content)
                
                # GRAG记忆存储（开发者模式不写入）
                if self.memory_manager and not self.dev_mode:
                    try:
                        await self.memory_manager.add_conversation_memory(u, final_content)
                    except Exception as e:
                        logger.error(f"GRAG记忆存储失败: {e}")
                
            except Exception as e:
                print(f"工具调用循环失败: {e}")
                yield ("娜迦", f"[MCP异常]: {e}")
                return

            return
        except Exception as e:
            import sys
            import traceback
            traceback.print_exc(file=sys.stderr)
            yield ("娜迦", f"[MCP异常]: {e}")
            return

    async def get_response(self, prompt: str, temperature: float = 0.7) -> str:
        """为树状思考系统等提供API调用接口""" # 统一接口
        try:
            response = await self.async_client.chat.completions.create(
                model=config.api.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=config.api.max_tokens
            )
            return response.choices[0].message.content
        except RuntimeError as e:
            if "handler is closed" in str(e):
                logger.debug(f"忽略连接关闭异常，重新创建客户端: {e}")
                # 重新创建客户端并重试
                self.async_client = AsyncOpenAI(api_key=config.api.api_key, base_url=config.api.base_url.rstrip('/') + '/')
                response = await self.async_client.chat.completions.create(
                    model=config.api.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=config.api.max_tokens
                )
                return response.choices[0].message.content
            else:
                logger.error(f"API调用失败: {e}")
                return f"API调用出错: {str(e)}"
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            return f"API调用出错: {str(e)}"

async def process_user_message(s,msg):
    if config.system.voice_enabled and not msg: #无文本输入时启动语音识别
        async for text in s.voice.stt_stream():
            if text:
                msg=text
                break
        return await s.process(msg, is_voice_input=True)  # 语音输入
    return await s.process(msg, is_voice_input=False)  # 文字输入

async def send_ai_message(s, msg):
    # 启用语音时，通过WebSocket流式推送到voice/genVoice服务
    if config.system.voice_enabled:
        ws_url = f"ws://127.0.0.1:{config.tts.port}/genVoice"  # WebSocket服务地址
        try:
            async with websockets.connect(ws_url) as websocket:
                await websocket.send(msg)  # 发送文本到TTS服务
                while True:
                    response = await websocket.recv()  # 接收音频流（json）
                    data = json.loads(response)
                    # data结构: {"seq":..., "text":..., "wav_base64":..., "duration":...}
                    # 这里可以推送data到前端或本地播放器
                    print(f"收到音频片段: 序号{data['seq']}，时长{data['duration']}秒")  # 示例：打印信息
                    # 如需流式返回，可 yield data
                    # 可根据需求break或继续接收
        except Exception as e:
            print(f"WebSocket TTS服务调用异常: {e}")
    return msg  # 始终返回文本
