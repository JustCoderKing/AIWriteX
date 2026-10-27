import re
from typing import Dict, List

from src.ai_write_x.config.config import Config
from src.ai_write_x.core.base_framework import (
    AgentConfig,
    ContentType,
    TaskConfig,
    WorkflowConfig,
    WorkflowType,
)
from src.ai_write_x.core.research.materials import Materials
from src.ai_write_x.core.research.queries import parse_queries, rule_queries
from src.ai_write_x.core.research.relevance import filter_relevant, rank_items
from src.ai_write_x.utils import log

MODES = ("auto", "always", "off")


def _run_single_task(name: str, role: str, description: str, inputs: Dict) -> str:
    from src.ai_write_x.core.content_generation import ContentGenerationEngine

    workflow = WorkflowConfig(
        name=name,
        description=role,
        workflow_type=WorkflowType.SEQUENTIAL,
        content_type=ContentType.ARTICLE,
        agents=[
            AgentConfig(
                role=role,
                name="worker",
                goal=role,
                backstory="你只按要求输出结果，不做解释",
                tools=[],
                max_iter=3,
                memory=False,
            )
        ],
        tasks=[
            TaskConfig(
                name=f"{name}_task",
                description=description,
                agent_name="worker",
                expected_output="按格式输出的结果",
            )
        ],
    )
    result = ContentGenerationEngine(workflow).execute_workflow(
        {**inputs, "parse_result": False, "content_format": "markdown"}
    )
    return result.content or ""


def build_queries(topic: str, use_llm: bool) -> List[str]:
    if use_llm:
        try:
            text = _run_single_task(
                "research_queries",
                "搜索关键词策划",
                """把文章题目「{topic}」改写成 2～3 个适合在百度等搜索引擎检索资料的关键词组合。
要求：
- 每行一个，只输出关键词组合本身，不要编号以外的任何说明
- 去掉口语和情绪化表达，保留核心概念，可补充「数据」「研究」「案例」等检索词
- 每个 4～20 个字""",
                {"topic": topic},
            )
            queries = parse_queries(text)
            if queries:
                return queries
            log.print_log("搜索词改写结果为空，改用规则提取", "warning")
        except Exception as e:
            log.print_log(f"搜索词改写失败，改用规则提取: {e}", "warning")
    return rule_queries(topic)


def llm_relevance_filter(topic: str, items: List[Dict]) -> List[Dict]:
    """让模型判断哪些条目与题目相关；失败时原样返回。"""
    if not items:
        return items
    listing = "\n".join(
        f"{i}. {(it.get('title') or '')[:80]} —— {(it.get('abstract') or '')[:120]}"
        for i, it in enumerate(items, 1)
    )
    try:
        text = _run_single_task(
            "research_relevance",
            "资料相关性审核",
            """文章题目：「{topic}」
以下是搜索结果列表：
{listing}

判断哪些条目能为这篇文章提供有用的事实、数据或观点。
只输出相关条目的编号，用英文逗号分隔（例如 1,3,4）；全部不相关则输出 0。""",
            {"topic": topic, "listing": listing},
        )
        picked = {int(n) for n in re.findall(r"\d+", text)}
        if picked == {0}:
            return []
        kept = [it for i, it in enumerate(items, 1) if i in picked]
        return kept if picked else items
    except Exception as e:
        log.print_log(f"模型相关性判断失败，保留规则筛选结果: {e}", "warning")
        return items


def _reference_materials(topic: str, urls: List[str], reference_ratio: float) -> Materials:
    from src.ai_write_x.tools import search_template

    log.print_log("开始提取参考链接中的文章信息，请耐心等待...")
    extracted = search_template.extract_urls_content(urls, topic)
    items = []
    if search_template.validate_search_result(
        extracted, min_results=1, search_type="reference_article"
    ):
        items = [
            it
            for it in extracted.get("results") or []
            if (it.get("title") or "").strip() and (it.get("content") or "").strip()
            and not (it.get("content") or "").startswith("无法提取内容")
        ]
    if not items:
        log.print_log("参考链接未提取到有效内容，将原创写作", "warning")
    return Materials(source_type="reference", items=items, reference_ratio=reference_ratio)


def _search(queries: List[str]) -> List[Dict]:
    from src.ai_write_x.tools import search_template

    sites = [s for s in Config.get_instance().search_sites if s.get("enabled")]
    if not sites:
        log.print_log("没有启用的搜索网站，跳过搜索", "warning")
        return []
    collected: List[Dict] = []
    for query in queries:
        log.print_log(f"搜索：{query}")
        collected.extend(search_template.search_enabled_sites(sites, query))
    return collected


def gather_materials(topic: str, urls: List[str] | None = None, reference_ratio: float = 0.0) -> Materials:
    """写作前收集素材：参考链接优先；否则按搜索模式检索并做相关性筛选。"""
    cfg = Config.get_instance().research_config
    mode = cfg.get("mode", "auto")
    if mode not in MODES:
        mode = "auto"

    log.print_log("[PROGRESS:SEARCH:START]", "internal")
    try:
        if urls:
            return _reference_materials(topic, urls, reference_ratio)

        if mode == "off":
            log.print_log("搜索模式为 off，不搜索，直接原创写作")
            return Materials()

        queries = build_queries(topic, bool(cfg.get("llm_query_rewrite", True)))
        log.print_log(f"搜索词：{' | '.join(queries)}")
        raw = _search(queries)
        if not raw:
            log.print_log("未获取到搜索结果，将原创写作", "warning")
            return Materials(source_type="search", queries=queries)

        max_items = int(cfg.get("max_materials", 8) or 8)
        threshold = float(cfg.get("relevance_threshold", 0.25))
        relevant = filter_relevant(raw, topic, queries, threshold, max_items)
        for score, item in relevant:
            log.print_log(f"相关 {score:.2f} | {(item.get('title') or '')[:50]}")
        items = [item for _, item in relevant]
        log.print_log(f"相关性筛选：{len(raw)} 条结果保留 {len(items)} 条（阈值 {threshold}）")

        if items and cfg.get("llm_relevance_check", False):
            before = len(items)
            items = llm_relevance_filter(topic, items)
            log.print_log(f"模型相关性判断：{before} 条保留 {len(items)} 条")

        if not items and mode == "always":
            items = [item for _, item in rank_items(raw, topic, queries)[:max_items]]
            log.print_log("搜索模式为 always，无相关结果时仍使用排名靠前的结果", "warning")

        if not items:
            log.print_log("搜索结果与题目均不相关，将原创写作", "warning")
        return Materials(source_type="search", items=items, queries=queries)
    except Exception as e:
        log.print_log(f"素材收集失败，将原创写作: {e}", "warning")
        return Materials()
    finally:
        log.print_log("[PROGRESS:SEARCH:END]", "internal")
