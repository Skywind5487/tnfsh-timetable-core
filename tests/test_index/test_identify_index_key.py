import pytest
from tnfsh_timetable_core.index.identify_index_key import identify_type
import itertools

base_url = "w3.tnfsh.tn.edu.tw/deanofstudies/course/"
roles = ["T", "C"]
prefixes = ["JA", "T", "103"]  # 英文ID/英文名/中文名
suffixes = ["04", "119", ""]
en_names = ["Tim", "Cindy", "Nicole"]
zh_names = ["王大明", "魏"]
class_codes = ["101", "102", "103", "104", "105", "106", "107", "108", "109", "110"]
html_exts = ["", ".html", ".HTML"]

def build_test_cases():
    test_inputs = set()
    # 三元素有/無排列組合
    for role in roles:
        for prefix in prefixes:
            for suffix in suffixes:
                for en in en_names:
                    for zh in zh_names:
                        for cls in class_codes:
                            for ext in html_exts:
                                # 產生所有有/無組合
                                for presence in itertools.product([en, ""], [zh, ""], [cls, ""]):
                                    # 跳過三個都空的情況
                                    if not any(presence):
                                        continue
                                    # 對有值的部分做所有排列
                                    non_empty = [x for x in presence if x]
                                    for perm in set(itertools.permutations(non_empty)):
                                        body = f"{prefix}{suffix}{''.join(perm)}"
                                        url = f"http://{base_url}{role}{body}{ext}"
                                        test_inputs.add(url)
                                        code = f"{role}{body}"
                                        test_inputs.add(code)
    # 再加上一些單純的 base_url + 代碼
    for code in ["TJA04", "C110119", "T王大明", "C101", "TNicole魏", "T王大明Nicole"]:
        for ext in html_exts:
            test_inputs.add(f"http://{base_url}{code}{ext}")
            test_inputs.add(f"{code}{ext}")
    return sorted(test_inputs)

@pytest.mark.parametrize("example", build_test_cases())
def test_identify_type(example):
    result = identify_type(example)
    # 只要不丟出例外就算通過，並格式化輸出
    if result:
        print(f"\n{example:30} | {result.role:7} | {result.match_case or '-':6} | {str(result.target)[:8]:8} | {str(result.ID)[:10]:10} | {getattr(result, 'type', None)}")
    else:
        print(f"\n{example:30} | {'-':7} | {'-':6} | {'-':8} | {'-':10} | -")
