"""
Playwright浏览器代理模块 - 三层Agent架构
"""
from .controller import PlaywrightController, BrowserAgent  # 控制器和BrowserAgent #
from .browser import PlaywrightBrowser, ContentAgent  # 观察器和ContentAgent #
from .agent_controller import ControllerAgent  # 顶层调度Agent #

__all__ = [
    'PlaywrightController', 
    'PlaywrightBrowser', 
    'BrowserAgent', 
    'ContentAgent', 
    'ControllerAgent'
]  # 导出所有核心组件 # 