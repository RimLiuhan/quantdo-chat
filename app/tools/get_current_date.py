from datetime import datetime
from langchain_core.tools import tool


@tool
def get_current_date():
    """获取当日日期，返回格式为 YYYYMMDD"""
    today = datetime.now().strftime("%Y%m%d")
    return today


if __name__ == '__main__':
    print(get_current_date.invoke({}))
