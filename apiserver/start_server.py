#!/usr/bin/env python3
"""
独立启动NagaAgent API服务器
可以独立于主程序运行API服务
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import argparse
    import uvicorn
    from api_server import app
    
    parser = argparse.ArgumentParser(description="独立启动NagaAgent API服务器")
    parser.add_argument("--host", default="127.0.0.1", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="开启自动重载")
    parser.add_argument("--log-level", default="info", help="日志级别")
    
    args = parser.parse_args()
    
    print(f"🚀 独立启动NagaAgent API服务器...")
    print(f"📍 地址: http://{args.host}:{args.port}")
    print(f"📚 文档: http://{args.host}:{args.port}/docs")
    print(f"🔄 自动重载: {'开启' if args.reload else '关闭'}")
    print(f"📝 日志级别: {args.log_level}")
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        app_dir=str(Path(__file__).parent)
    ) 