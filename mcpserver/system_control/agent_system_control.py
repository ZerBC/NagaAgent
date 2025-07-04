from agents import Agent
from config import *  # 统一变量管理 #
import asyncio
try:
    import screen_brightness_control as sbc  # 屏幕亮度调节 #
except ImportError:
    sbc = None
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    import comtypes  # COM组件初始化 #
except ImportError:
    AudioUtilities = None

class SystemControlAgent(Agent):
    """系统控制Agent #"""
    name = "SystemControlAgent"  # Agent名称 #
    instructions = "系统控制：定时关机、亮度、音量调节"  # 角色描述 #
    def __init__(self):
        super().__init__(
            name=self.name,
            instructions=self.instructions,
            tools=[],
            model=MODEL_NAME
        )
        self._shutdown_pending = False  # 关机待确认状态 #
        self._shutdown_time = 0  # 待确认的关机时间 #

    async def handle_handoff(self, data: dict) -> str:
        action = data.get("action")
        if action == "shutdown":
            time_sec = int(data.get("time", 0))
            if self._shutdown_pending:
                confirm = data.get("confirm", "").upper()
                if confirm == "Y":
                    import os
                    os.system(f"shutdown /s /t {self._shutdown_time}")  # Windows关机 #
                    self._shutdown_pending = False
                    return f"关机确认成功，{self._shutdown_time}秒后关机"
                elif confirm == "N":
                    self._shutdown_pending = False
                    return "关机已取消"
                else:
                    return "请回复 Y 确认关机，或 N 取消关机"
            else:
                self._shutdown_pending = True
                self._shutdown_time = time_sec
                time_str = f"{time_sec}秒后" if time_sec > 0 else "立即"
                return f"确认要{time_str}关机吗？请回复 Y 确认，或 N 取消"
        elif action == "set_brightness":
            value = int(data.get("value", 50))
            if sbc:
                sbc.set_brightness(value)
                return f"亮度已设置为{value}"
            else:
                return "未安装screen_brightness_control库，无法调节亮度"
        elif action == "set_volume":
            value = int(data.get("value", 50))
            if AudioUtilities:
                try:
                    comtypes.CoInitialize()  # 初始化COM组件 #
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    volume.SetMasterVolumeLevelScalar(value/100, None)
                    return f"音量已设置为{value}"
                except Exception as e:
                    return f"音量设置失败: {e}"
                finally:
                    comtypes.CoUninitialize()  # 清理COM组件 #
            else:
                return "未安装pycaw库，无法调节音量"
        else:
            return "未知操作" 