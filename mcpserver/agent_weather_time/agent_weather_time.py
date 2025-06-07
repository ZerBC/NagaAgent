# agent_weather_time.py # 天气和时间查询Agent
import json # 导入json模块
import aiohttp # 异步HTTP请求
from agents import Agent, ComputerTool # 导入Agent和工具基类
from config import DEBUG # 导入全局DEBUG配置
import requests # 用于同步获取IP和城市
import re # 用于正则解析
from datetime import datetime, timedelta # 用于日期处理
IPIP_URL = "https://myip.ipip.net/" # 统一配置

class WeatherTimeTool:
    """天气和时间工具类"""
    def __init__(self):
        self._ip_info = None # 缓存IP信息
        self._local_ip = None # 本地IP
        self._local_city = None # 本地城市
        self._get_local_ip_and_city() # 初始化时获取本地IP和城市
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._preload_ip_info())
            else:
                self._ip_info = loop.run_until_complete(self.get_ip_info())
        except Exception:
            self._ip_info = None

    def _get_local_ip_and_city(self):
        """同步获取本地IP和城市"""
        try:
            resp = requests.get(IPIP_URL, timeout=5)
            resp.encoding = 'utf-8'
            html = resp.text
            match = re.search(r"当前 IP：([\d\.]+)\s+来自于：(.+?)\s{2,}", html)
            if match:
                self._local_ip = match.group(1)
                self._local_city = match.group(2)
            else:
                self._local_ip = None
                self._local_city = None
        except Exception as e:
            self._local_ip = None
            self._local_city = None

    async def _preload_ip_info(self):
        self._ip_info = await self.get_ip_info()

    async def get_ip_info(self):
        """获取用户IP和城市信息"""
        url = 'http://ip-api.com/json/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return data # 返回完整IP信息

    async def get_weather(self, city):
        """获取指定城市天气"""
        url = f'https://wttr.in/{city}?format=j1'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                return data

    async def get_time(self, timezone):
        """获取指定时区当前时间"""
        from datetime import datetime
        import pytz
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return now.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    def parse_weather_query(self, query, city, weather_data):
        """
        根据用户query和天气数据，返回对应的天气信息
        支持当前、明天、后天、未来N天、指定日期、日出日落、最高温、最低温、风力、湿度等
        """
        # 1. 当前天气
        if not query or re.search(r'(现在|当前|实时|today|current)', query):
            current = weather_data['current_condition'][0]
            desc = current['weatherDesc'][0]['value']
            temp = current['temp_C']
            feels = current['FeelsLikeC']
            wind = current['windspeedKmph']
            return f'{city}当前天气：{desc}，温度{temp}℃，体感{feels}℃，风速{wind}km/h'

        # 2. 明天天气
        if re.search(r'(明天|tomorrow)', query):
            if len(weather_data['weather']) > 1:
                tomorrow = weather_data['weather'][1]
                desc = tomorrow['hourly'][4]['weatherDesc'][0]['value']  # 取中午12点
                temp = tomorrow['avgtempC']
                return f'{city}明天天气：{desc}，平均温度{temp}℃'
            else:
                return f'{city}暂无明天天气数据'

        # 3. 后天天气
        if re.search(r'(后天|day after tomorrow)', query):
            if len(weather_data['weather']) > 2:
                after = weather_data['weather'][2]
                desc = after['hourly'][4]['weatherDesc'][0]['value']
                temp = after['avgtempC']
                return f'{city}后天天气：{desc}，平均温度{temp}℃'
            else:
                return f'{city}暂无后天天气数据'

        # 4. 未来N天
        match = re.search(r'未来(\d+)天', query)
        if match:
            n = int(match.group(1))
            n = min(n, len(weather_data['weather']))
            result = [f'{city}未来{n}天天气：']
            for i in range(n):
                day = weather_data['weather'][i]
                date = day['date']
                desc = day['hourly'][4]['weatherDesc'][0]['value']
                temp = day['avgtempC']
                result.append(f'{date}：{desc}，平均温度{temp}℃')
            return '\n'.join(result)

        # 5. 某天的天气（如"6月10日"）
        date_match = re.search(r'(\d{1,2})月(\d{1,2})日', query)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            for d in weather_data['weather']:
                d_date = datetime.strptime(d['date'], '%Y-%m-%d')
                if d_date.month == month and d_date.day == day:
                    desc = d['hourly'][4]['weatherDesc'][0]['value']
                    temp = d['avgtempC']
                    return f'{city}{month}月{day}日天气：{desc}，平均温度{temp}℃'

        # 6. 日出日落
        if re.search(r'(日出|sunrise)', query):
            today = weather_data['weather'][0]
            sunrise = today['astronomy'][0]['sunrise']
            return f'{city}今天日出时间：{sunrise}'
        if re.search(r'(日落|sunset)', query):
            today = weather_data['weather'][0]
            sunset = today['astronomy'][0]['sunset']
            return f'{city}今天日落时间：{sunset}'

        # 7. 最高温/最低温
        if re.search(r'(最高温|high)', query):
            today = weather_data['weather'][0]
            return f'{city}今天最高温：{today.get("maxtempC", "-")}℃'
        if re.search(r'(最低温|low)', query):
            today = weather_data['weather'][0]
            return f'{city}今天最低温：{today.get("mintempC", "-")}℃'

        # 8. 风力/湿度等专项
        if re.search(r'(风|wind)', query):
            current = weather_data['current_condition'][0]
            wind = current['windspeedKmph']
            return f'{city}当前风速：{wind}km/h'
        if re.search(r'(湿度|humidity)', query):
            current = weather_data['current_condition'][0]
            humidity = current['humidity']
            return f'{city}当前湿度：{humidity}%'

        # 兜底：返回当前天气
        current = weather_data['current_condition'][0]
        desc = current['weatherDesc'][0]['value']
        temp = current['temp_C']
        feels = current['FeelsLikeC']
        wind = current['windspeedKmph']
        return f'{city}当前天气：{desc}，温度{temp}℃，体感{feels}℃，风速{wind}km/h'

    async def handle(self, action=None, ip=None, city=None, query=None, format=None, **kwargs):
        """统一处理入口，兼容query/format等参数"""
        # 如果未指定城市，优先用本地预加载城市
        if not city:
            city = getattr(self, '_local_city', '') or ''
        if not action:
            if query:
                if 'time' in query or '时间' in query:
                    action = 'time'
                elif 'weather' in query or '天气' in query:
                    action = 'weather'
            elif format:
                if 'time' in format or '时间' in format:
                    action = 'time'
                elif 'weather' in format or '天气' in format:
                    action = 'weather'
        # 1. 获取IP和城市（优先用缓存）
        ip_info = self._ip_info or (await self.get_ip_info()) if not (ip and city) else {}
        if not city:
            city = ip_info.get('city', '')
        if not ip:
            ip = ip_info.get('query', '')
        timezone = ip_info.get('timezone', 'Asia/Shanghai')
        # 2. 根据action处理
        if action in ['weather', 'get_weather', 'current_weather']:
            if not city:
                return {'status': 'error', 'message': '未能识别城市'}
            weather = await self.get_weather(city)
            try:
                msg = self.parse_weather_query(query or '', city, weather) # 自动解析意图
                return {
                    'status': 'ok',
                    'message': msg,
                    'data': weather
                }
            except Exception:
                return {'status': 'error', 'message': '天气API返回异常', 'data': weather}
        elif action in ['time', 'get_time', 'current_time']:
            t = await self.get_time(timezone)
            if t:
                return {'status': 'ok', 'message': f'{city}当前时间：{t}', 'data': {'city': city, 'timezone': timezone, 'time': t}}
            else:
                return {'status': 'error', 'message': '时区解析失败', 'data': {'city': city, 'timezone': timezone}}
        else:
            return {'status': 'error', 'message': f'未知操作: {action}'}

class WeatherTimeAgent(Agent):
    """天气和时间Agent"""
    def __init__(self):
        self._tool = WeatherTimeTool() # 预加载
        super().__init__(
            name="WeatherTime Agent", # Agent名称
            instructions="天气和时间智能体", # 角色描述
            tools=[ComputerTool(self._tool)], # 注入工具
            model="weather-time-use-preview" # 使用统一模型
        )
        import sys
        ip_info = getattr(self._tool, '_ip_info', None)
        ip_str = ip_info.get('query') if ip_info else '未获取到IP'
        city_str = getattr(self._tool, '_local_city', '未知城市') # 获取本地城市
        sys.stderr.write(f'WeatherTimeAgent初始化完成，登陆地址：{city_str}\n')

    async def handle_handoff(self, task: dict) -> str:
        try:
            # 兼容多种action字段
            action = (
                task.get("action") or
                task.get("operation") or
                task.get("task") or
                task.get("query_type") or
                task.get("type") or  # 新增对type字段的兼容
                (("weather" if "weather" in str(task).lower() else None) if any(k in task for k in ["city", "weather", "get_weather"]) else None) or
                (("time" if "time" in str(task).lower() else None) if any(k in task for k in ["time", "get_time"]) else None)
            )
            ip = task.get("ip")
            city = task.get("city") or task.get("location")  # 兼容location字段
            query = task.get("query")
            format = task.get("format")
            # 兜底：如果action还没有，尝试从query/format推断
            if not action:
                if query:
                    if 'time' in query or '时间' in query:
                        action = 'time'
                    elif 'weather' in query or '天气' in query:
                        action = 'weather'
                elif format:
                    if 'time' in format or '时间' in format:
                        action = 'time'
                    elif 'weather' in format or '天气' in format:
                        action = 'weather'
            result = await self._tool.handle(action, ip, city, query, format)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e), "data": {}}, ensure_ascii=False)