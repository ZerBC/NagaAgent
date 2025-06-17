import os
from typing import Any, Optional
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig

class Configuration(BaseModel):
    """智能体配置类，用于管理Agent的所有配置参数。
    
    包含模型选择、查询生成、研究循环等配置项。
    支持从环境变量和RunnableConfig中加载配置。
    """
    
    # API配置
    api_key: str = Field(
        default="",
        description="DeepSeek API密钥"
    )
    
    # 模型配置
    query_generator_model: str = Field(
        default="deepseek-chat",
        description="用于生成搜索查询的模型名称"
    )
    
    reflection_model: str = Field(
        default="deepseek-chat",
        description="用于反思和评估的模型名称"
    )
    
    answer_model: str = Field(
        default="deepseek-chat",
        description="用于生成最终答案的模型名称"
    )
    
    # 研究参数配置
    number_of_initial_queries: int = Field(
        default=3,
        description="初始搜索查询数量",
        ge=1,
        le=10
    )
    
    max_research_loops: int = Field(
        default=2,
        description="最大研究循环次数",
        ge=1,
        le=5
    )
    
    # 搜索配置
    search_timeout: int = Field(
        default=30,
        description="搜索超时时间(秒)",
        ge=10,
        le=120
    )
    
    max_search_results: int = Field(
        default=5,
        description="每次搜索最大结果数",
        ge=1,
        le=10
    )
    
    # 记忆配置
    memory_window: int = Field(
        default=20,
        description="记忆窗口大小(轮数)",
        ge=5,
        le=50
    )
    
    # 兼容性配置
    compat_mode: bool = Field(
        default=False,
        description="是否启用兼容模式"
    )
    
    # 性能配置
    batch_size: int = Field(
        default=3,
        description="批处理大小",
        ge=1,
        le=10
    )
    
    cache_enabled: bool = Field(
        default=True,
        description="是否启用缓存"
    )
    
    # 调试配置
    debug_mode: bool = Field(
        default=False,
        description="是否启用调试模式"
    )
    
    log_level: str = Field(
        default="INFO",
        description="日志级别",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """从RunnableConfig创建配置实例。
        
        支持从环境变量和配置对象中加载配置。
        环境变量优先级高于配置对象。
        
        参数:
            config: 可选的RunnableConfig对象
            
        返回:
            Configuration实例
        """
        # 获取配置对象
        configurable = (
            config.get("configurable", {}) if config else {}
        )
        
        # 从环境变量或配置中获取原始值
        raw_values: dict[str, Any] = {}
        
        # 遍历所有字段
        for name in cls.model_fields.keys():
            # 尝试从环境变量获取
            env_value = os.environ.get(name.upper())
            if env_value is not None:
                # 根据字段类型转换环境变量值
                field = cls.model_fields[name]
                if field.annotation == bool:
                    raw_values[name] = env_value.lower() in ("true", "1", "yes")
                elif field.annotation == int:
                    raw_values[name] = int(env_value)
                else:
                    raw_values[name] = env_value
            # 如果环境变量不存在，尝试从配置对象获取
            elif name in configurable:
                raw_values[name] = configurable[name]
        
        # 创建配置实例
        return cls(**raw_values)
    
    def to_dict(self) -> dict[str, Any]:
        """将配置转换为字典格式。
        
        返回:
            包含所有配置项的字典
        """
        return self.model_dump()
    
    def update(self, **kwargs) -> None:
        """更新配置项。
        
        参数:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def validate(self) -> bool:
        """验证配置是否有效。
        
        返回:
            配置是否有效
        """
        try:
            self.model_validate(self.model_dump())
            return True
        except Exception:
            return False

# 默认配置实例
default_config = Configuration()

# 导出配置类
__all__ = ["Configuration", "default_config"]