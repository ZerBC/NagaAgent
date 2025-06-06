# app_name_matcher.py # 智能应用名适配与动态学习
import difflib
import os
import json

# 别名库文件路径
ALIAS_PATH = os.path.join(os.path.dirname(__file__), "app_alias.json")

def load_alias_dict():
    """加载别名库"""
    if os.path.exists(ALIAS_PATH):
        with open(ALIAS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_alias_dict(alias_dict):
    """保存别名库"""
    with open(ALIAS_PATH, "w", encoding="utf-8") as f:
        json.dump(alias_dict, f, ensure_ascii=False, indent=2)

def update_alias(user_input, real_name):
    """动态学习：记录用户说法与真实应用名的映射"""
    alias_dict = load_alias_dict()
    if user_input and real_name and user_input != real_name:
        alias_dict[user_input] = real_name
        save_alias_dict(alias_dict)

def calc_similarity(a, b):
    """综合相似度：拼音、英文、编辑距离"""
    a, b = a.lower(), b.lower()
    # 直接包含
    if a in b or b in a:
        return 1.0
    # 编辑距离相似度
    seq = difflib.SequenceMatcher(None, a, b)
    return seq.ratio()

def find_best_app(user_input, app_list):
    """智能查找最优应用"""
    alias_dict = load_alias_dict()
    # 1. 先查别名库
    if user_input in alias_dict:
        real_name = alias_dict[user_input]
        for app in app_list:
            if app['name'] == real_name:
                return app
    # 2. 多策略模糊匹配
    candidates = []
    for app in app_list:
        score = calc_similarity(user_input, app['name'])
        # 英文别名支持
        if ' ' in app['name']:
            for part in app['name'].split():
                score = max(score, calc_similarity(user_input, part))
        candidates.append((score, app))
    candidates.sort(reverse=True, key=lambda x: x[0])
    # 3. 返回最优（阈值可调）
    if candidates and candidates[0][0] > 0.6:
        return candidates[0][1]
    return None
