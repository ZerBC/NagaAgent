import logging,os,asyncio # 日志与系统
from datetime import datetime # 时间
from config import LOG_DIR,DEEPSEEK_API_KEY,DEEPSEEK_MODEL,TEMPERATURE,MAX_TOKENS,get_current_datetime,THEME_ROOTS,DEEPSEEK_BASE_URL,NAGA_SYSTEM_PROMPT,VOICE_ENABLED # 配置
from summer.summer_faiss import faiss_recall,faiss_add,faiss_fuzzy_recall # faiss检索与入库
from mcpserver.mcp_manager import get_mcp_manager, remove_tools_filter, HandoffInputData # 多功能管理
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX # handoff提示词
from mcpserver.agent_playwright_master import PlaywrightAgent, extract_url # 导入浏览器相关类
from openai import OpenAI,AsyncOpenAI # LLM
import difflib # 模糊匹配
import sys,json,traceback
from voice.voice_config import config as vcfg # 语音配置
from voice.voice_handler import VoiceHandler # 语音处理
import time # 时间戳打印
from summer.memory_manager import MemoryManager  # 新增
from mcpserver.mcp_registry import register_all_handoffs # 导入批量注册方法
from handoff_executor import execute_plan
now=lambda:time.strftime('%H:%M:%S:')+str(int(time.time()*1000)%10000) # 当前时间
_builtin_print=print
print=lambda *a,**k:sys.stderr.write('[print] '+(' '.join(map(str,a)))+'\n')

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("NagaConversation")

_MCP_HANDOFF_REGISTERED=False

class NagaConversation: # 对话主类
 def __init__(s):
  s.mcp=get_mcp_manager()
  s.messages=[]
  s.dev_mode=False
  s.voice=VoiceHandler() if vcfg.ENABLED else None
  s.client=OpenAI(api_key=DEEPSEEK_API_KEY,base_url=DEEPSEEK_BASE_URL.rstrip('/')+'/')
  s.async_client=AsyncOpenAI(api_key=DEEPSEEK_API_KEY,base_url=DEEPSEEK_BASE_URL.rstrip('/')+'/')
  s.memory = MemoryManager()  # 新增：初始化记忆管理器
  s.compat_mode = False # 新增：兼容升级模式状态
  global _MCP_HANDOFF_REGISTERED
  if not _MCP_HANDOFF_REGISTERED:
    try:
      logger.info("开始注册所有Agent handoff处理器...")
      register_all_handoffs(s.mcp) # 一键注册所有Agent
      logger.info("成功注册所有Agent handoff处理器")
      _MCP_HANDOFF_REGISTERED=True
    except Exception as e:
      logger.error(f"注册Agent handoff处理器失败: {e}")
      traceback.print_exc(file=sys.stderr)
 def save_log(s,u,a): # 保存对话日志
  if s.dev_mode:return # 开发者模式不写日志
  d=datetime.now().strftime('%Y-%m-%d')
  t=datetime.now().strftime('%H:%M:%S')
  f=os.path.join(LOG_DIR,f'{d}.txt')
  with open(f,'a',encoding='utf-8')as w:w.write(f'-'*50+f'\n时间: {d} {t}\n用户: {u}\n娜迦: {a}\n\n')
 def normalize_theme(s,raw): # 主题归一化
  seg=raw.split('/')
  root=difflib.get_close_matches(seg[0],THEME_ROOTS.keys(),n=1,cutoff=0.6)
  root=root[0] if root else list(THEME_ROOTS.keys())[0]
  if len(seg)>1:
    sub=difflib.get_close_matches(seg[1],THEME_ROOTS[root],n=1,cutoff=0.6)
    sub=sub[0] if sub else THEME_ROOTS[root][0]
    return '/'.join([root,sub]+seg[2:])
  return root
 def get_theme_and_level(s, u): # LLM主题+分层判定
  r = s.client.chat.completions.create(
      model=DEEPSEEK_MODEL,
      messages=[
          {"role": "system", "content": "请用/分隔输出本轮对话主题树（如'科技/人工智能/大模型'），并判断内容应归为哪类记忆层级（core/archival/long_term/short_term）。\n请用如下JSON格式返回：{\"theme\": \"主题树\", \"level\": \"core/archival/long_term/short_term\"}，不要多余内容。"},
          {"role": "user", "content": u}
      ],
      temperature=0.2,
      max_tokens=40
  ).choices[0].message.content
  try:
      result = json.loads(r)
      theme = s.normalize_theme(result.get('theme',''))
      level = result.get('level','').strip().lower()
      if level not in ['core','archival','long_term','short_term']:
          level = None
      return theme, level
  except Exception:
      # 兜底：只用原有主题判定，分层用规则
      theme = s.normalize_theme(u)
      text = u
      if '身份' in text:
          level = 'core'
      elif '重要事件' in text:
          level = 'archival'
      elif len(text) > 30:
          level = 'long_term'
      else:
          level = 'short_term'
      return theme, level
 def get_theme(s, u): # 兼容接口，内部用get_theme_and_level
  theme, _ = s.get_theme_and_level(u)
  return theme
 async def process(s,u):
  import json # 保证json在本地作用域可用
  try:
   # devmode优先判断
   if u.strip()=="#devmode":
    s.dev_mode=True
    yield ("娜迦","已进入开发者模式，后续对话不写入向量库");return
   # 兼容升级模式优先判断
   if u.strip() == '#夏园系统兼容升级':
    import subprocess, os, json
    LOG_DIR = 'logs'
    txt_files = [fn for fn in os.listdir(LOG_DIR) if fn.endswith('.txt') and fn[:4].isdigit() and fn[4] == '-' and fn[7] == '-']
    txt_files.sort()
    file_list_str = '发现以下历史对话日志：\n' + '\n'.join([f'{idx+1}. {fn}' for idx, fn in enumerate(txt_files)]) + '\n' + '-'*40
    subprocess.run(['python', 'summer/summer_upgrade/compat_txt_to_faiss.py', 'list'])
    HISTORY_JSON = os.path.join('summer', 'summer_upgrade', 'history_dialogs.json')
    try:
        with open(HISTORY_JSON, encoding='utf-8') as f:
            all_chunks = json.load(f)
        total = len(all_chunks)
    except Exception:
        total = 0
    msg = f"{file_list_str}\n共{total}条历史对话，已预热缓存至summer/summer_upgrade/history_dialogs.json\n请直接在对话框输入import命令（如import all或import 1,3,5-8）以完成选择性兼容。\n如需退出兼容模式，请输入exit。"
    s.compat_mode = True
    yield ("系统", msg)
    return
   # 兼容模式判断
   if hasattr(s, 'compat_mode') and s.compat_mode:
    if u.strip().startswith('import '):
     import subprocess, sys
     args = u.strip().split(' ', 1)[1]
     yield ("系统", "正在执行兼容导入程序，请稍候...")
     result = subprocess.run(
         [sys.executable, 'summer/summer_upgrade/compat_txt_to_faiss.py', 'import', args],
         capture_output=True, text=True
     )
     output = result.stdout.strip() or result.stderr.strip()
     yield ("系统", f"兼容导入结果：\n{output}")
     return
    elif u.strip() in ['exit', '完成', '退出兼容']:
     s.compat_mode = False
     yield ("系统", "已退出系统兼容升级模式，恢复正常对话。")
     return
    else:
     yield ("系统", "当前为系统兼容升级模式，仅支持import指令。如需退出，请输入exit。")
     return
   print(f"语音转文本结束，开始发送给GTP：{now()}") # 语音转文本结束/AI请求前
   theme, level = s.get_theme_and_level(u)
   ctx = s.memory.build_context(u, k=5)
   # 添加handoff提示词
   system_prompt = f"{RECOMMENDED_PROMPT_PREFIX}\n{NAGA_SYSTEM_PROMPT}"
   sysmsg={"role":"system","content":f"历史相关内容召回:\n{ctx}\n\n{system_prompt.format(available_mcp_services=s.mcp.format_available_services())}"} if ctx else {"role":"system","content":system_prompt.format(available_mcp_services=s.mcp.format_available_services())}
   msgs=[sysmsg] if sysmsg else[]
   msgs+=s.messages[-20:]+[{"role":"user","content":u}]
   
   print(f"GTP请求发送：{now()}") # AI请求前
   # 流式输出
   a = ''
   resp = await s.async_client.chat.completions.create(model=DEEPSEEK_MODEL,messages=msgs,temperature=TEMPERATURE,max_tokens=MAX_TOKENS,stream=True)
   async for chunk in resp:
    if chunk.choices and chunk.choices[0].delta.content:
     a+=chunk.choices[0].delta.content
     yield ("娜迦",chunk.choices[0].delta.content) # 流式yield不加换行
   print(f"GTP返回数据：{now()}") # AI返回
   
   # 新增：自动解析plan结构并分步执行
   try:
    resp_json = json.loads(a)
    if "plan" in resp_json:
        async for step in execute_plan(resp_json, s.mcp):
            yield ("娜迦", step.get("msg") or str(step))  # 实时反馈每一步
        return
   except Exception as e:
    pass # 非plan结构或解析失败，继续原有流程
   
   # 检查LLM是否建议handoff
   if "[handoff]" in a:
    service = a.split("[handoff]")[1].strip().split()[0]
    yield ("娜迦",(await s.mcp.handoff(
     service,
     task={
       "messages": s.messages[-5:],
       "query": u,
       "url": extract_url(u),
       "source": "llm",
       "input_type": "browser"
     }
    )));return
   
   s.messages+=[{"role":"user","content":u},{"role":"assistant","content":a}]
   s.save_log(u,a)
   if not s.dev_mode:
    faiss_add([{
        'text': a,
        'role': 'ai',
        'time': get_current_datetime(),
        'file': 'conversation.txt',
        'theme': theme  # 确保theme字段写入meta
    }])
   s.memory.add_memory({'role':'user','text':u,'time':get_current_datetime(),'file':datetime.now().strftime('%Y-%m-%d')+'.txt','theme':theme}, level=level)
   s.memory.add_memory({'role':'ai','text':a,'time':get_current_datetime(),'file':datetime.now().strftime('%Y-%m-%d')+'.txt','theme':theme}, level=level)
   # 新增：支持用户通过#important <内容片段>命令标记记忆为重要（单条或批量智能判断）
   if u.strip().startswith('#important'):
    mark_text = u.strip()[10:].strip()
    if not mark_text:
     yield ("娜迦","请在#important后输入要标记的重要内容片段。");return
    # 模糊召回多条相关记忆
    recall = s.memory.fuzzy_recall(mark_text, k=5)  # k值可根据需要调整
    if recall:
     keys = [item.get('key') for item in recall if 'key' in item]
     if len(keys) == 1:
      s.memory.mark_important(keys[0])
      yield ("娜迦",f"已将相关记忆片段标记为重要：{recall[0].get('text','')}");return
     else:
      updated = s.memory.mark_important_batch(keys)
      preview = "\n".join([f"{i+1}.{item.get('text','')[:30]}" for i,item in enumerate(recall)])
      yield ("娜迦",f"已批量标记{updated}条相关记忆为重要：\n{preview}");return
    else:
     yield ("娜迦","未找到相关记忆，无法标记。");return
   # 每20轮动态批量衰减权重
   s.memory.adjust_weights_periodically()
   return
  except Exception as e:
   import sys, traceback;traceback.print_exc(file=sys.stderr)
   yield ("娜迦",f"[MCP异常]: {e}");return

async def process_user_message(s,msg):
    if vcfg.ENABLED and not msg: #无文本输入时启动语音识别
        async for text in s.voice.stt_stream():
            if text:msg=text;break
    return await s.process(msg)

async def send_ai_message(s,msg):
    if vcfg.ENABLED: #启用语音时转换为语音
        async for _ in s.voice.tts_stream(msg):pass
    return msg 