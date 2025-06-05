import json
from mcpserver.mcp_manager import MCPManager
import asyncio
import sys

class TaskNode:
    """
    链式任务节点，支持动态决策和on_result钩子
    """
    def __init__(self, node_id, agent=None, params=None, desc="", next_node=None, parallel=None):
        self.node_id = node_id
        self.agent = agent
        self.params = params or {}
        self.desc = desc
        self.next_node = next_node  # TaskNode/dict/list/None
        self.parallel = parallel    # list of TaskNode

class TaskGraphExecutor:
    def __init__(self, start_node, mcp_manager):
        self.start_node = start_node
        self.mcp_manager = mcp_manager

    async def run(self, context=None, yield_func=None):
        context = context or {}
        await self._run_node(self.start_node, context, yield_func)
        return context

    async def _run_node(self, node, context, yield_func):
        if not node:
            return
        # 并行分支
        if node.parallel:
            if yield_func:
                await yield_func({"desc": node.desc, "status": "start", "msg": "并行分支开始"})
            await asyncio.gather(*(self._run_node(n, context, yield_func) for n in node.parallel))
            return
        # 执行当前节点
        result = None
        if node.agent:
            if yield_func:
                await yield_func({"desc": node.desc, "status": "start"})
            try:
                result = await self.mcp_manager.handoff(node.agent, node.params)
                msg = result
                try:
                    result_json = json.loads(result)
                    msg = result_json.get("data", {}).get("content") or result_json.get("message") or str(result_json.get("status"))
                except Exception:
                    pass
                context[f"{node.node_id}_result"] = result
                if yield_func:
                    await yield_func({"desc": node.desc, "status": "success", "msg": msg, "raw": result})
            except Exception as e:
                if yield_func:
                    await yield_func({"desc": node.desc, "status": "error", "msg": str(e)})
                return
        # 动态决策
        next_node = None
        if isinstance(node.next_node, TaskNode):
            next_node = node.next_node
        elif isinstance(node.next_node, dict):
            status = None
            try:
                result_json = json.loads(result)
                status = result_json.get("status")
            except Exception:
                status = "success"
            next_node = node.next_node.get(status) or node.next_node.get("success") or node.next_node.get("default")
        # 递归执行
        if next_node:
            await self._run_node(next_node, context, yield_func)

def plan_to_graph(plan, mcp_manager):
    """
    将plan结构自动转换为链式任务流
    """
    steps = plan.get("steps", [])
    node_map = {}
    # 1. 创建所有节点
    for step in steps:
        action = step.get("action", {})
        agent = action.get("agent")
        # 兼容action.params嵌套结构
        params = action.get("params", {}).copy() if "params" in action else action.copy() if action else {}
        if "agent" in params:
            del params["agent"]
        # 自动兼容plan参数命名
        if 'operation' in params:
            params['action'] = params.pop('operation')
        if 'task' in params:
            params['action'] = params.pop('task')
        node = TaskNode(
            node_id=step["id"],
            agent=agent,
            params=params,
            desc=step.get("desc", ""),
            next_node=step.get("next"),
            parallel=step.get("parallel")
        )
        node_map[step["id"]] = node
    # 2. 处理 next/parallel 字段
    for node in node_map.values():
        if isinstance(node.next_node, str):
            node.next_node = node_map.get(node.next_node)
        elif isinstance(node.next_node, dict):
            for k, v in node.next_node.items():
                node.next_node[k] = node_map.get(v)
        if node.parallel:
            node.parallel = [node_map[pid] for pid in node.parallel]
    start_id = plan.get("start") or (steps[0]["id"] if steps else None)
    return node_map.get(start_id)

async def execute_plan(plan_json, mcp_manager):
    """
    执行LLM返回的plan结构，自动分步handoff调用agent
    :param plan_json: LLM返回的完整json字符串或已解析dict
    :param mcp_manager: MCP管理器实例，需有handoff(agent, params)方法
    :yield: dict，每步执行的实时反馈，前端可直接消费
    """
    try:
        if isinstance(plan_json, str):
            try:
                resp_json = json.loads(plan_json)
            except Exception as e:
                sys.stderr.write(f"[execute_plan] plan解析失败: {e}\n原始内容: {plan_json}\n")
                yield {"type": "error", "msg": f"plan解析失败: {e}"}
                return
        else:
            resp_json = plan_json

        if "plan" not in resp_json:
            sys.stderr.write(f"[execute_plan] 未检测到plan结构: {resp_json}\n")
            yield {"type": "error", "msg": "未检测到plan结构，无法自动分步执行。"}
            return

        plan = resp_json["plan"]
        # 判断是否为新格式
        if "start" in plan and "steps" in plan and any("id" in s for s in plan["steps"]):
            sys.stderr.write(f"[execute_plan] 检测到新plan格式，开始转换为任务流\n")
            start_node = plan_to_graph(plan, mcp_manager)
            executor = TaskGraphExecutor(start_node, mcp_manager)
            # 兼容 yield
            class YieldCollector:
                def __init__(self):
                    self.steps = []
                async def __call__(self, step):
                    self.steps.append(step)
                    return  # 不要yield
            collector = YieldCollector()
            await executor.run(yield_func=collector)
            for step in collector.steps:
                yield step
            sys.stderr.write(f"[execute_plan] 所有任务已完成\n")
            yield {"type": "done", "msg": "所有任务已完成"}
            return

        # 原有分步机制兜底
        sys.stderr.write(f"[execute_plan] 使用原有分步机制兜底\n")
        steps = plan.get("steps", [])
        context = {}
        for idx, step in enumerate(steps):
            desc = step.get("desc", "")
            action = step.get("action")
            sys.stderr.write(f"[execute_plan] 开始步骤{idx+1}: {desc}, action={action}\n")
            # 通知开始
            yield {"step": idx+1, "desc": desc, "status": "start"}
            if action and "agent" in action:
                agent = action["agent"]
                params = action.get("params", {})
                params["context"] = context  # 传递上下文
                sys.stderr.write(f"[execute_plan] 调用handoff: agent={agent}, params={params}\n")
                # yield处理中
                yield {"step": idx+1, "desc": desc, "status": "running", "msg": f"正在调用{agent}"}
                try:
                    result = await mcp_manager.handoff(agent, params)
                    sys.stderr.write(f"[execute_plan] handoff结果: {result}\n")
                    # 只提取核心内容，避免前端显示完整json
                    try:
                        result_json = json.loads(result)
                        msg = result_json.get("data", {}).get("content") or result_json.get("message") or str(result_json.get("status"))
                    except Exception:
                        msg = str(result)
                    context[f"step_{idx+1}_result"] = result
                    yield {"step": idx+1, "desc": desc, "status": "success", "msg": msg, "raw": result}
                except Exception as e:
                    sys.stderr.write(f"[execute_plan] handoff异常: {e}\n")
                    yield {"step": idx+1, "desc": desc, "status": "error", "msg": str(e)}
                    break  # 遇到错误可选择中断或继续
            else:
                sys.stderr.write(f"[execute_plan] 步骤{idx+1}无action，跳过\n")
                yield {"step": idx+1, "desc": desc, "status": "skip", "msg": "无action，跳过"}
        sys.stderr.write(f"[execute_plan] 所有分步执行已完成\n")
        yield {"type": "done", "msg": "所有分步执行已完成", "context": context}
    except Exception as e:
        sys.stderr.write(f"[execute_plan] 总体异常: {e}\n")
        import traceback;traceback.print_exc(file=sys.stderr)
        yield {"type": "error", "msg": f"execute_plan异常: {e}"}
