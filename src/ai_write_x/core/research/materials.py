from dataclasses import dataclass, field
from typing import Dict, List

NO_MATERIALS = "（无可用参考素材，请基于常识与逻辑原创写作，不要编造具体数据、机构或人物言论）"


@dataclass
class Materials:
    """写作前收集到的参考素材。"""

    source_type: str = "none"  # none | search | reference
    items: List[Dict] = field(default_factory=list)
    queries: List[str] = field(default_factory=list)
    reference_ratio: float = 0.0

    @property
    def empty(self) -> bool:
        return not self.items

    def to_prompt_block(self) -> str:
        if self.empty:
            return NO_MATERIALS

        if self.source_type == "reference":
            lines = [
                f"以下是用户指定的参考文章（借鉴比例约 {self.reference_ratio:.0%}），"
                "可借鉴观点与结构，但必须用自己的语言重写，不得大段照搬：",
                "",
            ]
        else:
            lines = [
                "以下是搜索得到、经过相关性筛选的参考素材，仅作可选参考：",
                "- 与话题无关或可信度存疑的条目必须忽略，不得为了引用而引用",
                "- 引用数据时以素材为准，没有可靠来源的数字不要编造",
                "",
            ]

        for i, item in enumerate(self.items, 1):
            title = (item.get("title") or "无标题")[:100]
            lines.append(f"[{i}] {title}")
            if item.get("pub_time"):
                lines.append(f"发布时间：{item['pub_time']}")
            if item.get("source_name"):
                lines.append(f"来源：{item['source_name']}")
            body = (item.get("content") if self.source_type == "reference" else "") or item.get(
                "abstract", ""
            )
            limit = 800 if self.source_type == "reference" else 300
            body = (body or "").strip()
            if len(body) > limit:
                body = body[:limit] + "..."
            if body:
                lines.append(f"内容：{body}")
            lines.append("")
        return "\n".join(lines).strip()
