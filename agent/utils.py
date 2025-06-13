from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import json
import re
from urllib.parse import urlparse
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage, SystemMessage
from .tools_and_schemas import SearchResult, Message, MemoryEntry

class Utils:
    """工具类，提供通用功能"""
    
    @staticmethod
    def get_research_topic(messages: List[AnyMessage]) -> str:
        """获取研究主题
        
        参数:
            messages: 消息历史列表
            
        返回:
            研究主题字符串
        """
        if not messages:
            return ""
            
        # 获取最后一条用户消息
        last_user_msg = next(
            (msg for msg in reversed(messages) if isinstance(msg, HumanMessage)),
            None
        )
        
        if last_user_msg:
            return last_user_msg.content
            
        # 如果没有用户消息，则合并所有消息
        return "\n".join(
            f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
            for msg in messages
        )

    @staticmethod
    def resolve_urls(urls_to_resolve: List[Any], id: int) -> Dict[str, str]:
        """解析URL列表
        
        参数:
            urls_to_resolve: URL列表
            id: 唯一标识符
            
        返回:
            URL映射字典
        """
        prefix = f"https://vertexaisearch.cloud.google.com/id/"
        urls = [site.web.uri for site in urls_to_resolve if hasattr(site, 'web')]
        
        return {
            url: f"{prefix}{id}-{idx}"
            for idx, url in enumerate(urls)
        }

    @staticmethod
    def insert_citation_markers(text: str, citations_list: List[Dict[str, Any]]) -> str:
        """在文本中插入引用标记
        
        参数:
            text: 原始文本
            citations_list: 引用列表
            
        返回:
            插入引用标记后的文本
        """
        if not citations_list:
            return text
            
        # 按结束索引降序排序
        sorted_citations = sorted(
            citations_list,
            key=lambda c: (c.get("end_index", 0), c.get("start_index", 0)),
            reverse=True
        )
        
        modified_text = text
        for citation in sorted_citations:
            end_idx = citation.get("end_index", 0)
            segments = citation.get("segments", [])
            
            if not segments:
                continue
                
            marker = " ".join(
                f"[{seg['label']}]({seg['short_url']})"
                for seg in segments
            )
            
            modified_text = (
                modified_text[:end_idx] +
                f" {marker}" +
                modified_text[end_idx:]
            )
            
        return modified_text

    @staticmethod
    def get_citations(
        response: Any,
        resolved_urls_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """获取引用信息
        
        参数:
            response: 模型响应对象
            resolved_urls_map: URL映射字典
            
        返回:
            引用信息列表
        """
        citations = []
        
        if not response or not hasattr(response, "candidates"):
            return citations
            
        candidate = response.candidates[0]
        if not hasattr(candidate, "grounding_metadata"):
            return citations
            
        metadata = candidate.grounding_metadata
        if not hasattr(metadata, "grounding_supports"):
            return citations
            
        for support in metadata.grounding_supports:
            if not hasattr(support, "segment"):
                continue
                
            segment = support.segment
            if segment.end_index is None:
                continue
                
            citation = {
                "start_index": segment.start_index or 0,
                "end_index": segment.end_index,
                "segments": []
            }
            
            if hasattr(support, "grounding_chunk_indices"):
                for idx in support.grounding_chunk_indices:
                    try:
                        chunk = metadata.grounding_chunks[idx]
                        if hasattr(chunk, "web"):
                            resolved_url = resolved_urls_map.get(chunk.web.uri)
                            if resolved_url:
                                citation["segments"].append({
                                    "label": chunk.web.title.split(".")[0],
                                    "short_url": resolved_url,
                                    "value": chunk.web.uri
                                })
                    except (IndexError, AttributeError):
                        continue
                        
            if citation["segments"]:
                citations.append(citation)
                
        return citations

    @staticmethod
    def format_message(msg: AnyMessage) -> Message:
        """格式化消息
        
        参数:
            msg: 原始消息对象
            
        返回:
            格式化后的消息对象
        """
        return Message(
            role="user" if isinstance(msg, HumanMessage) else
                 "assistant" if isinstance(msg, AIMessage) else
                 "system" if isinstance(msg, SystemMessage) else "unknown",
            content=msg.content,
            timestamp=datetime.now(),
            metadata={}
        )

    @staticmethod
    def parse_url(url: str) -> Dict[str, str]:
        """解析URL
        
        参数:
            url: URL字符串
            
        返回:
            URL组件字典
        """
        parsed = urlparse(url)
        return {
            "scheme": parsed.scheme,
            "netloc": parsed.netloc,
            "path": parsed.path,
            "params": parsed.params,
            "query": parsed.query,
            "fragment": parsed.fragment
        }

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本
        
        参数:
            text: 原始文本
            
        返回:
            清理后的文本
        """
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:，。！？；：]', '', text)
        return text.strip()

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
        """提取关键词
        
        参数:
            text: 文本内容
            max_keywords: 最大关键词数量
            
        返回:
            关键词列表
        """
        # 简单实现，实际应用中可以使用更复杂的算法
        words = re.findall(r'\w+', text.lower())
        word_freq = {}
        for word in words:
            if len(word) > 1:  # 忽略单字符
                word_freq[word] = word_freq.get(word, 0) + 1
                
        return sorted(
            word_freq.keys(),
            key=lambda x: word_freq[x],
            reverse=True
        )[:max_keywords]

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """计算文本相似度
        
        参数:
            text1: 文本1
            text2: 文本2
            
        返回:
            相似度分数(0-1)
        """
        # 简单实现，实际应用中可以使用更复杂的算法
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
            
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0

# 导出
__all__ = ["Utils"]