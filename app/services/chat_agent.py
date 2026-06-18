import os, re, json
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware import SummarizationMiddleware
from huggingface_hub.cli.cache import summarize_deletions
from langchain.agents import create_agent
from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI
from app.api.request_remote.get_structure_tree import get_structure_tree
from app.api.request_remote.analysis_service_find_by_between_date import analysis_service_find_by_between_date
from app.api.request_remote.multiDimension_report import multiDimension_report
from app.tools.generate_option import send_chart_option
from app.tools.get_current_date import get_current_date
from langgraph.checkpoint.memory import MemorySaver
from app.services.prompts import system_prompt
from app.utils.logger import log_messages
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import gradio as gr
import uuid

class AgentResponse(BaseModel):
    # 助手的文本回复（必填）
    message: str = Field(..., description="给用户的文本回复内容")

    # 结构化图表数据（可选）
    # 注意：这里直接存 dict，前端拿到后可以直接注入 echarts.setOption()
    chart_option: Optional[Dict[str, Any]] = Field(
        None, description="ECharts 的配置对象，如果没有图表则为 null"
    )

    # 元数据，方便前端处理逻辑
    has_chart: bool = Field(False, description="是否包含图表数据")

    content_type: str = Field("text", description="内容类型：text, echarts, table 等")

llm = ChatOpenAI(
    model = os.getenv("llm_model"),
    api_key=os.getenv("llm_api_key"),
    base_url=os.getenv("llm_base_url"),
    temperature=0,
    streaming=True,
    extra_body={
        # "enable_thinking": False,
        "parallel_tool_calls": False
    },
)


memory = MemorySaver()
config = {"configurable": {"thread_id": os.getenv("secrekey")}}


agent = create_deep_agent(
    model=llm,
    tools=[get_structure_tree, analysis_service_find_by_between_date,
           multiDimension_report, get_current_date, send_chart_option],
    checkpointer=memory,
    system_prompt=system_prompt,
)


def ask(query: str) -> AgentResponse:
    # 🔑 1. 获取当前已有的历史状态
    state = agent.get_state(config)
    history = state.values.get("messages", [])

    # 🔑 2. 执行滑动窗口裁剪
    if len(history) > 10:
        history = history[-9:]
        agent.update_state(config, {"messages": history})

    inputs = {"messages": [{"role": "user", "content": query}]}
    result = agent.invoke(inputs, config)

    all_messages = result["messages"]
    log_messages(all_messages)
    chart_option = None
    answer_text = ""

    # 从后往前遍历，只寻找属于“当前轮次”的消息
    # 我们从最后一条消息开始查，直到遇到这一轮的用户 query 为止
    for msg in reversed(all_messages):
        # 1. 提取文字回复（最后一条 AI 消息）
        if msg.type == "ai" and not answer_text:
            answer_text = msg.content

        # 2. 提取当前轮次的工具调用
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "send_chart_option":
                    option_arg = tc["args"].get("option")
                    if isinstance(option_arg, str):
                        try:
                            # 如果是字符串，尝试解析为 JSON 对象
                            chart_option = json.loads(option_arg)
                        except json.JSONDecodeError:
                            # 如果解析失败，保持原样
                            chart_option = option_arg
                    else:
                        # 如果已经是对象，直接使用
                        chart_option = option_arg
                    break

        # 关键点：如果我们已经回溯到了当前轮次的用户请求，就停止回溯
        # 这样可以防止获取到上一轮对话中的 tool_calls
        if msg.type == "human":
            break

    return AgentResponse(
        message=answer_text,
        chart_option=chart_option,
        has_chart=chart_option is not None,
        content_type="echarts" if chart_option else "text"
    )


def ask_stream(query: str):
    """
    流式发送查询：
    1. 实时 yield 文本内容
    2. 结束后从 LangGraph 状态中提取当前轮次的图表数据，避免重复调用 LLM
    """
    # 🔑 1. 获取当前已有的历史状态
    state = agent.get_state(config)
    history = state.values.get("messages", [])
    print(len(history))
    print("history: ", history)

    # 🔑 2. 执行滑动窗口裁剪
    if len(history) > 12:
        history = history[-8:]
        agent.update_state(config, {"messages": history})
        print("new_history: ", history)
        print("new_history_len: ",len(history))

    inputs = {"messages": [{"role": "user", "content": query}]}

    # --- 第一阶段：执行流式输出 ---
    # 使用 stream_mode="messages" 实时获取 AI 文本片段
    for chunk, metadata in agent.stream(inputs, config, stream_mode="messages"):
        if hasattr(chunk, "reasoning_content") and chunk.reasoning_content:
            yield chunk.reasoning_content
        if hasattr(chunk, "content") and chunk.content and chunk.type == "AIMessageChunk":
            yield chunk.content
            # 检测工具调用并输出提示信息
        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            for tc in chunk.tool_calls:
                tool_name = tc.get("name", "")
                if tool_name:
                    yield f'<span class="tool-call-notice" data-tool-name="{tool_name}" style="display: inline-block; padding: 2px 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; font-size: 11px; line-height: 1.2; margin: 2px 0;">🔧 正在调用{tool_name}...</span>'

    # --- 第二阶段：提取结果（不再次调用 invoke） ---
    # 此时 agent 的状态已经更新到了内存中，我们直接读取最新状态
    state = agent.get_state(config)
    all_messages = state.values.get("messages", [])
    log_messages(all_messages)

    current_chart_option = None

    # 逆序遍历，确保只获取“当前轮次”产生的数据
    # 逻辑：从最后一条消息回溯，直到遇到本次提问的 HumanMessage
    for msg in reversed(all_messages):
        # 查找最新的工具调用
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "send_chart_option":
                    option_arg = tc["args"].get("option")
                    if isinstance(option_arg, str):
                        try:
                            # 如果是字符串，尝试解析为 JSON 对象
                            current_chart_option = json.loads(option_arg)
                        except json.JSONDecodeError:
                            # 如果解析失败，保持原样
                            current_chart_option = option_arg
                    else:
                        # 如果已经是对象，直接使用
                        current_chart_option = option_arg
                    break

        if current_chart_option:
            break

        # 核心：一旦遇到 HumanMessage，说明已经跨过当前轮次进入历史记录了
        if msg.type == "human":
            break

    print("current_chart_option: ", current_chart_option)
    # --- 第三阶段：发送图表元数据 ---
    # 以约定好的字典格式发送给前端（Gradio 或自定义前端）
    yield {
        "has_chart": current_chart_option is not None,
        "chart_option": current_chart_option,
        "content_type": "echarts" if current_chart_option else "text"
    }
