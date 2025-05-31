# NagaAgent API服务器

这个文件夹包含NagaAgent的API服务器相关文件。

## 文件说明

- `api_server.py` - 主要的FastAPI服务器代码
- `start_server.py` - 独立启动脚本
- `__init__.py` - Python包初始化文件

## 使用方式

### 1. 通过main.py自动启动（推荐）
```bash
python main.py
```
API服务器会在系统启动时自动启动在端口8000。

### 2. 独立启动API服务器
```bash
cd apiserver
python start_server.py
```

### 3. 自定义端口启动
```bash
cd apiserver
python start_server.py --host 0.0.0.0 --port 8080
```

### 4. 开发模式（自动重载）
```bash
cd apiserver
python start_server.py --reload --log-level debug
```

## API接口

启动后可以访问：
- API文档: http://127.0.0.1:8000/docs
- 健康检查: http://127.0.0.1:8000/health
- 对话接口: http://127.0.0.1:8000/chat
- 流式对话: http://127.0.0.1:8000/chat/stream

## 代理问题

如果你使用了代理服务器，测试本地API时需要绕过代理：
```bash
NO_PROXY="127.0.0.1,localhost" curl -X GET "http://127.0.0.1:8000/health"
``` 