#!/usr/bin/env python3
"""
测试WebSocket客户端 - 用于测试MCP实时通知功能
"""

import asyncio
import websockets
import json
import sys

async def test_websocket_client():
    """测试WebSocket客户端"""
    uri = "ws://127.0.0.1:8000/ws/mcplog" # 使用API服务器的WebSocket端点
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ 已连接到WebSocket服务器")
            
            # 接收消息
            async def receive_messages():
                try:
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        print(f"📨 收到消息: {json.dumps(data, ensure_ascii=False, indent=2)}")
                except websockets.exceptions.ConnectionClosed:
                    print("❌ WebSocket连接已关闭")
                except Exception as e:
                    print(f"❌ 接收消息错误: {e}")
            
            await receive_messages()
            
    except Exception as e:
        print(f"❌ 连接WebSocket服务器失败: {e}")
        print("💡 请确保API服务器正在运行: python apiserver/start_server.py")

if __name__ == "__main__":
    print("🚀 开始测试WebSocket客户端...")
    print("📡 连接到: ws://127.0.0.1:8000/ws/mcplog")
    print("💡 请确保API服务器正在运行")
    print("-" * 50)
    
    asyncio.run(test_websocket_client()) 