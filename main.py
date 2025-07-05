import asyncio
import os
import sys
import threading
import time

from conversation_core import NagaConversation

sys.path.append(os.path.dirname(__file__))
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

# 导入配置
from config import config
from summer_memory.memory_manager import memory_manager
from ui.pyqt_chat_window import ChatWindow

n=NagaConversation()
def show_help():print('系统命令: 清屏, 查看索引, 帮助, 退出')
def show_index():print('主题分片索引已集成，无需单独索引查看')
def clear():os.system('cls' if os.name == 'nt' else 'clear')

def check_port_available(host, port):
    """检查端口是否可用"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False

def start_api_server():
    """在后台启动API服务器"""
    try:
        # 检查端口是否被占用
        if not check_port_available(config.api_server.host, config.api_server.port):
            print(f"⚠️ 端口 {config.api_server.port} 已被占用，跳过API服务器启动")
            return
            
        import uvicorn
        # 使用字符串路径而不是直接导入，确保模块重新加载
        # from apiserver.api_server import app
        
        print("🚀 正在启动夏园API服务器...")
        print(f"📍 地址: http://{config.api_server.host}:{config.api_server.port}")
        print(f"📚 文档: http://{config.api_server.host}:{config.api_server.port}/docs")
        
        # 在新线程中启动API服务器
        def run_server():
            try:
                uvicorn.run(
                    "apiserver.api_server:app",  # 使用字符串路径
                    host=config.api_server.host,
                    port=config.api_server.port,
                    log_level="error",  # 减少日志输出
                    access_log=False,
                    reload=False  # 确保不使用自动重载
                )
            except Exception as e:
                print(f"❌ API服务器启动失败: {e}")
        
        api_thread = threading.Thread(target=run_server, daemon=True)
        api_thread.start()
        print("✅ API服务器已在后台启动")
        
        # 等待服务器启动
        time.sleep(1)
        
    except ImportError as e:
        print(f"⚠️ API服务器依赖缺失: {e}")
        print("   请运行: pip install fastapi uvicorn")
    except Exception as e:
        print(f"❌ API服务器启动异常: {e}")

with open('./ui/progress.txt','w')as f:
    f.write('0')
mm = memory_manager

print('='*30+'\n娜迦系统已启动\n'+'='*30)

# 自动启动API服务器
if config.api_server.enabled and config.api_server.auto_start:
    start_api_server()

def check_tts_port_available(port):
    """检查TTS端口是否可用"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
            return True
    except OSError:
        return False

def start_tts_server():
    """在后台启动TTS服务"""
    try:
        if not check_tts_port_available(config.tts.port):
            print(f"⚠️ 端口 {config.tts.port} 已被占用，跳过TTS服务启动")
            return
        import subprocess
        print("🚀 正在启动TTS服务...")
        print(f"📍 地址: http://127.0.0.1:{config.tts.port}")
        def run_tts():
            try:
                subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), 'voice', 'server.py')])
            except Exception as e:
                print(f"❌ TTS服务启动失败: {e}")
        tts_thread = threading.Thread(target=run_tts, daemon=True)
        tts_thread.start()
        print("✅ TTS服务已在后台启动")
        time.sleep(1)
    except Exception as e:
        print(f"❌ TTS服务启动异常: {e}")

# 自动启动TTS服务
start_tts_server()

show_help()
loop=asyncio.new_event_loop()
threading.Thread(target=loop.run_forever,daemon=True).start()

# 推迟WebSocket初始化到事件循环环境下
asyncio.run_coroutine_threadsafe(n._init_websocket(), loop)

class NagaAgentAdapter:
 def __init__(s):s.naga=NagaConversation()  # 第二次初始化：NagaAgentAdapter构造函数中创建
 async def respond_stream(s,txt):
     async for resp in s.naga.process(txt):
         yield "娜迦",resp,None,True,False

if __name__=="__main__":
 app=QApplication(sys.argv)
 icon_path = os.path.join(os.path.dirname(__file__), "ui", "window_icon.png")
 app.setWindowIcon(QIcon(icon_path))
 win=ChatWindow()
 win.setWindowTitle("NagaAgent")
 win.show()
 sys.exit(app.exec_())
