import requests
import hashlib
import os
from dotenv import load_dotenv
from langchain_core.tools import tool

from app.utils.compact_json import compact_json

load_dotenv()

@tool
def get_structure_tree():
    """
    查询组织架构,不需要参数,直接调用即可获取完整架构树数据。

    重要提示：
    - 此工具只需调用一次即可获取完整的组织架构数据
    - 如果返回的数据为空或出错，请不要重复调用，直接使用已有信息回答用户
    - 获取到数据后应立即生成回复，不要再次调用此工具
    """
    # 配置参数
    remote_data_center_ip = os.getenv("remote_data_center_ip")
    api_url = f"http://{remote_data_center_ip}/qdpms/structureTreeService/getStructureTree"
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
        "brokerId": os.getenv("brokerId"),
        "nodeTypeList": [
            "0",
            "1",
            "3"
        ],
        "tagGroupId": "StructureTree",
        "isRight": "0"
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        data = response.json()
        cleaned_data = compact_json(data)
        print(cleaned_data)
        return cleaned_data
    except Exception as e:
        print(f"Error: {e}")
        return "获取组织架构数据出错，请稍后再试。"

if __name__ == '__main__':
    print(get_structure_tree.invoke({}))