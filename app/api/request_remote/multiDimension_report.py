import json

import requests
import hashlib
import os
from dotenv import load_dotenv
from langchain_core.tools import tool

from app.utils.compact_json import compact_json

load_dotenv()

@tool
def multiDimension_report(dateType: str="D", date: str="20250919"):
    """
    获取指定日期的用户账户/策略盈亏分析报告。

    参数:
    - dateType: 日期类型,日-'D',月-'M',年-'Y'
    - date: 日期，单日格式为 yyyymmdd,月格式为yyyymm,年格式为yyyy

    重要提示：
    - 此工具只需调用一次即可获取指定日期的盈亏分析数据
    - 如果返回的数据为空或出错，请不要重复调用，直接使用已有信息回答用户
    """
    # 配置参数
    remote_data_center_ip = os.getenv("remote_data_center_ip")
    api_url = f"http://{remote_data_center_ip}/qdpms/multiDimensionReportRest/futureProfitlossReport"
    apikey = os.getenv("api_key")
    secrekey = os.getenv("secrekey")
    client_ip = os.getenv("client_ip")

    # 计算 sn
    raw_str = secrekey + client_ip                    # 字符串拼接
    utf8_bytes = raw_str.encode('utf-8')              # 转 UTF-8
    sn = hashlib.md5(utf8_bytes).hexdigest()          # 计算 MD5，得到32位小写hex

    # 构造请求头
    headers = {
        "apikey": apikey,
        "sn": sn,
        "Content-Type": "application/json"            # 根据接口要求，可能是其他类型
    }

    # 构造请求体（示例）
    payload = {
        "priceType": "2",
        "instClientID": os.getenv("brokerId"),
        "dateType": dateType,
        "settleDate": date
    }

    response = requests.post(api_url, headers=headers, json=payload)
    try:
        data = response.json()  # 等价于 json.loads(response.text)
        cleaned_data = compact_json(data)["result"]
        cleaned_response = json.dumps(cleaned_data, ensure_ascii=False)
        print("原始响应大小:", len(response.text))
        print("清洗后大小:", len(cleaned_response))
        return cleaned_response
    except Exception as e:
        # 如果响应不是合法 JSON，直接返回原始文本
        return response.text




if __name__ == '__main__':
    print(multiDimension_report.invoke({}))