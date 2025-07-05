import os
from dotenv import load_dotenv
from agents import Agent, AgentHooks, RunContextWrapper
from .controller import BrowserAgent
from .browser import ContentAgent
from config import MODEL_NAME

load_dotenv()
API_KEY  = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

class ControllerAgentHooks(AgentHooks):
    async def on_start(self, context: RunContextWrapper, agent: Agent):
        print(f"[ControllerAgent] 开始: {agent.name}")
    async def on_end(self, context: RunContextWrapper, agent: Agent, output):
        print(f"[ControllerAgent] 结束: {agent.name}, 输出: {output}")

class ControllerAgent(Agent):
    """浏览器控制Agent #"""
    name = "ControllerAgent"
    instructions = "你负责理解用户目标，自动分配任务给BrowserAgent和ContentAgent，并汇总结果。"
    def __init__(self):
        super().__init__(
            name=self.name,
            instructions=self.instructions,
            tools=[],  # 可扩展
            model=MODEL_NAME
        )
        # 可选：初始化BrowserAgent/ContentAgent引用
        import sys
        sys.stderr.write('✅ ControllerAgent初始化完成\n')

    async def handle_handoff(self, task: dict) -> str:
        """处理MCP handoff请求，智能分配任务 #"""
        try:
            action = task.get("action", "")
            task_type = task.get("task_type", "")
            # 这里只做简单模拟，实际可调用BrowserAgent/ContentAgent
            if task_type == "browser" or action in ["open", "click", "type", "scroll", "wait_for_element", "take_screenshot", "search_github"]:
                return f"BrowserAgent已处理页面操作: {action}"
            elif task_type == "content" or action in ["get_content", "get_title", "get_screenshot", "subscribe_page_change"]:
                return f"ContentAgent已处理内容任务: {action}"
            else:
                return f"ControllerAgent正在协调多Agent处理复杂任务: {action}"
        except Exception as e:
            return f"ControllerAgent处理失败: {str(e)}"

ControllerAgent = Agent(
    name="ControllerAgent",
    instructions="你负责理解用户目标，自动分配任务给BrowserAgent和ContentAgent，并汇总结果。",
    handoffs=[BrowserAgent, ContentAgent],
    hooks=ControllerAgentHooks(),
    model=MODEL_NAME
) 
