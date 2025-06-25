# MCP WebSocket 实时通知功能说明

## 概述

本项目为MCPManager添加了WebSocket实时通知功能，当MCP工具被调用时，可以实时推送执行状态和结果给客户端。该功能基于JavaScript版本的WebSocketServer.js设计，为Python版本的MCP系统提供类似的实时通知能力。

## 核心组件

### 1. WebSocket管理器 (`websocket_manager.py`)

**功能**：
- 管理WebSocket连接
- 提供消息广播功能
- 支持多种客户端类型
- 处理分布式工具调用

**主要类**：
- `WebSocketClient`: WebSocket客户端信息
- `MCPWebSocketManager`: WebSocket管理器主类

### 2. MCPManager集成

**功能**：
- 在handoff方法中添加实时通知
- 通知工具调用开始、成功、失败状态
- 与WebSocket管理器协同工作

### 3. API服务器集成

**功能**：
- 提供WebSocket端点 `/ws/mcplog`
- 支持实时通知推送
- 与现有API服务无缝集成

## 消息类型

### 连接确认
```json
{
    "type": "connection_ack",
    "message": "WebSocket连接成功",
    "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### Handoff调用通知
```json
{
    "type": "handoff_call",
    "data": {
        "service_name": "agent_coder",
        "task": {...},
        "status": "started|success|error",
        "result": "...",
        "error": "..."
    },
    "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### 工具执行通知
```json
{
    "type": "tool_execution",
    "data": {
        "service_name": "agent_coder",
        "tool_name": "generate_code",
        "status": "started|success|error",
        "result": "...",
        "error": "..."
    },
    "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### MCP事件通知
```json
{
    "type": "mcp_event",
    "data": {
        "event_type": "service_connected|service_disconnected|tool_registered",
        "service_name": "agent_coder",
        "details": {...}
    },
    "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## 使用方法

### 1. 启动API服务器

```bash
python apiserver/start_server.py
```

### 2. 连接WebSocket

**推荐使用API服务器的WebSocket端点**：

**JavaScript客户端**：
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/mcplog'); // 使用API服务器的WebSocket端点

ws.onopen = () => {
    console.log('WebSocket连接已建立');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
    
    switch(data.type) {
        case 'connection_ack':
            console.log('连接确认:', data.message);
            break;
        case 'handoff_call':
            console.log('Handoff调用:', data.data);
            break;
        case 'tool_execution':
            console.log('工具执行:', data.data);
            break;
        case 'mcp_event':
            console.log('MCP事件:', data.data);
            break;
    }
};

ws.onerror = (error) => {
    console.error('WebSocket错误:', error);
};

ws.onclose = () => {
    console.log('WebSocket连接已关闭');
};
```

**Python客户端**：
```python
import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://127.0.0.1:8000/ws/mcplog" // 使用API服务器的WebSocket端点
    
    async with websockets.connect(uri) as websocket:
        print("✅ 已连接到WebSocket服务器")
        
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

# 运行客户端
asyncio.run(websocket_client())
```

### 3. 测试WebSocket功能

使用提供的测试客户端：

```bash
python test_websocket_client.py
```

## 配置说明

### 端口配置

#### 端口分配
- **API服务器**: `8000` - 提供RESTful API和WebSocket端点 `/ws/mcplog`
- **MCP WebSocket管理器**: `8081` - 独立的WebSocket服务器（备用）

#### 推荐使用方式
建议使用API服务器的WebSocket端点：
- **地址**: `ws://127.0.0.1:8000/ws/mcplog`
- **优势**: 统一管理，无需额外端口

#### 配置说明

##### WebSocket服务器配置

在 `conversation_core.py` 中：

```python
# 初始化WebSocket管理器
asyncio.create_task(self._init_websocket())

async def _init_websocket(self):
    """初始化WebSocket管理器"""
    try:
        await self.mcp.initialize_websocket(host='127.0.0.1', port=8081) # MCP WebSocket管理器端口
        logger.info("WebSocket管理器初始化完成")
    except Exception as e:
        logger.error(f"WebSocket管理器初始化失败: {e}")
```

##### MCPManager集成配置

在 `mcp_manager.py` 中：

```python
def __init__(self):
    # ... 其他初始化代码 ...
    self.websocket_manager = get_websocket_manager() # 获取WebSocket管理器

async def initialize_websocket(self, host: str = '127.0.0.1', port: int = 8081): # MCP WebSocket管理器端口
    """初始化WebSocket管理器"""
    try:
        self.websocket_manager.set_mcp_manager(self)
        await self.websocket_manager.start_server(host, port)
        sys.stderr.write(f"WebSocket管理器已启动: ws://{host}:{port}\n")
    except Exception as e:
        sys.stderr.write(f"WebSocket管理器启动失败: {e}\n")
```

## 客户端类型支持

### 1. MCPLog客户端
- **路径**: `/ws/mcplog`
- **用途**: 接收MCP工具调用日志和状态通知
- **认证**: 无需特殊认证

### 2. MCPClient客户端
- **路径**: `/ws/mcplog`
- **用途**: 通用MCP客户端连接
- **认证**: 无需特殊认证

### 3. DistributedServer客户端
- **路径**: `/ws/mcplog`
- **用途**: 分布式服务器连接
- **认证**: 无需特殊认证

## 错误处理

### 连接错误
- WebSocket连接失败时自动重试
- 连接断开时自动清理资源
- 错误日志记录到系统日志

### 消息错误
- 无效JSON消息自动忽略
- 消息解析错误记录到日志
- 客户端异常断开自动处理

### 超时处理
- 连接超时自动断开
- 消息发送超时重试
- 长时间无响应自动清理

## 性能优化

### 1. 连接管理
- 使用连接池管理多个客户端
- 自动清理断开的连接
- 限制最大连接数

### 2. 消息广播
- 异步消息发送
- 批量消息处理
- 消息队列缓冲

### 3. 内存管理
- 及时清理无用连接
- 限制消息大小
- 定期垃圾回收

## 监控和调试

### 1. 日志记录
```python
# 启用调试模式
DEBUG = True

# 查看WebSocket日志
logger = logging.getLogger("MCPWebSocketManager")
```

### 2. 状态监控
```python
# 获取连接状态
manager = get_websocket_manager()
client_count = len(manager.clients)
print(f"当前连接数: {client_count}")
```

### 3. 消息追踪
```python
# 启用消息追踪
manager.debug_mode = True
```

## 扩展功能

### 1. 自定义消息类型
```python
# 发送自定义消息
await manager.broadcast({
    "type": "custom_event",
    "data": {"message": "自定义消息"}
})
```

### 2. 定向消息
```python
# 发送给特定类型的客户端
await manager.broadcast({
    "type": "targeted_message",
    "data": {"message": "定向消息"}
}, target_type="MCPLog")
```

### 3. 消息过滤
```python
# 根据消息类型过滤
if data.get("type") == "handoff_call":
    # 处理handoff调用消息
    pass
```

## 故障排除

### 常见问题

1. **WebSocket连接失败**
   - 检查端口是否被占用
   - 确认防火墙设置
   - 验证服务器地址

2. **消息接收异常**
   - 检查JSON格式
   - 验证消息结构
   - 查看错误日志

3. **性能问题**
   - 检查连接数量
   - 监控内存使用
   - 优化消息频率

### 调试命令

```bash
# 检查WebSocket端口
netstat -an | grep 8080

# 测试WebSocket连接
python test_websocket_client.py

# 查看日志
tail -f logs/websocket.log
```

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持基本WebSocket连接
- 实现消息广播功能
- 集成MCPManager通知

### 计划功能
- 支持SSL/TLS加密
- 添加消息压缩
- 实现消息持久化
- 支持集群部署

## PyQt界面集成

### 功能说明
PyQt主界面已集成WebSocket客户端功能，可以实时接收和显示MCP推送消息。

### 消息类型和颜色标识

| 消息类型 | 颜色 | 说明 | 示例 |
|---------|------|------|------|
| 连接状态 | 🔵 蓝色 | WebSocket连接状态 | 🔗 WebSocket连接成功 |
| Handoff调用 | 🟠 橙色 | MCP服务调用状态 | 🚀 开始执行: agent_coder |
| 工具执行 | 🟢 绿色 | 工具调用结果 | ✅ agent_coder 执行成功 |
| MCP事件 | 🟣 紫色 | MCP系统事件 | 📡 MCP事件: service_registered |
| 错误消息 | 🔴 红色 | 错误和异常 | ❌ 连接失败: Connection refused |

### 使用方法

1. **启动API服务器**：
   ```bash
   python apiserver/start_server.py
   ```

2. **启动PyQt界面**：
   ```bash
   python test_websocket_pyqt.py
   # 或者
   python main.py  # 如果main.py包含PyQt界面
   ```

3. **自动连接**：
   - PyQt界面启动时会自动连接到WebSocket服务器
   - 连接状态会显示在主对话框中
   - 所有推送消息都会实时显示，带有时间戳

### 消息显示格式

```
[14:30:25] 🔗 WebSocket连接成功
[14:30:30] 🚀 开始执行: agent_coder
[14:30:32] ✅ agent_coder 执行成功
结果: 代码已生成...
[14:30:35] 📝 日记已创建: 小明同学 (2024-01-15)
文件: /path/to/diary.txt
```

### 技术实现

- **WebSocket客户端**：`WebSocketClient`类处理连接和消息接收
- **异步线程**：`WebSocketThread`类在独立线程中运行WebSocket客户端
- **消息处理**：`on_websocket_message`方法处理不同类型的消息
- **UI更新**：使用PyQt信号槽机制在主线程中更新UI

### 配置说明

- **WebSocket地址**：`ws://127.0.0.1:8000/ws/mcplog`
- **自动重连**：连接断开时会自动尝试重连
- **线程安全**：使用信号槽机制确保UI更新的线程安全

### 故障排除

1. **连接失败**：
   - 确保API服务器正在运行
   - 检查端口8000是否被占用
   - 查看控制台错误信息

2. **消息不显示**：
   - 检查WebSocket连接状态
   - 确认MCP服务正在发送推送
   - 查看PyQt控制台输出

3. **界面卡顿**：
   - WebSocket处理在独立线程中，不会影响主界面
   - 如果仍有问题，检查消息处理逻辑
