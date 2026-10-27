import re
from typing import Dict, Iterable, List, Set, Tuple

from src.ai_write_x.core.research.queries import clean_topic

_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
_ASCII_WORD = re.compile(r"[a-zA-Z0-9]{2,}")


def terms(text: str) -> Set[str]:
    """中文按两字片段、英文数字按单词切分。"""
    result: Set[str] = set()
    for run in _CJK_RUN.findall(text or ""):
        if len(run) == 1:
            continue
        result.update(run[i : i + 2] for i in range(len(run) - 1))
    result.update(w.lower() for w in _ASCII_WORD.findall(text or ""))
    return result


def coverage(reference: Set[str], text_terms: Set[str]) -> float:
    if not reference:
        return 0.0
    return len(reference & text_terms) / len(reference)


def item_text(item: Dict) -> str:
    return f"{item.get('title', '')} {item.get('abstract', '')}"


def relevance_score(item: Dict, references: Iterable[Set[str]]) -> float:
    """取各参照（题目、每个搜索词）覆盖率的最大值。"""
    text_terms = terms(item_text(item))
    return max((coverage(ref, text_terms) for ref in references if ref), default=0.0)


def _dedupe_key(item: Dict) -> str:
    return (item.get("url") or "").strip() or (item.get("title") or "").strip()


def rank_items(items: List[Dict], topic: str, queries: List[str]) -> List[Tuple[float, Dict]]:
    """去重并按相关度降序排列。"""
    references = [terms(clean_topic(topic))] + [terms(q) for q in queries]
    seen: Set[str] = set()
    ranked: List[Tuple[float, Dict]] = []
    for item in items:
        key = _dedupe_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        ranked.append((relevance_score(item, references), item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return ranked


def filter_relevant(
    items: List[Dict],
    topic: str,
    queries: List[str],
    threshold: float,
    max_items: int,
) -> List[Tuple[float, Dict]]:
    ranked = rank_items(items, topic, queries)
    return [pair for pair in ranked if pair[0] >= threshold][:max_items]
