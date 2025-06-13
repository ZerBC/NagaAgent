import logging,os,asyncio # 日志与系统
from datetime import datetime # 时间
from config import LOG_DIR,DEEPSEEK_API_KEY,DEEPSEEK_MODEL,TEMPERATURE,MAX_TOKENS,get_current_datetime,THEME_ROOTS,DEEPSEEK_BASE_URL,NAGA_SYSTEM_PROMPT,VOICE_ENABLED # 配置
from summer.summer_faiss import faiss_recall,faiss_add,faiss_fuzzy_recall # faiss检索与入库
from mcpserver.mcp_manager import get_mcp_manager, remove_tools_filter, HandoffInputData # 多功能管理
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX # handoff提示词
from mcpserver.agent_playwright_master import PlaywrightAgent, extract_url # 导入浏览器相关类
from openai import OpenAI,AsyncOpenAI # LLM
import difflib # 模糊匹配
import sys,json,traceback
import time # 时间戳打印
from summer.memory_manager import MemoryManager  # 新增
from mcpserver.mcp_registry import register_all_handoffs # 导入批量注册方法
from handoff_executor import execute_plan
from voice.tts_handler import generate_speech, get_models, get_voices # TTS功能
import config
import asyncio
import json
import websockets 
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langchain_core.runnables import RunnableConfig
from agent.state import OverallState, QueryGenerationState, ReflectionState, WebSearchState # 从state.py导入状态类

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

# 新增：配置类
class AgentConfiguration(BaseModel):
    """智能体配置类"""
    query_generator_model: str = Field(default="deepseek-chat")
    reflection_model: str = Field(default="deepseek-chat")
    answer_model: str = Field(default="deepseek-chat")
    number_of_initial_queries: int = Field(default=3)
    max_research_loops: int = Field(default=2)

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> "AgentConfiguration":
        """从RunnableConfig创建配置实例"""
        configurable = config.get("configurable", {}) if config else {}
        return cls(**configurable)

class NagaConversation:
    def __init__(self):
        self.mcp = get_mcp_manager()
        self.messages = []
        self.dev_mode = False
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL.rstrip('/') + '/')
        self.async_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL.rstrip('/') + '/')
        self.memory = MemoryManager()
        self.compat_mode = False
        self.agent_config = AgentConfiguration()
        
        # 初始化Agent Graph
        self.graph = self._build_agent_graph()
        
        global _MCP_HANDOFF_REGISTERED
        if not _MCP_HANDOFF_REGISTERED:
            try:
                logger.info("开始注册所有Agent handoff处理器...")
                register_all_handoffs(self.mcp)
                logger.info("成功注册所有Agent handoff处理器")
                _MCP_HANDOFF_REGISTERED = True
            except Exception as e:
                logger.error(f"注册Agent handoff处理器失败: {e}")
                traceback.print_exc(file=sys.stderr)

    def _build_agent_graph(self) -> StateGraph:
        """构建Agent执行图"""
        builder = StateGraph(OverallState, config_schema=AgentConfiguration)
        
        # 添加节点
        builder.add_node("generate_query", self._generate_query)
        builder.add_node("web_research", self._web_research)
        builder.add_node("reflection", self._reflection)
        builder.add_node("finalize_answer", self._finalize_answer)
        
        # 设置边
        builder.add_edge(START, "generate_query")
        builder.add_conditional_edges(
            "generate_query", 
            self._continue_to_web_research, 
            ["web_research"]
        )
        builder.add_edge("web_research", "reflection")
        builder.add_conditional_edges(
            "reflection", 
            self._evaluate_research, 
            ["web_research", "finalize_answer"]
        )
        builder.add_edge("finalize_answer", END)
        
        return builder.compile(name="naga-agent")

    async def _generate_query(self, state: OverallState, config: RunnableConfig) -> QueryGenerationState:
        """生成搜索查询"""
        configurable = AgentConfiguration.from_runnable_config(config)
        
        if state.get("initial_search_query_count") is None:
            state["initial_search_query_count"] = configurable.number_of_initial_queries
            
        # 使用现有LLM生成查询
        response = await self.async_client.chat.completions.create(
            model=configurable.query_generator_model,
            messages=[
                {"role": "system", "content": "请生成搜索查询列表"},
                {"role": "user", "content": state["messages"][-1].content}
            ],
            temperature=1.0,
            max_tokens=MAX_TOKENS
        )
        
        queries = response.choices[0].message.content.split("\n")
        return {"query_list": queries}

    def _continue_to_web_research(self, state: QueryGenerationState):
        """继续网络研究"""
        return [
            Send("web_research", {"search_query": query, "id": idx})
            for idx, query in enumerate(state["query_list"])
        ]

    async def _web_research(self, state: WebSearchState, config: RunnableConfig) -> OverallState:
        """执行网络研究"""
        configurable = AgentConfiguration.from_runnable_config(config)
        
        # 使用现有LLM进行网络研究
        response = await self.async_client.chat.completions.create(
            model=configurable.query_generator_model,
            messages=[
                {"role": "system", "content": "请进行网络研究"},
                {"role": "user", "content": state["search_query"]}
            ],
            temperature=0,
            max_tokens=MAX_TOKENS
        )
        
        return {
            "sources_gathered": [],
            "search_query": [state["search_query"]],
            "web_research_result": [response.choices[0].message.content]
        }

    async def _reflection(self, state: OverallState, config: RunnableConfig) -> ReflectionState:
        """反思和生成后续查询"""
        configurable = AgentConfiguration.from_runnable_config(config)
        state["research_loop_count"] = state.get("research_loop_count", 0) + 1
        
        response = await self.async_client.chat.completions.create(
            model=configurable.reflection_model,
            messages=[
                {"role": "system", "content": "请分析当前研究结果并生成后续查询"},
                {"role": "user", "content": "\n\n".join(state["web_research_result"])}
            ],
            temperature=1.0,
            max_tokens=MAX_TOKENS
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "is_sufficient": result.get("is_sufficient", True),
            "knowledge_gap": result.get("knowledge_gap", ""),
            "follow_up_queries": result.get("follow_up_queries", []),
            "research_loop_count": state["research_loop_count"],
            "number_of_ran_queries": len(state["search_query"])
        }

    def _evaluate_research(self, state: ReflectionState, config: RunnableConfig):
        """评估研究进度"""
        configurable = AgentConfiguration.from_runnable_config(config)
        max_research_loops = state.get("max_research_loops", configurable.max_research_loops)
        
        if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
            return "finalize_answer"
        else:
            return [
                Send(
                    "web_research",
                    {
                        "search_query": query,
                        "id": state["number_of_ran_queries"] + idx
                    }
                )
                for idx, query in enumerate(state["follow_up_queries"])
            ]

    async def _finalize_answer(self, state: OverallState, config: RunnableConfig):
        """生成最终答案"""
        configurable = AgentConfiguration.from_runnable_config(config)
        
        response = await self.async_client.chat.completions.create(
            model=configurable.answer_model,
            messages=[
                {"role": "system", "content": "请生成最终研究报告"},
                {"role": "user", "content": "\n---\n".join(state["web_research_result"])}
            ],
            temperature=0,
            max_tokens=MAX_TOKENS
        )
        
        return {
            "messages": [AIMessage(content=response.choices[0].message.content)],
            "sources_gathered": state["sources_gathered"]
        }

    # 保留原有的方法
    def save_log(self, u, a):
        if self.dev_mode:
            return
        d = datetime.now().strftime('%Y-%m-%d')
        t = datetime.now().strftime('%H:%M:%S')
        f = os.path.join(LOG_DIR, f'{d}.txt')
        with open(f, 'a', encoding='utf-8') as w:
            w.write(f'-'*50 + f'\n时间: {d} {t}\n用户: {u}\n娜迦: {a}\n\n')

    def normalize_theme(self, raw):
        seg = raw.split('/')
        root = difflib.get_close_matches(seg[0], THEME_ROOTS.keys(), n=1, cutoff=0.6)
        root = root[0] if root else list(THEME_ROOTS.keys())[0]
        if len(seg) > 1:
            sub = difflib.get_close_matches(seg[1], THEME_ROOTS[root], n=1, cutoff=0.6)
            sub = sub[0] if sub else THEME_ROOTS[root][0]
            return '/'.join([root, sub] + seg[2:])
        return root

    def get_theme_and_level(self, u):
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

    def get_theme(self, u):
        theme, _ = self.get_theme_and_level(u)
        return theme

    async def handle_llm_response(self, a, mcp):
        import json
        try:
            resp_json = json.loads(a)
            if "plan" in resp_json:
                from handoff_executor import execute_plan
                async for _ in execute_plan(resp_json, mcp):
                    pass
                return
        except Exception:
            pass
        for line in a.splitlines():
            yield ("娜迦", line)

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

    async def process(self, u):
        import json
        try:
            if u.strip() == "#devmode":
                self.dev_mode = True
                yield ("娜迦", "已进入开发者模式，后续对话不写入向量库")
                return
                
            compat_result = self.handle_compat_upgrade(u)
            if compat_result:
                yield compat_result
                return
                
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

            print(f"语音转文本结束，开始发送给GTP：{now()}")
            theme, level = self.get_theme_and_level(u)
            ctx = self.memory.build_context(u, k=5)
            
            # 添加handoff提示词
            system_prompt = f"{RECOMMENDED_PROMPT_PREFIX}\n{NAGA_SYSTEM_PROMPT}"
            sysmsg = {"role": "system", "content": f"历史相关内容召回:\n{ctx}\n\n{system_prompt.format(available_mcp_services=self.mcp.format_available_services())}"} if ctx else {"role": "system", "content": system_prompt.format(available_mcp_services=self.mcp.format_available_services())}
            msgs = [sysmsg] if sysmsg else []
            msgs += self.messages[-20:] + [{"role": "user", "content": u}]

            print(f"GTP请求发送：{now()}")
            
            # 使用Agent Graph处理
            initial_state = {
                "messages": msgs,
                "initial_search_query_count": self.agent_config.number_of_initial_queries,
                "max_research_loops": self.agent_config.max_research_loops,
                "research_loop_count": 0,
                "reasoning_model": self.agent_config.query_generator_model,
                "search_query": [],
                "web_research_result": [],
                "sources_gathered": [],
                "theme": theme,
                "memory_level": level,
                "context": ctx
            }
            
            async for step in self.graph.astream(initial_state):
                if "messages" in step:
                    async for item in self.handle_llm_response(step["messages"][-1].content, self.mcp):
                        yield item
                    break

            self.messages += [{"role": "user", "content": u}, {"role": "assistant", "content": step["messages"][-1].content}]
            self.save_log(u, step["messages"][-1].content)
            
            if not self.dev_mode:
                faiss_add([{
                    'text': step["messages"][-1].content,
                    'role': 'ai',
                    'time': get_current_datetime(),
                    'file': 'conversation.txt',
                    'theme': theme
                }])
                
            self.memory.add_memory({'role': 'user', 'text': u, 'time': get_current_datetime(), 'file': datetime.now().strftime('%Y-%m-%d') + '.txt', 'theme': theme}, level=level)
            self.memory.add_memory({'role': 'ai', 'text': step["messages"][-1].content, 'time': get_current_datetime(), 'file': datetime.now().strftime('%Y-%m-%d') + '.txt', 'theme': theme}, level=level)
            
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
                    
            self.memory.adjust_weights_periodically()
            return
            
        except Exception as e:
            import sys, traceback
            traceback.print_exc(file=sys.stderr)
            yield ("娜迦", f"[MCP异常]: {e}")
            return

async def process_user_message(s,msg):
    if VOICE_ENABLED and not msg:
        async for text in s.voice.stt_stream():
            if text:msg=text;break
    return await s.process(msg)

async def send_ai_message(s, msg):
    if config.VOICE_ENABLED:
        ws_url = f"ws://127.0.0.1:{config.TTS_PORT}/genVoice"
        try:
            async with websockets.connect(ws_url) as websocket:
                await websocket.send(msg)
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    print(f"收到音频片段: 序号{data['seq']}，时长{data['duration']}秒")
        except Exception as e:
            print(f"WebSocket TTS服务调用异常: {e}")
    return msg