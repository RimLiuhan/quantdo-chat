# -*- coding: utf-8 -*-
import traceback

import gradio as gr
import os
import json
import random
from app.services.chat_agent import ask_stream

custom_css = """
footer { visibility: hidden !important; }
.input-row .button { width: auto !important; min-width: unset !important; flex: 0 0 auto !important; padding: 4px 16px !important; line-height: normal !important; align-self: stretch !important; }
.input-row .textbox { flex: 1 !important; }
.input-row { align-items: stretch !important; }

@keyframes fadeInOut {
    0% { opacity: 0; transform: translateY(-10px); }
    20% { opacity: 1; transform: translateY(0); }
    80% { opacity: 1; transform: translateY(0); }
    100% { opacity: 0; transform: translateY(-10px); }
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

@keyframes dots {
    0%, 20% { content: '.'; }
    40% { content: '..'; }
    60%, 100% { content: '...'; }
}

"""
# 注入 ECharts CDN 和自动渲染脚本
js_code = """
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<script>
(function() {
    function renderEcharts() {
        const containers = document.querySelectorAll('[data-echart-option]');
        containers.forEach(container => {
            if (container.__echart_rendered) return;
            const optionStr = container.getAttribute('data-echart-option');
            if (!optionStr) return;
            try {
                const option = JSON.parse(optionStr);
                if (typeof echarts !== 'undefined') {
                    const chart = echarts.init(container);
                    chart.setOption(option);
                    window.addEventListener('resize', () => chart.resize());
                    container.__echart_rendered = true;
                } else {
                    console.warn('ECharts not loaded');
                }
            } catch(e) {
                console.error('图表渲染错误', e);
            }
        });
    }

    // 将工具调用提示替换为"正在思考中"
    function replaceToolNoticesWithThinking() {
        const notices = document.querySelectorAll('.tool-call-notice');
        notices.forEach(notice => {
            // 创建"正在思考中"的占位元素
            const thinkingSpan = document.createElement('span');
            thinkingSpan.className = 'thinking-placeholder';
            thinkingSpan.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; color: #888; font-size: 13px; padding: 2px 0;';
            thinkingSpan.innerHTML = '<span style="display: inline-block; animation: pulse 1.2s ease-in-out infinite;">✨</span><span>正在思考<span style="display: inline-block; animation: dots 1.4s steps(4,end) infinite;">...</span></span>';

            // 替换节点
            if (notice.parentNode) {
                notice.parentNode.replaceChild(thinkingSpan, notice);
            }
        });
    }

    // 移除"正在思考中"占位符
    function removeThinkingPlaceholders() {
        const thinkingElements = document.querySelectorAll('.thinking-placeholder');
        thinkingElements.forEach(thinking => {
            // 使用 display: none 完全移除，不留空白
            thinking.style.display = 'none';
        });
    }

    // 初始渲染
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderEcharts);
    } else {
        renderEcharts();
    }

    // 监听动态变化
    const observer = new MutationObserver((mutations) => {
        renderEcharts();

        // 检查是否有新的非工具提示内容出现
        let hasNewContent = false;
        let hasTextContent = false;

        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    // 如果新增节点不是工具调用提示或思考占位，则触发清理
                    if (!node.classList || 
                        (!node.classList.contains('tool-call-notice') && 
                         !node.classList.contains('thinking-placeholder'))) {
                        hasNewContent = true;
                    }
                    // 检查是否是文本内容或包含文本的元素
                    if (node.textContent && node.textContent.trim().length > 0) {
                        hasTextContent = true;
                    }
                } else if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                    hasTextContent = true;
                    hasNewContent = true;
                }
            });
        });

        // 如果有新内容且存在工具提示，则替换为"正在思考中"
        if (hasNewContent && document.querySelectorAll('.tool-call-notice').length > 0) {
            setTimeout(replaceToolNoticesWithThinking, 800);
        }

        // 如果有新内容且存在思考占位符，则移除
        if (hasNewContent && document.querySelectorAll('.thinking-placeholder').length > 0) {
            setTimeout(removeThinkingPlaceholders, 300);
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
"""


def generate_chart_div(option):
    """生成纯 div 容器，不含 <script>，由前端统一渲染"""
    chart_id = f"echart_{random.randint(10000, 99999)}"
    option_json = json.dumps(option, ensure_ascii=False).replace("'", "&#39;")
    return f'<div id="{chart_id}" class="echart-container" data-echart-option=\'{option_json}\' style="width:100%; height:600px; margin-top:10px;"></div>'


def generate_response_and_chat(message, history):
    """
    流式响应，直接更新 chatbot 内容，图表嵌入 assistant 消息。
    :param message: 用户输入
    :param history: 聊天历史（list of dict），Gradio Chatbot 接受的格式
    :yield: (空字符串, 更新后的history)   # 第一个输出是清空输入框，第二个是聊天组件
    """
    if not message.strip():
        yield "", history
        return

    # 添加用户消息到历史
    history.append({"role": "user", "content": message})
    yield "", history
    # 添加"正在思考中"的 assistant 消息占位
    thinking_message = {"role": "assistant",
                        "content": "<div style='display: flex; align-items: center; gap: 10px; color: #888; font-size: 14px; padding: 4px 0;'><span style='display: inline-block; animation: pulse 1.2s ease-in-out infinite;'>✨</span><span>正在思考中<span style='display: inline-block; animation: dots 1.4s steps(4,end) infinite;'>...</span></span></div>"}
    history.append(thinking_message)
    yield "", history

    full_response = ""

    try:
        first_chunk = True
        for item in ask_stream(message):
            if isinstance(item, str):
                if first_chunk:
                    # 第一个文本片段到达时，替换掉"正在思考中"的提示
                    full_response = item
                    history[-1]["content"] = full_response
                    first_chunk = False
                else:
                    full_response += item
                    history[-1]["content"] = full_response
                yield "", history
            elif isinstance(item, dict) and item.get("has_chart"):
                # 图表 option 出现，生成 div 并追加到消息内容后面
                chart_div = generate_chart_div(item["chart_option"])
                full_response += chart_div
                history[-1]["content"] = full_response
                yield "", history
    except Exception as e:
        error_msg = "出错了，请刷新重试或联系管理员反馈问题"
        print(f"错误详情：{traceback.format_exc()}")
        history[-1]["content"] = error_msg
        yield "", history

    # 添加空的 assistant 消息占位
    # history.append({"role": "assistant", "content": ""})
    # full_response = ""
    #
    # try:
    #     for item in ask_stream(message):
    #         if isinstance(item, str):
    #             full_response += item
    #             history[-1]["content"] = full_response
    #             yield "", history
    #         elif isinstance(item, dict) and item.get("has_chart"):
    #             # 图表 option 出现，生成 div 并追加到消息内容后面
    #             chart_div = generate_chart_div(item["chart_option"])
    #             full_response += chart_div
    #             history[-1]["content"] = full_response
    #             yield "", history
    # except Exception as e:
    #     error_msg = "出错了，请刷新重试或联系管理员反馈问题"
    #     print(f"错误详情：{traceback.format_exc()}")
    #     history[-1]["content"] = error_msg
    #     yield "", history

def create_ui():

    with gr.Blocks(
            title="DeepAgent Chat",
            elem_classes="app",
    ) as ui:
        gr.Markdown("# <center>DeepAgent 智能助手</center>", elem_id="header")

        # 注意：sanitize_html=False 允许渲染 HTML，否则图表标签会被转义
        chatbot = gr.Chatbot(
            elem_id="chatbot",
            avatar_images=("images/user.svg", "images/robot.svg"),
            show_label=False,
            min_height=800,
            sanitize_html=False  # 关键参数！
        )

        with gr.Row(elem_classes=["input-row"]):
            msg = gr.Textbox(placeholder="输入消息...", show_label=False, container=False, elem_classes=["textbox"])
            submit_btn = gr.Button("发送", elem_classes=["button"])

        # 绑定事件：输出到 msg（清空）和 chatbot
        submit_btn.click(generate_response_and_chat, [msg, chatbot], [msg, chatbot])
        msg.submit(generate_response_and_chat, [msg, chatbot], [msg, chatbot])

    return ui


if __name__ == "__main__":
    ui = create_ui()
    ui.launch(server_name="0.0.0.0", server_port=8761, share=False, css=custom_css,head=js_code)