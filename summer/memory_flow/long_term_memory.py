# 长期记忆管理模块，faiss主库，权重动态管理
# from summer.summer_faiss import faiss_add, faiss_recall # 注释掉faiss导入
from config import LONG_TERM_CONSOLIDATE_WEIGHT
import time
from collections import defaultdict
import json, os
from config import LOG_DIR

class LongTermMemory:
    def __init__(self, meta, usage):
        self.meta = meta
        self.usage = usage
    def add(self, chunk):
        """长期记忆写入，满足条件才写入faiss"""
        # faiss_add([chunk]) # 注释掉faiss写入
        key = chunk.get('key')
        now = time.time()
        meta = self.meta.get(key, {})
        # 只有权重高/被标记/AI判定重要才写入faiss
        if meta.get('weight', 0) >= LONG_TERM_CONSOLIDATE_WEIGHT or meta.get('important', False):
            # faiss_add([chunk]) # 注释掉faiss写入
            self.meta[key] = {**chunk, 'weight': meta.get('weight', 1), 'last_used': now, 'level': 'long_term'}
            self.usage[key] = now
        else:
            # 只更新meta和usage，不写入faiss
            self.meta[key] = {**chunk, 'weight': meta.get('weight', 1), 'last_used': now, 'level': 'long_term'}
            self.usage[key] = now
    def recall(self, query, k=5, theme=None):
        """长期记忆召回，使用faiss检索"""
        # ltm_future = faiss_recall(query, k) # 注释掉faiss召回
        # return ltm_future
        return [] # 返回空列表作为占位符
