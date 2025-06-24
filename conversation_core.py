import logging,os,asyncio # 日志与系统
from datetime import datetime # 时间
from config import LOG_DIR,DEEPSEEK_API_KEY,DEEPSEEK_MODEL,TEMPERATURE,MAX_TOKENS,get_current_datetime,THEME_ROOTS,DEEPSEEK_BASE_URL,NAGA_SYSTEM_PROMPT,VOICE_ENABLED # 配置
# from summer.summer_faiss import faiss_recall,faiss_add,faiss_fuzzy_recall # faiss检索与入库 # 注释掉faiss导入
from mcpserver.mcp_manager import get_mcp_manager, remove_tools_filter, HandoffInputData # 多功能管理
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX # handoff提示词
from mcpserver.agent_playwright_master import PlaywrightAgent, extract_url # 导入浏览器相关类
from openai import OpenAI,AsyncOpenAI # LLM
import difflib # 模糊匹配
import sys,json,traceback
import time # 时间戳打印
from summer.memory_manager import MemoryManager  # 新增
from mcpserver.mcp_registry import register_all_handoffs # 导入批量注册方法
from voice.tts_handler import generate_speech, get_models, get_voices # TTS功能
import config
import asyncio
import json
import websockets 
import re # 添加re模块导入
from typing import List, Dict # 修复List未导入
now=lambda:time.strftime('%H:%M:%S:')+str(int(time.time()*1000)%10000) # 当前时间
_builtin_print=print
print=lambda *a,**k:sys.stderr.write('[print] '+(' '.join(map(str,a)))+'\n')

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("NagaConversation")

_MCP_HANDOFF_REGISTERED=False

class NagaConversation: # 对话主类
    def __init__(self):
        self.mcp = get_mcp_manager()
        self.messages = []
        self.dev_mode = False
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL.rstrip('/') + '/')
        self.async_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL.rstrip('/') + '/')
        self.memory = MemoryManager()  # 新增：初始化记忆管理器
        self.compat_mode = False  # 新增：兼容升级模式状态
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

    def save_log(self, u, a):  # 保存对话日志
        if self.dev_mode:
            return  # 开发者模式不写日志
        d = datetime.now().strftime('%Y-%m-%d')
        t = datetime.now().strftime('%H:%M:%S')
        f = os.path.join(LOG_DIR, f'{d}.txt')
        with open(f, 'a', encoding='utf-8') as w:
            w.write(f'-'*50 + f'\n时间: {d} {t}\n用户: {u}\n娜迦: {a}\n\n')

    def normalize_theme(self, raw):  # 主题归一化
        seg = raw.split('/')
        root = difflib.get_close_matches(seg[0], THEME_ROOTS.keys(), n=1, cutoff=0.6)
        root = root[0] if root else list(THEME_ROOTS.keys())[0]
        if len(seg) > 1:
            sub = difflib.get_close_matches(seg[1], THEME_ROOTS[root], n=1, cutoff=0.6)
            sub = sub[0] if sub else THEME_ROOTS[root][0]
            return '/'.join([root, sub] + seg[2:])
        return root

    def get_theme_and_level(self, u):  # LLM主题+分层判定
        r = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "请用/分隔输出本轮对话主题树（如'科技/人工智能/大模型'），并判断内容应归为哪类记忆层级（core/archival/long_term/short_term）。\n请用如下JSON格式返回：{\"theme\": \"主题树\", \"level\": \"core/archival/long_term/short_term\"}，不要多余内容。"},
                {"role": "user", "content": u}
            ],
            temperature=0.2,
            max_tokens=40
        ).choices[0].message.content
        try:
            result = json.loads(r)
            theme = self.normalize_theme(result.get('theme', ''))
            level = result.get('level', '').strip().lower()
            if level not in ['core', 'archival', 'long_term', 'short_term']:
                level = None
            return theme, level
        except Exception:
            # 兜底：只用原有主题判定，分层用规则
            theme = self.normalize_theme(u)
            text = u
            if '身份' in text:
                level = 'core'
            elif '重要事件' in text:
                level = 'archival'
            elif len(text) > 30:
                level = 'long_term'
            else:
                level = 'short_term'
            return theme, level

    def get_theme(self, u):  # 兼容接口，内部用get_theme_and_level
        theme, _ = self.get_theme_and_level(u)
        return theme

    async def _call_llm(self, messages: List[Dict]) -> Dict:
        """调用LLM API"""
        resp = await self.async_client.chat.completions.create(
            model=DEEPSEEK_MODEL, 
            messages=messages, 
            temperature=TEMPERATURE, 
            max_tokens=MAX_TOKENS, 
            stream=False  # 工具调用循环中不使用流式
        )
        return {
            'content': resp.choices[0].message.content,
            'status': 'success'
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

    async def execute_tool_calls(self, tool_calls: list) -> str:
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
        max_recursion = int(os.getenv('MaxVCPLoopStream', '5')) if is_streaming else int(os.getenv('MaxVCPLoopNonStream', '5'))
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

    def handle_compat_upgrade(self, u):
        if u.strip() == '#夏园系统兼容升级':
            import subprocess, os, json
            LOG_DIR = 'logs'
            txt_files = [fn for fn in os.listdir(LOG_DIR) if fn.endswith('.txt') and fn[:4].isdigit() and fn[4] == '-' and fn[7] == '-']
            txt_files.sort()
            file_list_str = '发现以下历史对话日志：\n' + '\n'.join([f'{idx+1}. {fn}' for idx, fn in enumerate(txt_files)]) + '\n' + '-'*40
            subprocess.run(['python', 'summer/summer_upgrade/compat_txt_to_faiss.py', 'list'])
            HISTORY_JSON = os.path.join('summer', 'summer_upgrade', 'history_dialogs.json')
            try:
                with open(HISTORY_JSON, encoding='utf-8') as f:
                    all_chunks = json.load(f)
                total = len(all_chunks)
            except Exception:
                total = 0
            msg = f"{file_list_str}\n共{total}条历史对话，已预热缓存至summer/summer_upgrade/history_dialogs.json\n请直接在对话框输入import命令（如import all或import 1,3,5-8）以完成选择性兼容。\n如需退出兼容模式，请输入exit。"
            self.compat_mode = True
            return ("系统", msg)
        return None

    async def process(self, u, is_voice_input=False):  # 添加is_voice_input参数
        import json  # 保证json在本地作用域可用
        try:
            # 开发者模式优先判断
            if u.strip() == "#devmode":
                self.dev_mode = True
                yield ("娜迦", "已进入开发者模式，后续对话不写入向量库")
                return
            # 兼容升级模式优先判断
            compat_result = self.handle_compat_upgrade(u)
            if compat_result:
                yield compat_result
                return
            # 兼容模式判断
            if hasattr(self, 'compat_mode') and self.compat_mode:
                if u.strip().startswith('import '):
                    import subprocess, sys
                    args = u.strip().split(' ', 1)[1]
                    yield ("系统", "正在执行兼容导入程序，请稍候...")
                    result = subprocess.run(
                        [sys.executable, 'summer/summer_upgrade/compat_txt_to_faiss.py', 'import', args],
                        capture_output=True, text=True
                    )
                    output = result.stdout.strip() or result.stderr.strip()
                    yield ("系统", f"兼容导入结果：\n{output}")
                    return
                elif u.strip() in ['exit', '完成', '退出兼容']:
                    self.compat_mode = False
                    yield ("系统", "已退出系统兼容升级模式，恢复正常对话。")
                    return
                else:
                    yield ("系统", "当前为系统兼容升级模式，仅支持import指令。如需退出，请输入exit。")
                    return

            # 只在语音输入时显示处理提示
            if is_voice_input:
                print(f"开始处理用户输入：{now()}")  # 语音转文本结束，开始处理
            theme, level = self.get_theme_and_level(u)
            # ctx = self.memory.build_context(u, k=5)  # 注释掉向量检索
            # 添加handoff提示词
            system_prompt = f"{RECOMMENDED_PROMPT_PREFIX}\n{NAGA_SYSTEM_PROMPT}"
            sysmsg = {"role": "system", "content": system_prompt.format(available_mcp_services=self.mcp.format_available_services())}  # 直接使用系统提示词，不包含历史召回
            msgs = [sysmsg] if sysmsg else []
            msgs += self.messages[-20:] + [{"role": "user", "content": u}]

            print(f"GTP请求发送：{now()}")  # AI请求前
            
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
                
            except Exception as e:
                print(f"工具调用循环失败: {e}")
                yield ("娜迦", f"[MCP异常]: {e}")
                return

            if not self.dev_mode:
                pass
            self.memory.add_memory({'role': 'user', 'text': u, 'time': get_current_datetime(), 'file': datetime.now().strftime('%Y-%m-%d') + '.txt', 'theme': theme}, level=level)
            self.memory.add_memory({'role': 'ai', 'text': final_content if 'final_content' in locals() else '', 'time': get_current_datetime(), 'file': datetime.now().strftime('%Y-%m-%d') + '.txt', 'theme': theme}, level=level)
            # 支持用户通过#important <内容片段>命令标记记忆为重要
            if u.strip().startswith('#important'):
                mark_text = u.strip()[10:].strip()
                if not mark_text:
                    yield ("娜迦", "请在#important后输入要标记的重要内容片段。")
                    return
                recall = self.memory.fuzzy_recall(mark_text, k=5)
                if recall:
                    keys = [item.get('key') for item in recall if 'key' in item]
                    if len(keys) == 1:
                        self.memory.mark_important(keys[0])
                        yield ("娜迦", f"已将相关记忆片段标记为重要：{recall[0].get('text', '')}")
                        return
                    else:
                        updated = self.memory.mark_important_batch(keys)
                        preview = "\n".join([f"{i+1}.{item.get('text', '')[:30]}" for i, item in enumerate(recall)])
                        yield ("娜迦", f"已批量标记{updated}条相关记忆为重要：\n{preview}")
                        return
                else:
                    yield ("娜迦", "未找到相关记忆，无法标记。")
                    return
            # 每20轮动态批量衰减权重
            self.memory.adjust_weights_periodically()
            return
        except Exception as e:
            import sys, traceback
            traceback.print_exc(file=sys.stderr)
            yield ("娜迦", f"[MCP异常]: {e}")
            return

async def process_user_message(s,msg):
    if VOICE_ENABLED and not msg: #无文本输入时启动语音识别
        async for text in s.voice.stt_stream():
            if text:
                msg=text
                break
        return await s.process(msg, is_voice_input=True)  # 语音输入
    return await s.process(msg, is_voice_input=False)  # 文字输入

async def send_ai_message(s, msg):
    # 启用语音时，通过WebSocket流式推送到voice/genVoice服务
    if config.VOICE_ENABLED:
        ws_url = f"ws://127.0.0.1:{config.TTS_PORT}/genVoice"  # WebSocket服务地址
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
