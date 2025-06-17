import os
from config import DEEPSEEK_API_KEY  # 导入API密钥

from agent.tools_and_schemas import SearchQueryList, Reflection
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig
from langchain_deepseek import ChatDeepSeek

from agent.state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from agent.configuration import Configuration
from agent.prompts import (
    get_current_date,
    query_writer_instructions,
    web_searcher_instructions,
    reflection_instructions,
    answer_instructions,
)
from agent.utils import (
    Utils,
)

load_dotenv()

# 创建默认配置
default_config = Configuration(api_key=DEEPSEEK_API_KEY)

# 用于搜索API的客户端
genai_client = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0,
    api_key=default_config.api_key
)

# 节点定义

def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph 节点：根据用户问题生成搜索查询。

    使用 Gemini 2.0 Flash 基于用户问题生成用于网络研究的优化搜索查询。

    参数：
        state: 当前图状态，包含用户问题
        config: 可运行配置，包括 LLM 提供者设置

    返回：
        包含状态更新的字典，其中 search_query 键包含生成的查询
    """
    configurable = Configuration.from_runnable_config(config)

    # 检查自定义初始搜索查询数量
    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    # 初始化 Gemini 2.0 Flash
    llm = ChatDeepSeek(
        model=configurable.query_generator_model,
        temperature=1.0,
        max_retries=2,
        api_key=configurable.api_key or default_config.api_key,
    )
    structured_llm = llm.with_structured_output(SearchQueryList)

    # 格式化提示词
    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=Utils.get_research_topic(state["messages"]),
        number_queries=state["initial_search_query_count"],
    )
    # 生成搜索查询
    result = structured_llm.invoke(formatted_prompt)
    return {"query_list": result.query}


def continue_to_web_research(state: QueryGenerationState):
    """LangGraph 节点：将搜索查询发送到网络研究节点。

    用于为每个搜索查询生成 n 个 web_research 节点。
    """
    return [
        Send("web_research", {"search_query": search_query, "id": int(idx)})
        for idx, search_query in enumerate(state["query_list"])
    ]


def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph 节点：使用原生 Google Search API 工具进行网络研究。

    结合 Gemini 2.0 Flash 和 Google Search API 工具执行网络搜索。

    参数：
        state: 当前图状态，包含搜索查询和研究循环计数
        config: 可运行配置，包括搜索 API 设置

    返回：
        包含状态更新的字典，包括 sources_gathered、research_loop_count 和 web_research_results
    """
    # 配置
    configurable = Configuration.from_runnable_config(config)
    formatted_prompt = web_searcher_instructions.format(
        current_date=get_current_date(),
        research_topic=Utils.get_research_topic(state["messages"]),
    )

    # 使用deepseek客户端
    response = genai_client.models.generate_content(
        model=configurable.query_generator_model,
        contents=formatted_prompt,
        config={
            "tools": [{"web_search": {}}],
            "temperature": 0,
        },
    )
    # 将长 url 解析为短 url，节省 token 和时间
    resolved_urls = Utils.resolve_urls(
        response.candidates[0].grounding_metadata.grounding_chunks, state["id"]
    )
    # 获取引用并添加到生成文本中
    citations = Utils.get_citations(response, resolved_urls)
    modified_text = Utils.insert_citation_markers(response.text, citations)
    sources_gathered = [item for citation in citations for item in citation["segments"]]

    return {
        "sources_gathered": sources_gathered,
        "search_query": [state["search_query"]],
        "web_research_result": [modified_text],
    }


def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """LangGraph 节点：识别知识空白并生成后续查询。

    分析当前总结，识别需要进一步研究的领域，并生成后续查询。使用结构化输出以 JSON 格式提取后续查询。

    参数：
        state: 当前图状态，包含运行中的总结和研究主题
        config: 可运行配置，包括 LLM 提供者设置

    返回：
        包含状态更新的字典，其中 search_query 键包含生成的后续查询
    """
    configurable = Configuration.from_runnable_config(config)
    # 增加研究循环计数并获取推理模型
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model") or configurable.reasoning_model

    # 格式化提示词
    current_date = get_current_date()
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=Utils.get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(state["web_research_result"]),
    )
    # 初始化推理模型
    llm = ChatDeepSeek(
        model=reasoning_model,
        temperature=1.0,
        max_retries=2,
        api_key=configurable.api_key or default_config.api_key,
    )
    result = llm.with_structured_output(Reflection).invoke(formatted_prompt)

    return {
        "is_sufficient": result.is_sufficient,
        "knowledge_gap": result.knowledge_gap,
        "follow_up_queries": result.follow_up_queries,
        "research_loop_count": state["research_loop_count"],
        "number_of_ran_queries": len(state["search_query"]),
    }


def evaluate_research(
    state: ReflectionState,
    config: RunnableConfig,
) -> OverallState:
    """LangGraph 路由函数：决定研究流程的下一步。

    控制研究循环，判断是否继续收集信息或根据最大研究循环数配置结束总结。

    参数：
        state: 当前图状态，包含研究循环计数
        config: 可运行配置，包括 max_research_loops 设置

    返回：
        字符串字面量，指示下一个节点（"web_research" 或 "finalize_summary"）
    """
    configurable = Configuration.from_runnable_config(config)
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        return "finalize_answer"
    else:
        return [
            Send(
                "web_research",
                {
                    "search_query": follow_up_query,
                    "id": state["number_of_ran_queries"] + int(idx),
                },
            )
            for idx, follow_up_query in enumerate(state["follow_up_queries"])
        ]


def finalize_answer(state: OverallState, config: RunnableConfig):
    """LangGraph 节点：生成最终研究总结。

    对来源去重和格式化，然后与运行中的总结结合，生成结构良好、带有正确引用的研究报告。

    参数：
        state: 当前图状态，包含运行中的总结和收集到的来源

    返回：
        包含状态更新的字典，其中 running_summary 键包含格式化后的最终总结及来源
    """
    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.reasoning_model

    # 格式化提示词
    current_date = get_current_date()
    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=Utils.get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
    )

    # 初始化推理模型，默认为 Gemini 2.5 Flash
    llm = ChatDeepSeek(
        model=reasoning_model,
        temperature=0,
        max_retries=2,
        api_key=configurable.api_key or default_config.api_key,
    )
    result = llm.invoke(formatted_prompt)

    # 替换短 url 为原始 url，并将所有用到的 url 添加到 sources_gathered
    unique_sources = []
    for source in state["sources_gathered"]:
        if source["short_url"] in result.content:
            result.content = result.content.replace(
                source["short_url"], source["value"]
            )
            unique_sources.append(source)

    return {
        "messages": [AIMessage(content=result.content)],
        "sources_gathered": unique_sources,
    }

# 创建 Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# 定义各节点
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

# 设置入口为 generate_query
builder.add_edge(START, "generate_query")
# 添加条件边，继续并行分支的搜索查询
builder.add_conditional_edges(
    "generate_query", continue_to_web_research, ["web_research"]
)
# 反思网络研究
builder.add_edge("web_research", "reflection")
# 评估研究
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
# 最终答案
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent")
