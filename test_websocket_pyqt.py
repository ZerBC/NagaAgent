#!/usr/bin/env python3
"""
测试PyQt WebSocket功能
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from PyQt5.QtWidgets import QApplication
from ui.pyqt_chat_window import ChatWindow

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建聊天窗口
    window = ChatWindow()
    window.show()
    
    print("🚀 PyQt聊天窗口已启动")
    print("📡 WebSocket客户端将自动连接到 ws://127.0.0.1:8000/ws/mcplog")
    print("💡 请确保API服务器正在运行 (python apiserver/start_server.py)")
    print("💡 推送消息将显示在主对话框中，带有不同颜色标识")
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 