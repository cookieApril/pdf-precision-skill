import re
from decimal import Decimal, InvalidOperation

UNIT_SCALE = {
    "元": Decimal("1"), "人民币元": Decimal("1"),
    "万元": Decimal("10000"), "万人民币": Decimal("10000"),
    "亿元": Decimal("100000000"), "亿人民币": Decimal("100000000"),
    "%": Decimal("0.01"), "percent": Decimal("0.01"),
}

def normalize_number(text):
    """Extract and normalize the first numeric expression in text."""
    if text is None:
        return None
    raw = str(text)
    s = raw.replace(",", "").replace("，", "")
    negative_by_paren = bool(re.search(r"\(\s*[-+]?\d", s))
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        value = Decimal(m.group(0))
        if negative_by_paren and value > 0:
            value = -value
    except InvalidOperation:
        return None
    for unit, scale in UNIT_SCALE.items():
        if unit in s:
            return float(value * scale)
    return float(value)

def normalize_metric_name(text):
    if not text:
        return ""
    aliases = {
        "营业收入": ["收入", "营收", "营业总收入"],
        "净利润": ["归母净利润", "利润", "净收益"],
        "研发费用": ["研发投入", "研发支出"],
        "补贴上限": ["最高补贴", "资助上限", "补助上限"],
    }
    t = str(text).strip()
    for canon, vals in aliases.items():
        if t == canon or any(v in t for v in vals):
            return canon
    return t
