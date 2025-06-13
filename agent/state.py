from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
from langgraph.graph import add_messages
import operator
from datetime import datetime

# 基础状态类
class BaseState(dict):
    """基础状态类，提供通用功能"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._timestamp = datetime.now()
    
    @property
    def timestamp(self) -> datetime:
        """获取状态创建时间"""
        return self._timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return dict(self)

# 整体状态
class OverallState(TypedDict):
    """整体状态，包含所有必要的信息"""
    messages: Annotated[list, add_messages]  # 消息历史
    search_query: Annotated[list, operator.add]  # 搜索查询列表
    web_research_result: Annotated[list, operator.add]  # 网络研究结果
    sources_gathered: Annotated[list, operator.add]  # 收集的来源
    initial_search_query_count: int  # 初始查询数量
    max_research_loops: int  # 最大研究循环数
    research_loop_count: int  # 当前研究循环数
    reasoning_model: str  # 推理模型
    theme: Optional[str]  # 主题
    memory_level: Optional[str]  # 记忆层级
    context: Optional[str]  # 上下文信息

# 反思状态
class ReflectionState(TypedDict):
    """反思状态，用于评估研究进度"""
    is_sufficient: bool  # 研究是否充分
    knowledge_gap: str  # 知识空白
    follow_up_queries: Annotated[list, operator.add]  # 后续查询
    research_loop_count: int  # 研究循环计数
    number_of_ran_queries: int  # 已运行查询数
    confidence_score: float  # 置信度分数
    reasoning: str  # 推理过程

# 查询类
class Query(TypedDict):
    """单个查询的结构"""
    query: str  # 查询内容
    rationale: str  # 查询理由
    priority: int  # 优先级
    context: Optional[str]  # 上下文

# 查询生成状态
class QueryGenerationState(TypedDict):
    """查询生成状态"""
    query_list: List[Query]  # 查询列表
    research_topic: str  # 研究主题
    constraints: Dict[str, Any]  # 约束条件
    metadata: Dict[str, Any]  # 元数据

# 网络搜索状态
class WebSearchState(TypedDict):
    """网络搜索状态"""
    search_query: str  # 搜索查询
    id: str  # 查询ID
    filters: Dict[str, Any]  # 搜索过滤器
    timeout: int  # 超时时间
    max_results: int  # 最大结果数

# 搜索状态输出
@dataclass(kw_only=True)
class SearchStateOutput:
    """搜索状态输出"""
    running_summary: str = field(default=None)  # 运行中的总结
    sources: List[Dict[str, Any]] = field(default_factory=list)  # 来源列表
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

# 记忆状态
class MemoryState(TypedDict):
    """记忆状态"""
    content: str  # 内容
    theme: str  # 主题
    level: str  # 层级
    importance: float  # 重要性
    timestamp: datetime  # 时间戳
    metadata: Dict[str, Any]  # 元数据

# 对话状态
class ConversationState(TypedDict):
    """对话状态"""
    messages: List[Dict[str, Any]]  # 消息历史
    context: str  # 上下文
    theme: str  # 主题
    memory_level: str  # 记忆层级
    metadata: Dict[str, Any]  # 元数据

# 状态工厂
class StateFactory:
    """状态工厂，用于创建各种状态实例"""
    
    @staticmethod
    def create_overall_state(**kwargs) -> OverallState:
        """创建整体状态"""
        return OverallState(**kwargs)
    
    @staticmethod
    def create_reflection_state(**kwargs) -> ReflectionState:
        """创建反思状态"""
        return ReflectionState(**kwargs)
    
    @staticmethod
    def create_query_state(**kwargs) -> QueryGenerationState:
        """创建查询状态"""
        return QueryGenerationState(**kwargs)
    
    @staticmethod
    def create_web_search_state(**kwargs) -> WebSearchState:
        """创建网络搜索状态"""
        return WebSearchState(**kwargs)
    
    @staticmethod
    def create_memory_state(**kwargs) -> MemoryState:
        """创建记忆状态"""
        return MemoryState(**kwargs)
    
    @staticmethod
    def create_conversation_state(**kwargs) -> ConversationState:
        """创建对话状态"""
        return ConversationState(**kwargs)

# 状态管理器
class StateManager:
    """状态管理器，用于管理状态的生命周期"""
    
    def __init__(self):
        self._states: Dict[str, BaseState] = {}
        self._factory = StateFactory()
    
    def create_state(self, state_type: str, **kwargs) -> BaseState:
        """创建新状态"""
        if state_type == "overall":
            state = self._factory.create_overall_state(**kwargs)
        elif state_type == "reflection":
            state = self._factory.create_reflection_state(**kwargs)
        elif state_type == "query":
            state = self._factory.create_query_state(**kwargs)
        elif state_type == "web_search":
            state = self._factory.create_web_search_state(**kwargs)
        elif state_type == "memory":
            state = self._factory.create_memory_state(**kwargs)
        elif state_type == "conversation":
            state = self._factory.create_conversation_state(**kwargs)
        else:
            raise ValueError(f"未知的状态类型: {state_type}")
        
        self._states[state_type] = state
        return state
    
    def get_state(self, state_type: str) -> Optional[BaseState]:
        """获取状态"""
        return self._states.get(state_type)
    
    def update_state(self, state_type: str, **kwargs) -> None:
        """更新状态"""
        if state_type in self._states:
            state = self._states[state_type]
            state.update(**kwargs)
    
    def clear_state(self, state_type: str) -> None:
        """清除状态"""
        if state_type in self._states:
            del self._states[state_type]

# 导出
__all__ = [
    "BaseState",
    "OverallState",
    "ReflectionState",
    "Query",
    "QueryGenerationState",
    "WebSearchState",
    "SearchStateOutput",
    "MemoryState",
    "ConversationState",
    "StateFactory",
    "StateManager"
]