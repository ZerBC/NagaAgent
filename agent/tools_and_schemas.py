from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json

# 基础模型
class BaseSchema(BaseModel):
    """基础模型类，提供通用功能"""
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.model_dump()

# 搜索查询列表
class SearchQueryList(BaseSchema):
    """搜索查询列表模型"""
    query: List[str] = Field(
        description="用于网络研究的搜索查询列表",
        min_items=1,
        max_items=10
    )
    rationale: str = Field(
        description="简要说明这些查询与研究主题相关的原因",
        min_length=10
    )
    priority: List[int] = Field(
        description="每个查询的优先级(1-5)",
        default_factory=list
    )
    context: Optional[str] = Field(
        description="查询的上下文信息",
        default=None
    )

    @validator('priority')
    def validate_priority(cls, v, values):
        """验证优先级列表"""
        if 'query' in values and len(v) != len(values['query']):
            raise ValueError("优先级列表长度必须与查询列表相同")
        if not all(1 <= p <= 5 for p in v):
            raise ValueError("优先级必须在1-5之间")
        return v

# 反思结果
class Reflection(BaseSchema):
    """反思结果模型"""
    is_sufficient: bool = Field(
        description="提供的总结内容是否足以回答用户问题"
    )
    knowledge_gap: str = Field(
        description="描述缺失或需要澄清的信息",
        min_length=10
    )
    follow_up_queries: List[str] = Field(
        description="为弥补知识空白而生成的后续查询列表",
        min_items=0,
        max_items=5
    )
    confidence_score: float = Field(
        description="当前答案的置信度(0-1)",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="反思的推理过程",
        min_length=20
    )

# 搜索结果
class SearchResult(BaseSchema):
    """搜索结果模型"""
    title: str = Field(description="结果标题")
    url: str = Field(description="结果URL")
    snippet: str = Field(description="结果摘要")
    relevance_score: float = Field(
        description="相关性分数(0-1)",
        ge=0.0,
        le=1.0
    )
    timestamp: datetime = Field(description="结果时间戳")
    source_type: str = Field(description="来源类型")
    metadata: Dict[str, Any] = Field(
        description="额外元数据",
        default_factory=dict
    )

# 研究计划
class ResearchPlan(BaseSchema):
    """研究计划模型"""
    topic: str = Field(description="研究主题")
    queries: List[SearchQueryList] = Field(description="查询计划")
    max_iterations: int = Field(
        description="最大迭代次数",
        ge=1,
        le=5
    )
    constraints: Dict[str, Any] = Field(
        description="研究约束条件",
        default_factory=dict
    )
    expected_output: str = Field(description="预期输出格式")

# 记忆条目
class MemoryEntry(BaseSchema):
    """记忆条目模型"""
    content: str = Field(description="记忆内容")
    theme: str = Field(description="主题分类")
    level: str = Field(
        description="记忆层级",
        pattern="^(core|archival|long_term|short_term)$"
    )
    importance: float = Field(
        description="重要性分数(0-1)",
        ge=0.0,
        le=1.0
    )
    timestamp: datetime = Field(description="创建时间")
    metadata: Dict[str, Any] = Field(
        description="元数据",
        default_factory=dict
    )

# 对话消息
class Message(BaseSchema):
    """对话消息模型"""
    role: str = Field(
        description="消息角色",
        pattern="^(user|assistant|system)$"
    )
    content: str = Field(description="消息内容")
    timestamp: datetime = Field(description="发送时间")
    metadata: Dict[str, Any] = Field(
        description="元数据",
        default_factory=dict
    )

# 工具配置
class ToolConfig(BaseSchema):
    """工具配置模型"""
    name: str = Field(description="工具名称")
    enabled: bool = Field(description="是否启用")
    parameters: Dict[str, Any] = Field(
        description="工具参数",
        default_factory=dict
    )
    timeout: int = Field(
        description="超时时间(秒)",
        ge=1,
        le=300
    )
    retry_count: int = Field(
        description="重试次数",
        ge=0,
        le=3
    )

# 工具结果
class ToolResult(BaseSchema):
    """工具执行结果模型"""
    success: bool = Field(description="是否成功")
    result: Any = Field(description="执行结果")
    error: Optional[str] = Field(description="错误信息")
    execution_time: float = Field(description="执行时间(秒)")
    metadata: Dict[str, Any] = Field(
        description="元数据",
        default_factory=dict
    )

# 工具注册器
class ToolRegistry:
    """工具注册器，用于管理工具"""
    
    def __init__(self):
        self._tools: Dict[str, ToolConfig] = {}
    
    def register_tool(self, tool: ToolConfig) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())
    
    def remove_tool(self, name: str) -> None:
        """移除工具"""
        if name in self._tools:
            del self._tools[name]

# 导出
__all__ = [
    "BaseSchema",
    "SearchQueryList",
    "Reflection",
    "SearchResult",
    "ResearchPlan",
    "MemoryEntry",
    "Message",
    "ToolConfig",
    "ToolResult",
    "ToolRegistry"
]