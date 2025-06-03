import json
from mcpserver.mcp_manager import MCPManager

async def execute_plan(plan_json, mcp_manager):
    """
    执行LLM返回的plan结构，自动分步handoff调用agent
    :param plan_json: LLM返回的完整json字符串或已解析dict
    :param mcp_manager: MCP管理器实例，需有handoff(agent, params)方法
    :yield: dict，每步执行的实时反馈，前端可直接消费
    """
    # 兼容字符串和dict
    if isinstance(plan_json, str):
        try:
            resp_json = json.loads(plan_json)
        except Exception as e:
            yield {"type": "error", "msg": f"plan解析失败: {e}"}
            return
    else:
        resp_json = plan_json

    if "plan" not in resp_json:
        yield {"type": "error", "msg": "未检测到plan结构，无法自动分步执行。"}
        return

    plan = resp_json["plan"]
    steps = plan.get("steps", [])
    context = {}
    for idx, step in enumerate(steps):
        desc = step.get("desc", "")
        action = step.get("action")
        # 通知开始
        yield {"step": idx+1, "desc": desc, "status": "start"}
        if action and "agent" in action:
            agent = action["agent"]
            params = action.get("params", {})
            params["context"] = context  # 传递上下文
            # yield处理中
            yield {"step": idx+1, "desc": desc, "status": "running", "msg": f"正在调用{agent}"}
            try:
                result = await mcp_manager.handoff(agent, params)
                # 只提取核心内容，避免前端显示完整json
                try:
                    result_json = json.loads(result)
                    msg = result_json.get("data", {}).get("content") or result_json.get("message") or str(result_json.get("status"))
                except Exception:
                    msg = str(result)
                context[f"step_{idx+1}_result"] = result
                yield {"step": idx+1, "desc": desc, "status": "success", "msg": msg, "raw": result}
            except Exception as e:
                yield {"step": idx+1, "desc": desc, "status": "error", "msg": str(e)}
                break  # 遇到错误可选择中断或继续
        else:
            yield {"step": idx+1, "desc": desc, "status": "skip", "msg": "无action，跳过"}
    yield {"type": "done", "msg": "所有分步执行已完成", "context": context}
