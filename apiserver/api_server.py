#!/usr/bin/env python3
"""
NagaAgent API服务器
提供RESTful API接口访问NagaAgent功能
"""

import asyncio
import json
import sys
import traceback
import re
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import aiohttp

# 导入NagaAgent核心模块
from conversation_core import NagaConversation
from config import config
from ui.response_utils import extract_message  # 导入消息提取工具

# 全局NagaAgent实例
naga_agent: Optional[NagaConversation] = None

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # 移除断开的连接
                self.active_connections.remove(connection)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global naga_agent
    try:
        print("🚀 正在初始化NagaAgent...")
        naga_agent = NagaConversation()  # 第四次初始化：API服务器启动时创建
        print("✅ NagaAgent初始化完成")
        yield
    except Exception as e:
        print(f"❌ NagaAgent初始化失败: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("🔄 正在清理资源...")
        if naga_agent and hasattr(naga_agent, 'mcp'):
            try:
                await naga_agent.mcp.cleanup()
            except Exception as e:
                print(f"⚠️ 清理MCP资源时出错: {e}")

# 创建FastAPI应用
app = FastAPI(
    title="NagaAgent API",
    description="智能对话助手API服务",
    version="3.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class ChatRequest(BaseModel):
    message: str
    stream: bool = False
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
    status: str = "success"

class MCPRequest(BaseModel):
    service_name: str
    task: Dict
    session_id: Optional[str] = None

class SystemInfoResponse(BaseModel):
    version: str
    status: str
    available_services: List[str]
    api_key_configured: bool

# WebSocket路由
@app.websocket("/ws/mcplog")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点 - 提供MCP实时通知"""
    await manager.connect(websocket)
    try:
        # 发送连接确认
        await manager.send_personal_message(
            json.dumps({
                "type": "connection_ack",
                "message": "WebSocket连接成功"
            }, ensure_ascii=False),
            websocket
        )
        
        # 保持连接
        while True:
            try:
                # 等待客户端消息（心跳检测）
                data = await websocket.receive_text()
                # 可以处理客户端发送的消息
                await manager.send_personal_message(
                    json.dumps({
                        "type": "pong",
                        "message": "收到心跳"
                    }, ensure_ascii=False),
                    websocket
                )
            except WebSocketDisconnect:
                manager.disconnect(websocket)
                break
    except Exception as e:
        print(f"WebSocket错误: {e}")
        manager.disconnect(websocket)

# API路由
@app.get("/", response_model=Dict[str, str])
async def root():
    """API根路径"""
    return {
        "name": "NagaAgent API",
        "version": "3.0",
        "status": "running",
        "docs": "/docs",
        "websocket": "/ws/mcplog"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "agent_ready": naga_agent is not None,
        "timestamp": str(asyncio.get_event_loop().time())
    }

@app.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info():
    """获取系统信息"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    return SystemInfoResponse(
        version="3.0",
        status="running",
        available_services=naga_agent.mcp.list_mcps(),
        api_key_configured=bool(config.api.api_key and config.api.api_key != "sk-placeholder-key-not-set")
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """普通对话接口"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    
    try:
        # 构建消息
        messages = [
            {"role": "user", "content": request.message}
        ]
        
        # 定义LLM调用函数
        async def call_llm(messages: List[Dict]) -> Dict:
            """调用LLM API"""
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{config.api.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.api.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": config.api.model,
                        "messages": messages,
                        "temperature": config.api.temperature,
                        "max_tokens": config.api.max_tokens,
                        "stream": False
                    }
                ) as resp:
                    if resp.status != 200:
                        raise HTTPException(status_code=resp.status, detail="LLM API调用失败")
                    
                    data = await resp.json()
                    return {
                        'content': data['choices'][0]['message']['content'],
                        'status': 'success'
                    }
        
        # 处理工具调用循环
        result = await tool_call_loop(messages, naga_agent.mcp, call_llm, is_streaming=False)
        
        # 提取最终响应
        response_text = result['content']
        
        return ChatResponse(
            response=extract_message(response_text) if response_text else response_text,
            session_id=request.session_id,
            status="success"
        )
    except Exception as e:
        print(f"对话处理错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话接口"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            # 构建消息
            messages = [
                {"role": "user", "content": request.message}
            ]
            
            # 定义LLM调用函数
            async def call_llm(messages: List[Dict]) -> Dict:
                """调用LLM API"""
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{config.api.base_url}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {config.api.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": config.api.model,
                            "messages": messages,
                            "temperature": config.api.temperature,
                            "max_tokens": config.api.max_tokens,
                            "stream": False
                        }
                    ) as resp:
                        if resp.status != 200:
                            raise HTTPException(status_code=resp.status, detail="LLM API调用失败")
                        
                        data = await resp.json()
                        return {
                            'content': data['choices'][0]['message']['content'],
                            'status': 'success'
                        }
            
            # 处理工具调用循环
            result = await tool_call_loop(messages, naga_agent.mcp, call_llm, is_streaming=True)
            
            # 流式输出最终结果
            final_content = result['content']
            for line in final_content.splitlines():
                if line.strip():
                    yield f"data: {line}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"流式对话处理错误: {e}")
            traceback.print_exc()
            yield f"data: 错误: {str(e)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.post("/mcp/handoff")
async def mcp_handoff(request: MCPRequest):
    """MCP服务调用接口"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    try:
        # 直接调用MCP handoff
        result = await naga_agent.mcp.handoff(
            service_name=request.service_name,
            task=request.task
        )
        
        return {
            "status": "success",
            "result": result,
            "session_id": request.session_id
        }
    except Exception as e:
        print(f"MCP handoff错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"handoff失败: {str(e)}")

@app.get("/mcp/services")
async def get_mcp_services():
    """获取可用的MCP服务列表"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    try:
        services = naga_agent.mcp.list_mcps()
        return {
            "status": "success",
            "services": services,
            "count": len(services)
        }
    except Exception as e:
        print(f"获取MCP服务列表错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取服务列表失败: {str(e)}")

@app.post("/system/devmode")
async def toggle_devmode():
    """切换开发者模式"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    try:
        naga_agent.dev_mode = not naga_agent.dev_mode
        return {
            "status": "success",
            "dev_mode": naga_agent.dev_mode,
            "message": f"开发者模式已{'启用' if naga_agent.dev_mode else '禁用'}"
        }
    except Exception as e:
        print(f"切换开发者模式错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"切换开发者模式失败: {str(e)}")

@app.get("/memory/stats")
async def get_memory_stats():
    """获取记忆统计信息"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    try:
        # 这里可以添加记忆统计逻辑
        return {
            "status": "success",
            "memory_manager_ready": naga_agent.memory is not None,
            "message": "记忆管理器已就绪"
        }
    except Exception as e:
        print(f"获取记忆统计错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取记忆统计失败: {str(e)}")

# 工具调用循环相关函数

def parse_tool_calls(content: str) -> list:
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

async def execute_tool_calls(tool_calls: list, mcp_manager) -> str:
    """执行工具调用"""
    results = []
    for tool_call in tool_calls:
        try:
            result = await mcp_manager.handoff(
                service_name=tool_call['name'],
                task=tool_call['args']
            )
            results.append(f"来自工具 \"{tool_call['name']}\" 的结果:\n{result}")
        except Exception as e:
            error_result = f"执行工具 {tool_call['name']} 时发生错误：{str(e)}"
            results.append(error_result)
    return "\n\n---\n\n".join(results)

async def tool_call_loop(messages: list, mcp_manager, llm_caller, is_streaming: bool = False) -> dict:
    """工具调用循环主流程"""
    recursion_depth = 0
    max_recursion = config.handoff.max_loop_stream if is_streaming else config.handoff.max_loop_non_stream
    current_messages = messages.copy()
    current_ai_content = ''
    while recursion_depth < max_recursion:
        try:
            llm_response = await llm_caller(current_messages)
            current_ai_content = llm_response.get('content', '')
            tool_calls = parse_tool_calls(current_ai_content)
            if not tool_calls:
                break
            tool_results = await execute_tool_calls(tool_calls, mcp_manager)
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

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NagaAgent API服务器")
    parser.add_argument("--host", default=config.api_server.host, help="服务器主机地址")
    parser.add_argument("--port", type=int, default=config.api_server.port, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="开启自动重载")
    
    args = parser.parse_args()
    
    print(f"🚀 启动NagaAgent API服务器...")
    print(f"📍 地址: http://{args.host}:{args.port}")
    print(f"📚 文档: http://{args.host}:{args.port}/docs")
    print(f"🔄 自动重载: {'开启' if args.reload else '关闭'}")
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    ) 
