# mcpserver/websocket_manager.py
# MCP WebSocket管理器 - 提供实时通知功能
import asyncio
import json
import logging
import time
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger("MCPWebSocketManager")

@dataclass
class WebSocketClient:
    """WebSocket客户端信息"""
    websocket: WebSocketServerProtocol
    client_id: str
    client_type: str  # 'MCPLog', 'MCPClient', 'DistributedServer'
    connected_at: datetime
    metadata: Dict[str, Any] = None

class MCPWebSocketManager:
    """MCP WebSocket管理器 - 提供实时通知功能"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.clients: Dict[str, WebSocketClient] = {}
        self.distributed_servers: Dict[str, WebSocketClient] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.server = None
        self.mcp_manager = None
        
    def set_mcp_manager(self, mcp_manager):
        """设置MCP管理器引用"""
        self.mcp_manager = mcp_manager
        
    async def start_server(self, host: str = '127.0.0.1', port: int = 8081):
        """启动WebSocket服务器"""
        self.server = await websockets.serve(
            self.handle_connection, host, port
        )
        logger.info(f"MCP WebSocket服务器启动: ws://{host}:{port}")
        
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """处理WebSocket连接"""
        client_id = self._generate_client_id()
        client_type = self._parse_client_type(path)
        
        if not self._authenticate_client(path):
            await websocket.close(1008, "认证失败")
            return
            
        client = WebSocketClient(
            websocket=websocket,
            client_id=client_id,
            client_type=client_type,
            connected_at=datetime.now()
        )
        
        if client_type == 'DistributedServer':
            self.distributed_servers[client_id] = client
        else:
            self.clients[client_id] = client
            
        # 发送连接确认
        await self._send_to_client(client, {
            'type': 'connection_ack',
            'client_id': client_id,
            'message': f'WebSocket连接成功 ({client_type})'
        })
        
        try:
            async for message in websocket:
                await self._handle_message(client, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self._handle_disconnect(client)
            
    async def broadcast(self, data: Dict, target_type: Optional[str] = None):
        """广播消息"""
        message = json.dumps(data, ensure_ascii=False)
        
        # 选择目标客户端
        target_clients = []
        if target_type is None:
            target_clients.extend(self.clients.values())
            target_clients.extend(self.distributed_servers.values())
        else:
            if target_type == 'DistributedServer':
                target_clients.extend(self.distributed_servers.values())
            else:
                for client in self.clients.values():
                    if client.client_type == target_type:
                        target_clients.append(client)
                        
        # 发送消息
        for client in target_clients:
            try:
                await self._send_to_client(client, data)
            except Exception as e:
                logger.error(f"发送消息到客户端 {client.client_id} 失败: {e}")
                
    async def notify_mcp_event(self, event_type: str, data: Dict):
        """通知MCP事件"""
        notification = {
            'type': 'mcp_event',
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        await self.broadcast(notification, 'MCPLog')
        
    async def notify_tool_execution(self, service_name: str, tool_name: str, status: str, result: Any = None, error: str = None):
        """通知工具执行状态"""
        notification = {
            'type': 'tool_execution',
            'service_name': service_name,
            'tool_name': tool_name,
            'status': status,  # 'started', 'success', 'error'
            'timestamp': datetime.now().isoformat(),
            'result': result,
            'error': error
        }
        await self.broadcast(notification, 'MCPLog')
        
    async def notify_handoff_call(self, service_name: str, task: Dict, status: str, result: Any = None, error: str = None):
        """通知handoff调用状态"""
        notification = {
            'type': 'handoff_call',
            'service_name': service_name,
            'task': task,
            'status': status,  # 'started', 'success', 'error'
            'timestamp': datetime.now().isoformat(),
            'result': result,
            'error': error
        }
        await self.broadcast(notification, 'MCPLog')
        
    def _generate_client_id(self) -> str:
        """生成客户端ID"""
        return f"{int(time.time() * 1000)}-{hash(time.time()) % 10000}"
        
    def _parse_client_type(self, path: str) -> str:
        """解析客户端类型"""
        if '/mcplog/' in path:
            return 'MCPLog'
        elif '/distributed-server/' in path:
            return 'DistributedServer'
        else:
            return 'MCPClient'
            
    def _authenticate_client(self, path: str) -> bool:
        """认证客户端"""
        # 简单的路径认证，可以扩展为更复杂的认证机制
        return 'VCP_Key=' in path
        
    async def _send_to_client(self, client: WebSocketClient, data: Dict):
        """发送消息到客户端"""
        try:
            await client.websocket.send(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            
    async def _handle_message(self, client: WebSocketClient, message: str):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            if client.client_type == 'DistributedServer':
                await self._handle_distributed_message(client, data)
        except json.JSONDecodeError:
            logger.error(f"无效的JSON消息: {message}")
            
    async def _handle_disconnect(self, client: WebSocketClient):
        """处理客户端断开连接"""
        if client.client_type == 'DistributedServer':
            self.distributed_servers.pop(client.client_id, None)
            # 注销分布式工具
            if self.mcp_manager:
                # 这里可以添加注销分布式工具的逻辑
                pass
        else:
            self.clients.pop(client.client_id, None)
            
        logger.info(f"客户端断开连接: {client.client_id} ({client.client_type})")
        
    async def _handle_distributed_message(self, client: WebSocketClient, message: Dict):
        """处理分布式服务器消息"""
        # 这里可以添加处理分布式服务器消息的逻辑
        pass

# 全局WebSocket管理器实例
_websocket_manager_instance = None

def get_websocket_manager() -> MCPWebSocketManager:
    """获取全局WebSocket管理器实例"""
    global _websocket_manager_instance
    if _websocket_manager_instance is None:
        _websocket_manager_instance = MCPWebSocketManager(debug_mode=True)
    return _websocket_manager_instance 