from playwright.async_api import Browser, Page, Playwright, async_playwright
from agents import Agent, AsyncComputer, Button, ComputerTool, Environment, ModelSettings, Runner
from config import PLAYWRIGHT_HEADLESS
import base64,asyncio,sys,re,json,time
from typing import Literal, Union, Optional, Any, Dict, List, Tuple
from dataclasses import dataclass, asdict
from .message_filter import filter_messages
from .playwright_search import search_web, SearchEngine
from .controller import PlaywrightController  # 控制器 #
from .browser import PlaywrightBrowser  # 浏览器观察器 #

print=lambda *a,**k:sys.stderr.write('[print] '+(' '.join(map(str,a)))+'\n')

# 键盘映射表
CUA_KEY_TO_PLAYWRIGHT_KEY = {
    "/": "Divide",
    "\\": "Backslash", 
    "alt": "Alt",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight", 
    "arrowup": "ArrowUp",
    "backspace": "Backspace",
    "capslock": "CapsLock",
    "cmd": "Meta",
    "ctrl": "Control",
    "delete": "Delete",
    "end": "End",
    "enter": "Enter",
    "esc": "Escape",
    "home": "Home",
    "insert": "Insert",
    "option": "Alt",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "shift": "Shift",
    "space": " ",
    "super": "Meta",
    "tab": "Tab",
    "win": "Meta",
}

@dataclass
class BrowserContext:
    """浏览器上下文"""
    url: str = ""
    page_title: str = ""
    page_content: str = ""
    history: List[Dict] = None
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
            
    def update(self, url: str, title: str = "", content: str = ""):
        self.url = url
        self.page_title = title
        self.page_content = content
        self.history.append({
            "url": url,
            "title": title,
            "timestamp": time.time()
        })
        
    def to_dict(self) -> dict:
        return asdict(self)

class LocalPlaywrightComputer(AsyncComputer):
    """本地Playwright浏览器实现（支持实例复用）"""
    _global_playwright = None  # 全局playwright实例
    _global_browser = None     # 全局browser实例
    _global_page = None       # 全局page实例
    _global_context = None    # 全局上下文

    def __init__(self):
        self.context = BrowserContext() # 独立上下文
        # 复用全局实例
        if LocalPlaywrightComputer._global_playwright and LocalPlaywrightComputer._global_browser and LocalPlaywrightComputer._global_page:
            self._playwright = LocalPlaywrightComputer._global_playwright
            self._browser = LocalPlaywrightComputer._global_browser
            self._page = LocalPlaywrightComputer._global_page
        else:
            self._playwright = None
            self._browser = None
            self._page = None

    @staticmethod
    async def is_browser_alive():
        browser = LocalPlaywrightComputer._global_browser
        try:
            if browser is None:
                return False
            # 尝试获取浏览器的所有页面，如果报错说明已关闭
            contexts = browser.contexts
            # 额外检查：尝试获取浏览器版本信息
            version = browser.version
            return True
        except Exception as e:
            # 浏览器已关闭或无效，清理全局实例
            LocalPlaywrightComputer._global_browser = None
            LocalPlaywrightComputer._global_page = None
            return False

    async def _get_browser_and_page(self) -> Tuple[Browser, Page]:
        width, height = self.dimensions
        launch_args = [
            f"--window-size={width},{height}",
            "--disable-gpu",
            "--no-sandbox"
        ]
        
        # 检查浏览器是否活着，如果不存在或已关闭则重新初始化
        if not await LocalPlaywrightComputer.is_browser_alive():
            # 清理旧的全局实例
            if LocalPlaywrightComputer._global_browser:
                try:
                    await LocalPlaywrightComputer._global_browser.close()
                except Exception:
                    pass
                LocalPlaywrightComputer._global_browser = None
            
            if LocalPlaywrightComputer._global_playwright:
                try:
                    await LocalPlaywrightComputer._global_playwright.stop()
                except Exception:
                    pass
                LocalPlaywrightComputer._global_playwright = None
            
            # 重新启动
            try:
                LocalPlaywrightComputer._global_playwright = await async_playwright().start()
                LocalPlaywrightComputer._global_browser = await LocalPlaywrightComputer._global_playwright.chromium.launch(
                    headless=PLAYWRIGHT_HEADLESS,
                    args=launch_args
                )
                # 验证浏览器实例是否有效
                if not LocalPlaywrightComputer._global_browser:
                    raise Exception("浏览器启动失败")
                # 测试浏览器连接
                await LocalPlaywrightComputer._global_browser.new_context()
            except Exception as e:
                # 清理失败的实例
                LocalPlaywrightComputer._global_browser = None
                LocalPlaywrightComputer._global_playwright = None
                raise Exception(f"浏览器初始化失败: {e}")
        
        # 确保全局实例存在
        if not LocalPlaywrightComputer._global_browser:
            raise Exception("浏览器实例未正确初始化")
        
        # 每次都新建分页
        try:
            page = await LocalPlaywrightComputer._global_browser.new_page()
            await page.set_viewport_size({"width": width, "height": height})
            return LocalPlaywrightComputer._global_browser, page
        except Exception as e:
            # 如果new_page失败，可能是浏览器实例已损坏，重新初始化
            LocalPlaywrightComputer._global_browser = None
            LocalPlaywrightComputer._global_playwright = None
            raise Exception(f"创建新页面失败，需要重新初始化浏览器: {e}")

    async def __aenter__(self):
        """异步上下文管理器入口，支持实例复用"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._browser, self._page = await self._get_browser_and_page()
                self._playwright = LocalPlaywrightComputer._global_playwright
                return self
            except Exception as e:
                sys.stderr.write(f'浏览器实例初始化失败 (尝试 {attempt + 1}/{max_retries}): {e}\n')
                if attempt == max_retries - 1:
                    # 最后一次尝试失败，清理全局实例并抛出异常
                    LocalPlaywrightComputer._global_browser = None
                    LocalPlaywrightComputer._global_playwright = None
                    raise Exception(f"浏览器初始化失败，已重试{max_retries}次: {e}")
                # 等待一段时间后重试
                await asyncio.sleep(1)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出，异常兜底防止资源泄漏"""
        try:
            # 不主动关闭全局实例，实现长连接复用
            pass
        except Exception as e:
            sys.stderr.write(f'关闭浏览器资源异常: {e}\n')
        # 兜底：如遇kill信号等，尝试关闭
        try:
            if exc_type is not None:
                if self._page:
                    await self._page.close()
                if self._browser:
                    await self._browser.close()
                if self._playwright:
                    await self._playwright.stop()
        except Exception as e:
            sys.stderr.write(f'异常关闭资源失败: {e}\n')

    @property
    def playwright(self) -> Playwright:
        assert self._playwright is not None
        return self._playwright

    @property
    def browser(self) -> Browser:
        assert self._browser is not None
        return self._browser

    @property
    def page(self) -> Page:
        assert self._page is not None
        return self._page

    @property
    def environment(self) -> Environment:
        return "browser"

    @property
    def dimensions(self) -> Tuple[int, int]:
        return (1024, 768)

    async def screenshot(self) -> str:
        """截图"""
        png_bytes = await self.page.screenshot(full_page=False)
        return base64.b64encode(png_bytes).decode("utf-8")

    async def click(self, x: int, y: int, button: Button = "left") -> None:
        """点击"""
        playwright_button: Literal["left", "middle", "right"] = "left"
        if button in ("left", "right", "middle"):
            playwright_button = button # type: ignore
        await self.page.mouse.click(x, y, button=playwright_button)

    async def double_click(self, x: int, y: int) -> None:
        """双击"""
        await self.page.mouse.dblclick(x, y)

    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """滚动"""
        await self.page.mouse.move(x, y)
        await self.page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")

    async def type(self, text: str) -> None:
        """输入文本"""
        await self.page.keyboard.type(text)

    async def wait(self) -> None:
        """等待"""
        await asyncio.sleep(1)

    async def move(self, x: int, y: int) -> None:
        """移动鼠标"""
        await self.page.mouse.move(x, y)

    async def keypress(self, keys: List[str]) -> None:
        """按键"""
        mapped_keys = [CUA_KEY_TO_PLAYWRIGHT_KEY.get(key.lower(), key) for key in keys]
        for key in mapped_keys:
            await self.page.keyboard.down(key)
        for key in reversed(mapped_keys):
            await self.page.keyboard.up(key)

    async def drag(self, path: List[Tuple[int, int]]) -> None:
        """拖拽"""
        if not path:
            return
        await self.page.mouse.move(path[0][0], path[0][1])
        await self.page.mouse.down()
        for px, py in path[1:]:
            await self.page.mouse.move(px, py)
        await self.page.mouse.up()

    async def open_url(self, url: str, timeout: int = 30000, wait_until: str = 'domcontentloaded') -> str:
        """打开URL并返回状态"""
        try:
            sys.stderr.write(f'正在打开URL: {url}\n')
            
            # 设置页面超时
            self.page.set_default_timeout(timeout)
            
            # 尝试导航到URL
            try:
                await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            except Exception as nav_error:
                # 如果网络空闲超时，尝试只等待DOM加载完成
                if 'networkidle' in str(nav_error) and wait_until == 'networkidle':
                    sys.stderr.write(f'网络空闲超时，尝试DOM加载完成模式: {nav_error}\n')
                    try:
                        await self.page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                    except Exception as dom_error:
                        sys.stderr.write(f'DOM加载也失败: {dom_error}\n')
                        raise dom_error
                else:
                    raise nav_error
            
            # 获取页面信息
            try:
                title = await self.page.title()
            except Exception:
                title = "无法获取标题"
            
            try:
                content = await self.page.content()
            except Exception:
                content = ""
            
            self.context.update(url=url, title=title, content=content)
            return 'ok'
        except Exception as e:
            sys.stderr.write(f'打开URL失败: {e}\n')
            return str(e)

    async def type_by_selector(self, selector: str, text: str) -> str:
        """按CSS选择器输入文本"""
        try:
            await self.page.fill(selector, text)
            return 'ok'
        except Exception as e:
            sys.stderr.write(f'按selector输入失败: {e}\n')
            return str(e)

    async def click_by_selector(self, selector: str) -> str:
        """按CSS选择器点击元素"""
        try:
            await self.page.click(selector)
            return 'ok'
        except Exception as e:
            sys.stderr.write(f'按selector点击失败: {e}\n')
            return str(e)

class PlaywrightAgent(Agent):
    """Playwright浏览器代理"""
    def __init__(self):
        super().__init__(
            name="Playwright Browser Agent",
            instructions="You are a helpful browser automation agent.",
            tools=[ComputerTool(LocalPlaywrightComputer())],
            model="computer-use-preview",
            model_settings=ModelSettings(truncation="auto")
        )
        sys.stderr.write('✅ PlaywrightAgent初始化完成\n')

    async def handle_handoff(self, data: dict) -> str:
        """智能处理handoff请求，控制与观察分离 #"""
        try:
            data_json = json.dumps(data, ensure_ascii=False)  #
            sys.stderr.write(f'收到handoff请求数据: {data_json}\n'.encode('utf-8', errors='replace').decode('utf-8'))  #
            if not isinstance(data, dict):
                raise ValueError(f"无效的数据格式: {type(data)}")  #
            action = data.get("action", "")  #
            url = data.get("url")  #
            query = data.get("query")  #
            selector = data.get("selector")  #
            text = data.get("text")  #
            timeout = int(data.get("timeout", 30000))  #
            wait_until = data.get("wait_until", "domcontentloaded")  #
            # 控制类action #
            if action in ["open", "open_browser", "type", "click"]:
                async with LocalPlaywrightComputer() as computer:
                    controller = PlaywrightController(computer.page)  #
                    if action in ["open", "open_browser"] and url:
                        if not url.startswith(('http://', 'https://')):
                            url = 'https://' + url  #
                        result = await controller.open_url(url, timeout=timeout, wait_until=wait_until)  #
                        response = {
                            'status': 'ok' if result == 'ok' else 'error',
                            'message': result if result != 'ok' else '打开成功',
                            'query': query if query else url,
                            'data': {
                                'url': url,
                                'page_title': await computer.page.title(),
                                'page_content_length': len(await computer.page.content())
                            }
                        }
                        return json.dumps(response, ensure_ascii=False)  #
                if action == "type" and selector and text is not None:
                    result = await controller.type(selector, text)  #
                    response = {
                        'status': 'ok' if result == 'ok' else 'error',
                        'message': result if result == 'ok' else f'输入失败: {result}',
                        'query': query,
                        'data': {
                            'selector': selector,
                            'text': text
                        }
                    }
                    return json.dumps(response, ensure_ascii=False)  #
                if action == "click" and selector:
                    result = await controller.click(selector)  #
                    response = {
                        'status': 'ok' if result == 'ok' else 'error',
                        'message': result if result == 'ok' else f'点击失败: {result}',
                        'query': query,
                        'data': {
                            'selector': selector
                        }
                    }
                    return json.dumps(response, ensure_ascii=False)  #
            # 观察类action #
            if action in ["get_content", "get_title", "get_screenshot"]:
                async with LocalPlaywrightComputer() as computer:
                    browser = PlaywrightBrowser(computer.page)  #
                    if action == "get_content":
                        content = await browser.get_content()  #
                        return json.dumps({'status': 'ok', 'result': content}, ensure_ascii=False)  #
                    if action == "get_title":
                        title = await browser.get_title()  #
                        return json.dumps({'status': 'ok', 'result': title}, ensure_ascii=False)  #
                    if action == "get_screenshot":
                        screenshot = await browser.get_screenshot()  #
                        return json.dumps({'status': 'ok', 'result': base64.b64encode(screenshot).decode('utf-8')}, ensure_ascii=False)  #
            # 兼容原有url/query/搜索逻辑 #
            if url:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url  #
                async with LocalPlaywrightComputer() as computer:
                    controller = PlaywrightController(computer.page)  #
                    result = await controller.open_url(url, timeout=timeout, wait_until=wait_until)  #
                    response = {
                        'status': 'ok' if result == 'ok' else 'error',
                        'message': result if result != 'ok' else '打开成功',
                        'query': query if query else url,
                        'data': {
                            'url': url,
                            'page_title': await computer.page.title(),
                            'page_content_length': len(await computer.page.content())
                        }
                    }
                return json.dumps(response, ensure_ascii=False)  #
            if query:
                url2 = extract_url(query)  #
                if url2:
                    if not url2.startswith(('http://', 'https://')):
                        url2 = 'https://' + url2  #
                    async with LocalPlaywrightComputer() as computer:
                        controller = PlaywrightController(computer.page)  #
                        result = await controller.open_url(url2, timeout=timeout, wait_until=wait_until)  #
                        response = {
                            'status': 'ok' if result == 'ok' else 'error',
                            'message': result if result != 'ok' else '打开成功',
                            'query': query,
                            'data': {
                                'url': url2,
                                'page_title': await computer.page.title(),
                                'page_content_length': len(await computer.page.content())
                            }
                        }
                    return json.dumps(response, ensure_ascii=False)  #
                engine = data.get("engine", "")  #
                if not engine:
                    engine = "google"  #
                search_result = await search_web(query, engine)  #
                if search_result.get("status") == "ok" and search_result.get("data", {}).get("results"):
                    first_result = search_result["data"]["results"][0]  #
                    url3 = first_result.get("url")  #
                    if url3:
                        async with LocalPlaywrightComputer() as computer:
                            controller = PlaywrightController(computer.page)  #
                            result = await controller.open_url(url3, timeout=timeout, wait_until=wait_until)  #
                            if result == 'ok':
                                search_result["data"]["opened_url"] = url3  #
                                search_result["data"]["page_title"] = await computer.page.title()  #
                                search_result["data"]["page_content_length"] = len(await computer.page.content())  #
                search_result["query"] = query  #
                return json.dumps(search_result, ensure_ascii=False)  #
            return json.dumps({
                'status': 'error',
                'message': '未提供有效的url、query或action',
                'data': {}
            }, ensure_ascii=False)  #
        except Exception as e:
            sys.stderr.write(f'handle_handoff异常: {e}\n'.encode('utf-8', errors='replace').decode('utf-8'))  #
            import traceback;traceback.print_exc(file=sys.stderr)  #
            return json.dumps({
                'status': 'error',
                'message': str(e),
                'data': {}
            }, ensure_ascii=False)  #

def extract_url(text: str) -> str:
    """从文本中提取URL，仅正则判断，不做常见网站名称映射"""
    if not text:
        return ""
    # 直接URL模式
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    urls = re.findall(url_pattern, text)
    if urls:
        url = urls[0]
        if not url.startswith('http'):
            url = 'https://' + url
        return url
    return ""

if __name__=="__main__":
    sys.stderr.write('playwright.py 进入MCP主循环\n')
    import asyncio
    from agents.mcp import MCPServerStdio
    
    async def _main():
        # 创建Playwright代理
        agent = PlaywrightAgent()
        # 创建MCP服务器
        server = MCPServerStdio(
            name="playwright",
            agent=agent
        )
        await server.serve()
        
    asyncio.run(_main())
