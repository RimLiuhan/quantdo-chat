import json
from typing import Any, Union

def compact_json(data: Any) -> Any:
    """
    递归过滤掉 None、空字符串、空列表、空字典，返回精简后的数据。
    保留数值 0、False 等有意义的假值。
    """
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            # 跳过值为 None 的键
            if v is None:
                continue
            # 递归处理嵌套结构
            compacted_v = compact_json(v)
            # 如果递归后结果是空字典、空列表、空字符串，则跳过该键
            if (isinstance(compacted_v, dict) and not compacted_v) or \
               (isinstance(compacted_v, list) and not compacted_v) or \
               (isinstance(compacted_v, str) and compacted_v == ""):
                continue
            new_dict[k] = compacted_v
        return new_dict
    elif isinstance(data, list):
        new_list = []
        for item in data:
            compacted_item = compact_json(item)
            # 跳过 None、空字典、空列表、空字符串
            if compacted_item is None:
                continue
            if isinstance(compacted_item, dict) and not compacted_item:
                continue
            if isinstance(compacted_item, list) and not compacted_item:
                continue
            if isinstance(compacted_item, str) and compacted_item == "":
                continue
            new_list.append(compacted_item)
        return new_list
    else:
        # 保留数值 0、False、空字符串已经在上层跳过，这里直接返回
        return data