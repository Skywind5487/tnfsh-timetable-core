"""
📊 prefix / suffix / target 狀態組合表

| prefix | suffix | target | 類型代號 | 範例                         |
|--------|--------|--------|----------|------------------------------|
| ❌     | ❌     | ❌     | T7       | T                            |
| ✅     | ❌     | ❌     | T6a      | TTim                         |
| ❌     | ❌     | ✅     | T6b      | T王大明                       |
| ❌     | ✅     | ❌     | fallback | T03                          |
| ✅     | ✅     | ❌     | T5       | TJA04                        |
| ✅     | ❌     | ✅     | T6c/T6d  | TNicole魏 / T王大明Nicole     |
| ❌     | ✅     | ✅     | T4-like  | T03王大明                     |
| ✅     | ✅     | ✅     | T4       | TJA04王大明                   |
"""

"""
| 代號 | 形式                    | 範例           |
| ---- | ---------------------- | -------------- |
| T0   | 空字串                  | ""             |
| T1a  | zh_name                | 王大明          |
| T1b  | en_name                | Tim            |
| T2   | ID + zh_name / en_name | JA04王大明     |
| T3   | ID                     | JA04           |
| T4   | T + ID + zh_name       | TJA04王大明    |
| T5   | T + ID                 | TJA04          |
| T6a  | T + en_name            | TTim           |
| T6b  | T + zh_name            | T王大明         |
| T6c  | T + en_name + zh_name  | TNicole魏      |
| T6d  | T + zh_name + en_name  | T王大明Nicole   |
| T7   | T                      | T              |
| T8   | T + 非法 ID 組合        | T@zhen         |

| C0   | 空字串                   | ""              |
| C1   | class_code（3碼）      | 101            |
| C2   | 重複 class_code         | 110123123      |
| C3   | class_code（6碼）      | 110123         |
| C4   | C + 重複 class_code     | C110123123     |
| C5   | C + class_code（6碼）   | C110123        |
| C6   | C + class_code（3碼）   | C101           |
| C7   | C                      | C              |
| C8   | 非法 C 組合             | Czzzzz         |
"""


import regex
from typing import Optional, Literal, List
from pydantic import BaseModel
from tnfsh_timetable_core import TNFSHTimetableCore

core = TNFSHTimetableCore()
logger = core.get_logger(logger_level="DEBUG")

# 🔍 識別結果的結構：教師或班級，其類型、代號與對應目標（如姓名或班級號）
class IdentificationResult(BaseModel):
    role: Literal["teacher", "class"]  # 識別為教師或班級
    match_case: Optional[Literal[
        "T1a", "T1b", "T2", "T3", "T4", "T5", "T6a", "T6b", "T6c", "T6d", "fallback",
        "C1", "C2", "C3", "C4", "C5", "C6"
    ]] = None  # 類型代號（如 T1, T2, C1, C2 等）
    target: Optional[str] = None          # 主要名稱（如教師姓名或班級號）
    ID: Optional[str] = None              # 識別碼（如教師代號或班級ID）


# 🌟 主函式：根據輸入文字判斷其類型並回傳識別結果
def identify_type(text: str, 
                  class_code_len: int = 3, 
                  class_id_prefix_len: int = 3,
                  base_url: str = "http://w3.tnfsh.tn.edu.tw/deanofstudies/course/"
) -> Optional[IdentificationResult]:
    """
    根據輸入文字自動判斷其為教師或班級，並回傳識別結果。

    Args:
        text (str): 欲識別的文字，可為教師姓名、教師代碼、班級代碼等。
        class_code_len (int, optional): 班級代碼長度，預設為 3。

    可接受的輸入：
        - 教師姓名（純中文或純英文，如 "王大明"、"Tim"）
        - 教師代碼（如 "TJA04"、"JA04王大明"、"T王大明Nicole"）
        - 班級代碼（如 "C108119"、"119"、"C110123123"）
        - 其他常見的教師/班級編碼組合

    處理流程：
        1. 先判斷是否為純英文或純中文（教師名）。
        2. 若有 T/C 前綴，依據結構拆解 prefix/suffix/target，判斷教師或班級型態。
        3. 若無前綴，嘗試以常見教師/班級編碼規則比對。
        4. 若有非法符號，僅警告不阻斷。
        5. 無法識別時回傳 None。

    Returns:
        IdentificationResult | None: 識別結果，包含角色（teacher/class）、類型代號（如 T1a、C5）、主要名稱、ID 等欄位。
        若無法識別，回傳 None。
    """
    # 預處理網址與非法符號
    origin_text_len = len(text)
    is_url = False
    if not text or origin_text_len < 2:
        return None  # T0, C0, T7, C7: 空字串或單字元無效輸入
    base_url = base_url.replace('http://', '').replace('https://', '')
    text = text.replace('http://', '').replace('https://', '')
    text = text.replace(base_url, '').replace('.html', '').replace('.HTML', '')
    if len(text) != origin_text_len:
        is_url = True

    # 先檢查非法符號（非英數/漢字），僅警告不阻斷
    if regex.search(r'[^A-Za-z0-9\p{Han}]', text):
        logger.warning(f"⚠️ 輸入 `{text}` 含有非法符號，將略過處理或僅保留有效部分")

    # 提前判斷 C5/T5 並處理 URL warning
    is_c5 = text.startswith('C') and regex.fullmatch(fr'\d{{{class_code_len * 2}}}', text[1:])
    is_t5 = text.startswith('T') and regex.match(r'^([A-Za-z]+)(\d+)$', text[1:])
    if is_url and not (is_c5 or is_t5):
        logger.warning(f"⚠️ `{text}` is not a valid url for this type")

    # T1a: 純英文教師名（如 Tim）
    if regex.fullmatch(r'[A-Za-z]+', text):
        return IdentificationResult(role="teacher", match_case="T1a", target=text)
    # T1b: 純中文教師名（如 王大明）
    if regex.fullmatch(r'\p{Han}+', text):
        return IdentificationResult(role="teacher", match_case="T1b", target=text)

    # 進入 T/C 前綴分支
    role = text[0]
    body = text[1:]  # 去掉 T / C 前綴

    if role == 'T':
        # 解析 T 開頭的教師代碼，分 prefix(英文)、suffix(數字)、target(姓名)
        match = regex.match(r'^([A-Za-z]*)(\d*)([A-Za-z\p{Han}]*)$', body)
        if not match:
            return None
        prefix, suffix, target = match.groups()
        match_case = None
        # 依據 prefix/suffix/target 組合判斷教師類型
        match (bool(prefix), bool(suffix), bool(target)):
            case (True, True, True):  # T4：T + ID + 中文名
                match_case = "T4"
                if regex.fullmatch(r'\p{Han}+', target):
                    return IdentificationResult(role="teacher", match_case=match_case, target=target, ID=f"T{prefix}{suffix}")
            case (True, True, False):  # T5：T + ID
                match_case = "T5"
                return IdentificationResult(role="teacher", match_case=match_case, target=None, ID=f"T{prefix}{suffix}")
            case (False, True, False):  # fallback：只有T為prefix的ID
                match_case = "fallback"
                return IdentificationResult(role="teacher", match_case=match_case, target=None, ID=f"T{'T'}{suffix}")
            case (True, False, False):  # T6a：T + 英文名
                match_case = "T6a"
                if regex.fullmatch(r'[A-Za-z]+', prefix):
                    return IdentificationResult(role="teacher", match_case=match_case, target=prefix, ID=None)
                raise KeyError(f"❌ 無法識別的教師代碼：{prefix}")
            case (False, False, True):  # T6b / T6d：T + 中文名 或混合
                match_case = "T6b/T6d"
                if regex.fullmatch(r'\p{Han}+', target):
                    return IdentificationResult(role="teacher", match_case="T6b", target=target, ID=None)
                # 混合中英文，僅保留英文
                if regex.search(r'\p{Han}+', target) and regex.search(r'[A-Za-z]+', target):
                    zh = ''.join(regex.findall(r'\p{Han}+', target))
                    en = ''.join(regex.findall(r'[A-Za-z]+', target))
                    if zh and en:
                        logger.warning(f"⚠️ 教師代碼 `T{target}` 為 T6d，僅保留英文 `{en}`")
                        return IdentificationResult(role="teacher", match_case="T6d", target=en, ID=None)
            case (True, False, True):  # T6c：T + 英文名 + 中文名 → 保留英文
                match_case = "T6c/T6d"
                if regex.fullmatch(r'\p{Han}+', target) and regex.fullmatch(r'[A-Za-z]+', prefix):
                    logger.warning(f"⚠️ 教師代碼 `{prefix + target}` 中出現中英文混合（T6c），僅保留英文 `{prefix}` 當作姓名")
                    return IdentificationResult(role="teacher", match_case="T6c", target=prefix, ID=None)
                if regex.fullmatch(r'\p{Han}+', prefix) and regex.fullmatch(r'[A-Za-z]+', target):
                    logger.warning(f"⚠️ 教師代碼 `{prefix + target}` 中出現中文+英文混合（T6d），僅保留英文 `{target}` 當作姓名")
                    return IdentificationResult(role="teacher", match_case="T6d", target=target, ID=None)
                if not regex.fullmatch(r'[A-Za-z]*', prefix):
                    raise KeyError(f"❌ 教師代碼 `{prefix + target}` 中 prefix 含非法字元，無法識別")

    elif role == 'C':
        # 處理 C 開頭的班級代碼
        # C5: C + 3碼prefix + 3碼class_code（如 C110123）
        if regex.fullmatch(fr'\d{{{class_code_len * 2}}}', body):
            return IdentificationResult(role="class", match_case="C5", target=body[-class_code_len:], ID=f"C{body[:class_code_len*2]}")
        # C6: C + 3碼class_code（如 C101）→ 直接返回
        if regex.fullmatch(fr'\d{{{class_code_len}}}', body):
            return IdentificationResult(role="class", match_case="C6", target=body, ID=None)
        # C4: C + 重複 class_code（如 C110123123 C + prefix + suffix + class)code 其中suffix就是 class_code）→ 拆解後三段檢查
        match = regex.fullmatch(fr'(\d+)(\d{{{class_code_len}}})(\d{{{class_code_len}}})', body)
        if match:
            front, mid, tail = match.groups()
            if mid != tail:
                logger.warning(f"❌ C4 格式錯誤：後兩段 `{mid}` 與 `{tail}` 不一致，將以 `{mid}` 為目標")
            # C110123123 → ID = C110123, target = 123
            return IdentificationResult(role="class", match_case="C4", target=tail, ID=f"C{front}{mid}")
        # C8: 非法 C 組合（fallback）
        logger.warning(f"⚠️ 班級代碼 `C{body}` 無法識別，視為非法 C8")
        return None

    else:
        # C8: 非法 C 組合（C 開頭但不是合法班級格式）
        if text.startswith('C'):
            logger.warning(f"⚠️ 班級代碼 `{text}` 無法識別，視為非法 C8")
            return None
        # T2: 英文+數字+中文名
        m = regex.fullmatch(r'([A-Za-z]+\d+)(\p{Han}+)', text)
        if m:
            return IdentificationResult(role="teacher", match_case="T2", target=m.group(2), ID=f"T{m.group(1)}")
        # T3: 英文+數字
        if regex.fullmatch(r'[A-Za-z]+\d+', text):
            return IdentificationResult(role="teacher", match_case="T3", target=None, ID=f"T{text}")
        # C1: 3碼數字
        if regex.fullmatch(fr'\d{{{class_code_len}}}', text):
            return IdentificationResult(role="class", match_case="C1", target=text, ID=None)
        # C3: 6碼數字
        if regex.fullmatch(fr'\d{{{class_code_len * 2}}}', text):
            return IdentificationResult(role="class", match_case="C3", target=text[-class_code_len:], ID=f"C{text}")
        # C2: 重複 class_code
        m = regex.fullmatch(fr'(\d+)(\d{{{class_code_len}}})(\d{{{class_code_len}}})', text)
        if m:
            a, b, c = m.groups()
            if b != c:
                logger.warning(f"❌ C2 格式錯誤：後兩段 `{b}` 與 `{c}` 不一致，將以 `{b}` 為目標")
            return IdentificationResult(role="class", match_case="C2", target=c, ID=f"C{a}{b}")
        # T8: 非法 T 組合
        if text.startswith('T'):
            logger.warning(f"⚠️ 教師代碼 `{text}` 無法識別，視為非法 T8")
            return None
    return None


from tnfsh_timetable_core.index.models import TargetInfo, FullIndexResult

def get_fuzzy_target_info(text: str, source_index: FullIndexResult) -> TargetInfo| List[str]| None:
    """
    模糊查詢目標資訊。

    支援多種編碼、前綴、ID、姓名等組合。
    只需要 FullIndexResult 的 id_to_info、target_to_unique_info 和 target_to_conflicting_ids。

    Args:
        text (str): 欲查詢的文字，可為教師姓名、教師代碼、班級代碼等。
        source_index (FullIndexResult): 索引資料，僅需 id_to_info、target_to_unique_info、target_to_conflicting_ids。

    查詢流程：
        1. 先直接查 target_to_unique_info（唯一對應）
        2. 再查 target_to_conflicting_ids（有衝突的名稱）
        3. 用 identify_type 分析後，依 ID 與 target 再查
        4. 若 TTim（純英文名）嘗試去掉 T 前綴再查
        5. 全部查不到則丟出 KeyError

    Returns:
        TargetInfo | List[str] | None: 查到則回傳目標資訊或衝突 ID 列表，查不到丟出 KeyError。
    """
    result = None

    # 1. 直接查唯一 target
    result = source_index.target_to_unique_info.get(text)
    if result:
        return result
    # 2. 查有衝突的 target
    result = source_index.target_to_conflicting_ids.get(text)
    if result:
        return result

    # 3. 用識別規則分析
    identify_result = identify_type(text)
    if not identify_result:
        raise KeyError(f"無法識別的輸入：{text}")

    # 3a. 先用 ID 查
    if identify_result.ID:
        id = identify_result.ID
        result = source_index.id_to_info.get(id)
        if result:
            return result
    # 3b. 再用 target 查
    if identify_result.target:
        target = identify_result.target
        result = source_index.target_to_unique_info.get(target)
        if result:
            return result
        result = source_index.target_to_conflicting_ids.get(target)
        if result:
            return result
        # 4. 若 T1a（純英文名）嘗試去掉 T 前綴再查
        if identify_result.match_case == "T1a":
            target = target[1:] if target.startswith('T') else target
            result = source_index.target_to_unique_info.get(target)
            if result:
                return result
            result = source_index.target_to_conflicting_ids.get(target)
            if result:
                return result
    # 5. 全部查不到
    if not result:
        raise KeyError(f"無法找到對應的目標資訊：{text} (ID: {identify_result.ID}, Target: {identify_result.target})")


if __name__ == "__main__":
    examples = [
        "",        # T0 / C0
        "王大明",   # T1a
        "Tim",     # T1b
        "Cindy",  # T1b
        "JA04王大明",  # T2
        "JA04",     # T3
        "TJA04王大明",  # T4
        "TJA04",     # T5
        "TTim",      # T6a 因為純英文，其實會視為 T1b 得到 TTim 
        "T王大明",    # T6b
        "TNicole魏", # T6c
        "T王大明Nicole",  # T6d
        "T",         # T7
        "T@zhen",     # T8
        "T03" ,  # fallback
        "TT03", # fallback
        "Tzhen@",  # T8
        "101",       # C1
        "110123123", # C2
        "110123",    # C3
        "C110123123",# C4
        "C110123",   # C5
        "C101",      # C6
        "C",         # C7
        "Czzzzz"      # C8 因為純英文，其實會視為T1b，這也是沒辦法的事
    ]

    for example in examples:
        try:
            result = identify_type(example)
            print(f"{example!r:20} → {result} type={getattr(result, 'type', None) if result else None}")
        except Exception as e:
            print(f"{example!r:20} → ❌ {e}")