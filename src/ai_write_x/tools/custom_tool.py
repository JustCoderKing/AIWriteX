import os
import glob
import random
import sys
from pathlib import Path
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.ai_write_x.utils import utils
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log
from src.ai_write_x.tools import search_template
from src.ai_write_x.utils.path_manager import PathManager


class ReadTemplateToolInput(BaseModel):
    pass


# 1. Read Template Tool
class ReadTemplateTool(BaseTool):
    name: str = "read_template_tool"
    description: str = (
        "从本地读取HTML模板文件，此模板必须作为最终输出的基础结构，保持视觉风格和布局效果，仅替换内容部分"
    )
    args_schema: Type[BaseModel] = ReadTemplateToolInput

    def _run(self) -> str:
        config = Config.get_instance()

        # 获取模板文件的绝对路径
        template_dir_abs = PathManager.get_template_dir()
        forced = getattr(config, "forced_template_file", None)
        if isinstance(forced, str) and os.path.isfile(forced):
            selected_template_file = forced
            with open(selected_template_file, "r", encoding="utf-8") as file:
                selected_template_content = file.read()
            return self._render_template_result(
                config, template_dir_abs, selected_template_file, selected_template_content
            )

        # 根据custom_topic是否为空选择配置源
        if config.custom_topic:
            # 使用自定义话题的模板配置
            template_category = config.custom_template_category
            template = config.custom_template
        else:
            # 使用应用配置
            template_category = config.template_category
            template = config.template

        random_template = True
        selected_template_file: str = ""

        # 如果指定了具体模板且存在，则不随机
        if template and template != "":  # 随机模板的条件是""
            template_filename = template if template.endswith(".html") else f"{template}.html"

            # 如果指定了分类，在分类目录下查找
            if template_category and template_category != "":  # 实际上选则了模板，也一定选择了分类
                category_dir = os.path.join(template_dir_abs, template_category)
                selected_template_file = os.path.join(category_dir, template_filename)

            if os.path.exists(path=selected_template_file):
                random_template = False

        # 需要随机选择模板
        if random_template:
            # 排除的目录
            excluded_dirs = {"components", "__pycache__", ".git"}

            # 如果指定了分类且不是随机分类
            if template_category and template_category != "":
                category_dir = os.path.join(template_dir_abs, template_category)
                template_files_abs = glob.glob(os.path.join(category_dir, "*.html"))
            else:
                # 随机分类或未指定分类，从所有分类的模板中选择
                template_files_abs = []
                for category_dir in os.listdir(template_dir_abs):
                    category_path = os.path.join(template_dir_abs, category_dir)
                    if os.path.isdir(category_path) and category_dir not in excluded_dirs:
                        template_files_abs.extend(glob.glob(os.path.join(category_path, "*.html")))

            if not template_files_abs:
                log.print_log(
                    f"在目录 '{template_dir_abs}' 中未找到任何模板文件。如果没有模板请将config.yaml中的use_template设置为false"
                )
                sys.exit(1)

            selected_template_file = random.choice(template_files_abs)

        with open(selected_template_file, "r", encoding="utf-8") as file:
            selected_template_content = file.read()

        return self._render_template_result(
            config, template_dir_abs, selected_template_file, selected_template_content
        )

    def _render_template_result(self, config, template_dir_abs, selected_template_file, selected_template_content):
        template_content = utils.compress_html(
            selected_template_content,
            config.use_compress,
        )

        selected_path = Path(selected_template_file)
        template_name = selected_path.stem
        template_category = selected_path.parent.name
        try:
            template_rel = str(selected_path.relative_to(Path(template_dir_abs))).replace("\\", "/")
        except ValueError:
            template_rel = f"{template_category}/{selected_path.name}"

        config.last_used_template = {
            "category": template_category,
            "name": template_name,
            "path": template_rel,
        }
        config.last_formatting_mode = "template"
        log.print_log(f"使用模板: {template_category}/{template_name}")
        log.print_log("模板填充适配处理比较耗时，请耐心等待...")
        return f"""
        【HTML模板 - 必须作为最终输出的基础】
        {template_content}

        【模板使用指南】
        1. 上面是完整的HTML模板，您必须基于此模板进行内容适配
        2. 必须保持的元素：
        - 所有<section>标签的布局结构和内联样式
        - 原有的视觉层次、色彩方案和排版风格
        - 卡片式布局、圆角和阴影效果
        - SVG动画元素和交互特性
        3. 内容适配规则：
        - 标题替换标题、段落替换段落、列表替换列表
        - 当新内容比原模板内容长或短时，合理调整，不破坏布局
        - 保持原有的强调部分（粗体、斜体、高亮等）应用于新内容的相应部分
        - 保持图片位置不变
        4. 严格禁止：
        - 不添加新的style标签或外部CSS
        - 不改变原有的色彩方案（限制在三种色系内）
        - 不修改模板的整体视觉效果和布局结构
        5. 最终输出必须是基于此模板的HTML，保持相同的视觉效果和样式，但内容已更新

        【重要提示】
        您的任务是将前置任务生成的文章内容适配到此模板中，而不是创建新的HTML。
        请分析模板结构，识别内容区域，然后将新内容填充到对应位置。
        """


# 2. AIForge Search Tool
class AIForgeSearchToolInput(BaseModel):
    """输入参数模型"""

    topic: str = Field(..., description="要搜索的话题")
    urls: List[str] = Field(default=[], description="参考文章链接数组")
    reference_ratio: float = Field(..., description="参考文章借鉴比例")


class AIForgeSearchTool(BaseTool):
    """AIForge搜索工具"""

    name: str = "aiforge_search_tool"
    description: str = (
        "搜索关于特定主题的最新信息、数据和趋势。"
        "每个任务最多调用一次；Action Input 必须是单个 JSON 对象"
        '（形如 {"topic":"...","urls":[],"reference_ratio":0.0}），不能是数组。'
        "拿到搜索结果后应立即撰写文章，不要用相同参数再次调用本工具。"
    )

    args_schema: type[BaseModel] = AIForgeSearchToolInput

    def _run(self, topic: str, urls: List[str], reference_ratio: float) -> str:
        """执行AIForge搜索"""
        results = None
        config = Config.get_instance()
        original_cwd = os.getcwd()

        log.print_log("[PROGRESS:SEARCH:START]", "internal")

        if len(urls) == 0:
            log.print_log("开始执行搜索，请耐心等待...")
            results = self._excute_search(topic)

            source_type = "搜索"
        else:
            log.print_log("开始提取参考链接中的文章信息，请耐心等待...")
            extract_results = search_template.extract_urls_content(urls, topic)
            # 这里只要参考文章获取到一条有效结果，就认为通过， 当然也可以len(urls)条结果
            if search_template.validate_search_result(
                extract_results, min_results=1, search_type="reference_article"
            ):
                results = extract_results.get("results")

            source_type = "参考文章"

        os.chdir(original_cwd)

        try:
            fmt_result = self._formatted_result(topic, urls, reference_ratio, source_type, results)
        except Exception:
            fmt_result = "未找到最新信息"

        log.print_log("[PROGRESS:SEARCH:END]", "internal")

        log.print_log("[PROGRESS:WRITING:START]", "internal")

        return fmt_result

    def _formatted_result(self, topic, urls, reference_ratio, source_type, results):
        if results:
            # 根据模式过滤掉相应字段为空的条目
            filtered_results = []
            for result in results:
                normalized = self._normalize_search_item(result)
                title = normalized.get("title", "").strip()

                # 根据模式判断不同的内容字段
                if len(urls) > 0:
                    # 借鉴模式：检查content字段
                    content_field = normalized.get("content", "").strip()
                else:
                    # 搜索模式：摘要优先，其次正文类字段
                    content_field = (
                        normalized.get("abstract", "").strip()
                        or normalized.get("content", "").strip()
                    )

                # 如果标题和对应的内容字段都不为空，则保留该条目
                if title and content_field:
                    filtered_results.append(normalized)

            if filtered_results:
                if len(urls) > 0:
                    formatted = (
                        f"关于'{topic}'的{source_type}结果（参考比例：{reference_ratio}）：\n\n"
                    )
                else:
                    formatted = f"关于'{topic}'的{source_type}结果：\n\n"

                for i, result in enumerate(filtered_results, 1):
                    # 限制标题长度
                    title = result.get("title", "无标题")
                    if len(title) > 100:
                        title = title[:100] + "..."

                    # 限制摘要长度
                    abstract = result.get("abstract", "无摘要")
                    if len(abstract) > 300:
                        abstract = abstract[:300] + "..."

                    formatted += f"## 结果 {i}\n"
                    formatted += f"**标题**: {title}\n"
                    formatted += f"**发布时间**: {result.get('pub_time', '未知时间')}\n"
                    source_url = result.get("url", "")
                    if source_url:
                        formatted += f"**链接**: {source_url}\n"
                    source_name = result.get("source_name", "")
                    if source_name:
                        formatted += f"**来源**: {source_name}\n"
                    formatted += f"**摘要**: {abstract}\n"

                    # 如果是URL提取，添加更多内容信息
                    if len(urls) > 0 and "content" in result:
                        content = result.get("content", "")
                        # 限制内容长度
                        if len(content) > 500:
                            content = content[:500] + "..."
                        formatted += f"**内容**: {content}...\n"
                    formatted += "\n"

                log.print_log(
                    f"搜索结果可用 {len(filtered_results)}/{len(results)} 条（已过滤空标题或空摘要）"
                )
                return formatted
            else:
                log.print_log(
                    f"搜索返回了 {len(results)} 条原始结果，但标题/摘要字段为空，已全部过滤",
                    "warning",
                )
                return f"未能找到关于'{topic}'的有效{source_type}结果。"
        else:
            return f"未能找到关于'{topic}'的{source_type}结果。"

    def _normalize_search_item(self, item: dict) -> dict:
        """统一搜索结果字段，兼容 snippet/summary 等常见别名。"""
        if not isinstance(item, dict):
            return {}

        normalized = dict(item)

        title = (
            normalized.get("title")
            or normalized.get("name")
            or normalized.get("标题")
            or ""
        )
        abstract = (
            normalized.get("abstract")
            or normalized.get("snippet")
            or normalized.get("summary")
            or normalized.get("desc")
            or normalized.get("description")
            or normalized.get("content")
            or normalized.get("摘要")
            or ""
        )
        url = (
            normalized.get("url")
            or normalized.get("link")
            or normalized.get("href")
            or normalized.get("链接")
            or ""
        )
        pub_time = (
            normalized.get("pub_time")
            or normalized.get("publish_time")
            or normalized.get("time")
            or normalized.get("date")
            or normalized.get("发布时间")
            or ""
        )

        normalized["title"] = str(title).strip() if title is not None else ""
        normalized["abstract"] = str(abstract).strip() if abstract is not None else ""
        normalized["url"] = str(url).strip() if url is not None else ""
        normalized["pub_time"] = str(pub_time).strip() if pub_time is not None else ""
        if "content" in normalized and normalized["content"] is not None:
            normalized["content"] = str(normalized["content"]).strip()
        return normalized

    def _excute_search(self, topic):
        """按系统设置中已启用的网站和各自条数检索。"""
        try:
            sites = [site for site in Config.get_instance().search_sites if site.get("enabled")]
            if not sites:
                log.print_log("没有启用的搜索网站，将不使用搜索结果生成文章", "warning")
                return None

            results = search_template.search_enabled_sites(sites, topic)
            if not results:
                log.print_log("已启用的搜索网站均未返回可用结果", "warning")
                return None

            for index, item in enumerate(results, 1):
                title = (item.get("title") or "")[:60]
                abs_len = len((item.get("abstract") or "").strip())
                source_name = item.get("source_name") or ""
                url = (item.get("url") or "")[:80]
                log.print_log(
                    f"搜索结果[{index}] 来源={source_name} | 标题={title} | 摘要={abs_len}字 | url={url}"
                )
            return results
        except Exception as e:
            log.print_traceback("搜索过程中发生错误：", e)
            return None
