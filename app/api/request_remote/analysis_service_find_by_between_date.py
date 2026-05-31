import json

import requests
import hashlib
import os
from dotenv import load_dotenv
from langchain_core.tools import tool

from app.utils.compact_json import compact_json

load_dotenv()

@tool
def analysis_service_find_by_between_date(startDate="20250420", endDate="20260420", nodeId=os.getenv("brokerId")):
    """
    查询指定日期范围内的指定部门的历史盈亏数据。

    参数:
    - startDate: 开始日期，格式为 yyyymmdd
    - endDate: 结束日期，格式为 yyyymmdd
    - nodeId: 部门Id, 调用get_structure_tree工具查找用户指定部门对应的Id

    重要提示：
    - 此工具只需调用一次即可获取指定日期范围内的数据
    - 如果返回的数据为空或出错，请不要重复调用，直接使用已有信息回答用户
    - 获取到数据后应立即生成回复，不要再次调用此工具
    """
    # 配置参数
    remote_data_center_ip = os.getenv("remote_data_center_ip")
    api_url = f"http://{remote_data_center_ip}/qdpms/attributionAnalysisService/findByBetweenDate"
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
        "tagGroupId": "StructureTree",
        "brokerId": os.getenv("brokerId"),
        "nodeId": nodeId,
        "levelNodeId": os.getenv("brokerId"),
        #"upNodeId": os.getenv("brokerId"),
        #"fieldID": "14",
        "startDate": startDate,
        "endDate": endDate
    }
    response = requests.post(api_url, headers=headers, json=payload)
    try:
        data = response.json()  # 等价于 json.loads(response.text)
        """
        仅保留result中每个部门的：
            nodeId
            upNodeId
            fieldValue
            nodeName
            startDate
            endDate
            y
        """
        result = data.get("result", [])

        simplified_result = []
        for item in result:
            simplified_item = {
                "nodeId": item.get("nodeId"),
                "upNodeId": item.get("upNodeId"),
                "fieldValue": item.get("fieldValue"),
                "nodeName": item.get("nodeName"),
                "startDate": item.get("x")[0],
                "endDate": item.get("x")[-1],
                "days_value": item.get("y")  # 保留完整时间序列（如需再压缩可以继续优化）
            }
            simplified_result.append(simplified_item)

        # # 2. 调用清洗函数（清洗字典/列表）
        # cleaned_data = compact_json(data)
        #
        # # 3. 转回 JSON 字符串
        # cleaned_response = json.dumps(cleaned_data, ensure_ascii=False)
        #
        # print("原始响应大小:", len(response.text))
        # print("清洗后大小:", len(cleaned_response))
        #
        # return cleaned_response
        print(len(simplified_result))
        print(simplified_result)
        return {
            "result": simplified_result
        }
    except Exception as e:
        # 如果响应不是合法 JSON，直接返回原始文本
        return response.text


if __name__ == '__main__':
    print(analysis_service_find_by_between_date.invoke({}))