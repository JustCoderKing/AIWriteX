from typing import Any, Dict, List, Optional

from src.ai_write_x.config.config import Config
from src.ai_write_x.core.base_framework import (
    AgentConfig,
    ContentResult,
    ContentType,
    TaskConfig,
    WorkflowConfig,
    WorkflowType,
)
from src.ai_write_x.core.content_generation import ContentGenerationEngine
from src.ai_write_x.core.research import Materials, gather_materials
from src.ai_write_x.core.writing.hooks import DEFAULT_HOOK, HOOK_TYPES
from src.ai_write_x.core.writing.models import OutlineResult
from src.ai_write_x.core.writing.outline_parser import parse_outline
from src.ai_write_x.core.writing.qc import check_article
from src.ai_write_x.utils import log

# CrewAI 用 str.format 填充任务描述，素材与大纲等外部文本一律经输入参数传入
NO_OUTLINE = "（无大纲，请自行规划清晰结构）"


class WritingPipeline:
    """素材收集 → 大纲 → 成稿 → 轻质检（可局部重写）。"""

    def run(self, topic: str, **kwargs) -> ContentResult:
        config = Config.get_instance()
        writing = config.writing_config
        outline_enabled = bool(writing.get("outline_enabled", True))
        hooks_enabled = bool(writing.get("hooks_enabled", True))
        qc_enabled = bool(writing.get("qc_enabled", True))
        qc_max_rewrite = int(writing.get("qc_max_rewrite", 1) or 0)

        materials = gather_materials(
            topic,
            urls=kwargs.get("urls") or [],
            reference_ratio=float(kwargs.get("reference_ratio") or 0.0),
        )

        outline: Optional[OutlineResult] = None
        if outline_enabled:
            log.print_log("[PROGRESS:OUTLINE:START]", "internal")
            try:
                outline = self._generate_outline(topic, materials, hooks_enabled, **kwargs)
            except Exception as e:
                log.print_log(f"大纲生成失败，降级为直接写作: {e}", "warning")
            log.print_log("[PROGRESS:OUTLINE:END]", "internal")

        log.print_log("[PROGRESS:WRITING:START]", "internal")
        article = self._generate_article(topic, materials, outline, **kwargs)
        log.print_log("[PROGRESS:WRITING:END]", "internal")

        if not qc_enabled:
            return article

        log.print_log("[PROGRESS:QC:START]", "internal")
        report = check_article(
            article.title, article.content, config.min_article_len, config.max_article_len
        )
        rewrites = 0
        while not report.passed and rewrites < qc_max_rewrite:
            log.print_log(
                f"质检未通过，尝试重写（{rewrites + 1}/{qc_max_rewrite}）: {'；'.join(report.reasons)}",
                "warning",
            )
            try:
                article = self._rewrite_article(topic, article, report.reasons, outline, **kwargs)
            except Exception as e:
                log.print_log(f"质检重写失败，保留当前稿: {e}", "warning")
                break
            rewrites += 1
            report = check_article(
                article.title, article.content, config.min_article_len, config.max_article_len
            )

        if report.passed:
            article.metadata["qc_passed"] = True
        else:
            log.print_log(f"质检仍未完全达标，继续后续流程: {'；'.join(report.reasons)}", "warning")
            article.metadata["qc_warning"] = report.reasons
        log.print_log("[PROGRESS:QC:END]", "internal")
        return article

    @staticmethod
    def _single_agent_workflow(
        name: str, role: str, goal: str, backstory: str, description: str, expected: str
    ) -> WorkflowConfig:
        return WorkflowConfig(
            name=name,
            description=goal,
            workflow_type=WorkflowType.SEQUENTIAL,
            content_type=ContentType.ARTICLE,
            agents=[
                AgentConfig(
                    role=role,
                    name="worker",
                    goal=goal,
                    backstory=backstory,
                    tools=[],
                    max_iter=4,
                )
            ],
            tasks=[
                TaskConfig(
                    name=f"{name}_task",
                    description=description,
                    agent_name="worker",
                    expected_output=expected,
                )
            ],
        )

    def _generate_outline(
        self, topic: str, materials: Materials, hooks_enabled: bool, **kwargs
    ) -> OutlineResult:
        config = Config.get_instance()
        hook_hint = (
            f"开头钩子类型必须从以下选择其一：{' / '.join(HOOK_TYPES)}"
            if hooks_enabled
            else f"开头钩子类型可选，默认 {DEFAULT_HOOK}"
        )
        description = f"""为文章题目「{{topic}}」生成写作大纲，只输出结构化大纲，不要写正文。

参考素材：
{{materials}}

输出格式（严格遵守）：
选定标题：xxx
开头钩子类型：xxx
候选标题：
- 标题1
- 标题2
- 标题3
正文小标题大纲：
1. 小标题A
2. 小标题B
3. 小标题C
（可选 4～6 个）

要求：
- 大纲必须紧扣题目本身；素材与题目无关时忽略素材
- 候选标题恰好 3 个，选定标题必须来自候选之一
- {hook_hint}
- 小标题 3～6 个，面向微信公众号可读性
- 目标字数约 {config.min_article_len}~{config.max_article_len}
- 不要输出思考过程
"""
        workflow = self._single_agent_workflow(
            "writing_outline",
            "选题与大纲编辑",
            "产出清晰可执行的文章大纲",
            "你擅长公众号爆文结构与开头钩子设计",
            description,
            "结构化大纲文本",
        )
        result = ContentGenerationEngine(workflow).execute_workflow(
            {
                "topic": topic,
                "materials": materials.to_prompt_block(),
                "parse_result": False,
                "content_format": "markdown",
            }
        )
        return parse_outline(result.content, fallback_topic=topic)

    def _generate_article(
        self,
        topic: str,
        materials: Materials,
        outline: Optional[OutlineResult] = None,
        **kwargs,
    ) -> ContentResult:
        config = Config.get_instance()
        hook_line = (
            f"- 开头必须使用「{outline.hook_type}」钩子手法，前 2 段抓住读者\n" if outline else ""
        )
        description = f"""围绕文章题目「{{topic}}」撰写一篇高质量的微信公众号文章。

写作大纲（必须遵循）：
{{outline}}

参考素材：
{{materials}}

文章要求：
- 内容必须紧扣题目；素材只是辅助，与题目无关的素材一律不用
- 标题优先使用大纲中的「选定标题」；平台标识「{{platform}}」不为空时，标题格式为「平台标识|选定标题」
{hook_line}- 用 Markdown 二级标题对应大纲小标题
- 总字数：{config.min_article_len}~{config.max_article_len}字（纯文本字数）
- 格式：标准Markdown；仅输出最终文章，严禁思考过程或额外说明
"""
        publish_platform = kwargs.get("publish_platform", "wechat")
        workflow = self._single_agent_workflow(
            f"{publish_platform}_content_generation",
            "内容创作专家",
            "按大纲撰写高质量文章",
            "你是一位擅长公众号结构与开头钩子的作家",
            description,
            "文章标题 + 文章正文（标准Markdown格式）",
        )
        input_data: Dict[str, Any] = {
            "topic": topic,
            "platform": kwargs.get("platform", ""),
            "outline": outline.to_prompt_block() if outline else NO_OUTLINE,
            "materials": materials.to_prompt_block(),
        }
        if outline and outline.selected_title:
            input_data["title"] = outline.selected_title
        result = ContentGenerationEngine(workflow).execute_workflow(input_data)

        result.metadata["materials"] = {
            "source_type": materials.source_type,
            "queries": materials.queries,
            "count": len(materials.items),
        }
        if outline:
            result.metadata["outline"] = {
                "selected_title": outline.selected_title,
                "hook_type": outline.hook_type,
                "sections": outline.sections,
                "candidate_titles": outline.candidate_titles,
            }
        return result

    def _rewrite_article(
        self,
        topic: str,
        article: ContentResult,
        reasons: List[str],
        outline: Optional[OutlineResult] = None,
        **kwargs,
    ) -> ContentResult:
        config = Config.get_instance()
        reason_text = "\n".join(f"- {r}" for r in reasons)
        description = f"""你是质检返工编辑。根据失败原因改写文章，只输出改写后的完整 Markdown 文章。

题目：{{topic}}
失败原因：
{reason_text}

目标字数：{config.min_article_len}~{config.max_article_len}
大纲约束：
{{outline}}

原稿：
{{content}}

要求：
- 保留有效信息，针对性修复失败项
- 标题保留或微调；开头更有钩子
- 减少空洞列表，段落自然
- 不要输出思考过程
"""
        workflow = self._single_agent_workflow(
            "writing_qc_rewrite",
            "质检返工编辑",
            "按质检意见改好文章",
            "你擅长快速修复结构与字数问题",
            description,
            "改写后的完整 Markdown 文章",
        )
        result = ContentGenerationEngine(workflow).execute_workflow(
            {
                "topic": topic,
                "content": article.content,
                "title": article.title,
                "outline": outline.to_prompt_block() if outline else "保持原有结构",
            }
        )
        result.metadata.update(article.metadata)
        result.metadata["qc_rewritten"] = True
        return result
