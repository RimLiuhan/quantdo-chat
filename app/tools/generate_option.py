from langchain_core.tools import tool
from typing import Dict, Any
import json

@tool
def send_chart_option(option: str) -> str:
    """
     调用此工具来生成并展示一个数据图表。
    【重要】当用户明确要求"画图"、"展示图表"、"看趋势"或任何需要可视化的场景时，你必须调用此工具。
    如果只是需要文字说明，则不需要调用此工具。
    树状图要注意合理布局，避免节点和节点靠得太近发生重叠，可缩放拖动查看整张图表。

    Args:
        option: 完整的 ECharts option 对象，必须是合法的 JSON 格式字符串。

    Returns:
        确认信息（不会显示给用户）。
    """
    # 工具本身无需实现任何逻辑
    try:
        if isinstance(option, str):
            json.loads(option)  # 验证是否为有效 JSON
        return "图表配置已接收"
    except json.JSONDecodeError:
        return "错误：提供的 option 不是有效的 JSON 格式"
