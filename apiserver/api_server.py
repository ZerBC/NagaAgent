#!/usr/bin/env python3
"""
NagaAgent API服务器
提供RESTful API接口访问NagaAgent功能
"""

import asyncio
import json
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 导入NagaAgent核心模块
from conversation_core import NagaConversation
from config import DEEPSEEK_API_KEY
from ui.response_utils import extract_message  # 导入消息提取工具

# 全局NagaAgent实例
naga_agent: Optional[NagaConversation] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global naga_agent
    try:
        print("🚀 正在初始化NagaAgent...")
        naga_agent = NagaConversation()
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
    version="2.3",
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

# API路由
@app.get("/", response_model=Dict[str, str])
async def root():
    """API根路径"""
    return {
        "name": "NagaAgent API",
        "version": "2.3",
        "status": "running",
        "docs": "/docs"
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
        version="2.3",
        status="running",
        available_services=naga_agent.mcp.list_mcps(),
        api_key_configured=bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "sk-placeholder-key-not-set")
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """普通对话接口"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    
    try:
        response_text = ""
        async for speaker, content in naga_agent.process(request.message):
            if speaker == "娜迦":
                # 使用extract_message提取纯文本
                raw_content = str(content)
                extracted_content = extract_message(raw_content)
                print(f"[DEBUG] 原始内容: {repr(raw_content[:100])}")
                print(f"[DEBUG] 提取内容: {repr(extracted_content[:100])}")
                response_text += extracted_content
        
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
            async for speaker, content in naga_agent.process(request.message):
                if speaker == "娜迦":
                    # 使用extract_message提取纯文本
                    extracted_content = extract_message(str(content))
                    # 使用Server-Sent Events格式
                    yield f"data: {json.dumps({'content': extracted_content, 'speaker': speaker}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            print(f"流式对话错误: {e}")
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/mcp/handoff")
async def mcp_handoff(request: MCPRequest):
    """MCP服务调用接口"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    try:
        result = await naga_agent.mcp.handoff(
            service_name=request.service_name,
            task=request.task
        )
        return {
            "result": result,
            "session_id": request.session_id,
            "status": "success"
        }
    except Exception as e:
        print(f"MCP调用错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"MCP调用失败: {str(e)}")

@app.get("/mcp/services")
async def get_mcp_services():
    """获取可用的MCP服务列表"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    try:
        services = naga_agent.mcp.get_available_services()
        return {
            "services": services,
            "status": "success"
        }
    except Exception as e:
        print(f"获取MCP服务列表错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@app.post("/system/devmode")
async def toggle_devmode():
    """切换开发者模式"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    naga_agent.dev_mode = not naga_agent.dev_mode
    return {
        "dev_mode": naga_agent.dev_mode,
        "message": f"开发者模式已{'开启' if naga_agent.dev_mode else '关闭'}",
        "status": "success"
    }

@app.get("/memory/stats")
async def get_memory_stats():
    """获取记忆系统统计信息"""
    if not naga_agent:
        raise HTTPException(status_code=503, detail="NagaAgent未初始化")
    
    try:
        stats = {
            "total_memories": len(naga_agent.memory.memories) if hasattr(naga_agent, 'memory') else 0,
            "dev_mode": naga_agent.dev_mode,
            "message_count": len(naga_agent.messages)
        }
        return {
            "stats": stats,
            "status": "success"
        }
    except Exception as e:
        print(f"获取记忆统计错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NagaAgent API服务器")
    parser.add_argument("--host", default="127.0.0.1", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
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