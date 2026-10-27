import re
from typing import List

# 标题里常见、但对搜索没有帮助的口语成分
STOP_PHRASES = [
    "为什么",
    "为何",
    "我劝你",
    "劝你",
    "千万别",
    "千万不要",
    "不要再",
    "别再",
    "你知道吗",
    "你必须知道",
    "必须知道",
    "一定要",
    "到底",
    "究竟",
    "竟然",
    "居然",
    "原来",
    "真相",
    "看完",
    "震惊",
    "怎么办",
    "如何",
    "怎样",
    "什么",
    "哪些",
    "这件事",
    "这些",
    "那些",
    "我们",
    "你们",
    "我",
    "你",
    "了",
    "吗",
    "呢",
    "吧",
    "啊",
    "的",
]

_PUNCT = re.compile(r"[\s\u3000，。！？、；：“”‘’（）《》【】\[\]()!?,.;:'\"|…—\-~·]+")

MAX_QUERIES = 3


def clean_topic(topic: str) -> str:
    """去掉口语成分与标点，得到较适合搜索的关键词串。"""
    text = topic or ""
    for phrase in sorted(STOP_PHRASES, key=len, reverse=True):
        text = text.replace(phrase, " ")
    text = _PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def rule_queries(topic: str) -> List[str]:
    """规则兜底：清洗后的关键词串 + 原题（去重）。"""
    queries: List[str] = []
    cleaned = clean_topic(topic)
    if len(cleaned.replace(" ", "")) >= 2:
        queries.append(cleaned)
    original = (topic or "").strip()
    if original and original not in queries:
        queries.append(original)
    return queries[:MAX_QUERIES]


def parse_queries(text: str) -> List[str]:
    """解析模型输出的搜索词（每行一个，允许列表符号）。"""
    queries: List[str] = []
    for line in (text or "").splitlines():
        s = re.sub(r"^\s*(?:[-*+]|\d+[\.、)])\s*", "", line).strip().strip("\"'“”")
        if not s or s.endswith(("：", ":")):
            continue
        if 2 <= len(s) <= 30 and s not in queries:
            queries.append(s)
        if len(queries) >= MAX_QUERIES:
            break
    return queries
