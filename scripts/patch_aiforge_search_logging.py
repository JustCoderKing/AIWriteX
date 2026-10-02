# -*- coding: UTF-8 -*-
"""给已安装的 aiforge-engine 增加各搜索引擎/层级的结果日志。

在虚拟环境中执行:
    python scripts/patch_aiforge_search_logging.py
重装 aiforge-engine 后需要再执行一次。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


HELPER_FUNC = '''
def _diagnose_validation_failure(i18n_manager, search_result, min_items=1, min_abstract_len=300):
    """诊断本地搜索结果未通过质量校验的原因（仅用于日志）。"""
    if not isinstance(search_result, dict):
        return "引擎未返回字典结果"
    if not search_result.get("success", False):
        return search_result.get("error") or "success=False"
    results = search_result.get("results") or []
    if not results:
        return "results为空"
    if len(results) < min_items:
        return f"结果数{len(results)} < min_items={min_items}"

    reasons = []
    required_fields = ["title", "url", "abstract", "pub_time"]
    for idx, item in enumerate(results[:5], 1):
        missing = [f for f in required_fields if not str(item.get(f) or "").strip()]
        abs_len = len(str(item.get("abstract") or "").strip())
        if abs_len < min_abstract_len:
            missing.append(f"abstract_len={abs_len}<{min_abstract_len}")
        pub_time = str(item.get("pub_time") or "").strip()
        if pub_time and not re.match(r"^\\d{4}-\\d{2}-\\d{2}$", pub_time):
            missing.append(f"pub_time格式异常={pub_time}")
        if missing:
            reasons.append(f"#{idx}缺[{','.join(missing)}]")
        else:
            reasons.append(f"#{idx}字段齐全但整体未达标")
    return "; ".join(reasons) if reasons else "未知原因"


def _report_engine_search_result(
    progress_indicator,
    i18n_manager,
    engine_name,
    search_result,
    min_items=1,
    min_abstract_len=300,
    exception=None,
):
    """向进度总线报告单个搜索引擎/层级的结果摘要。"""
    if not progress_indicator:
        return

    if exception is not None:
        progress_indicator.emit(
            "search_engine_result",
            engine=engine_name,
            raw_count=0,
            passed=False,
            fail_reason=f"异常: {exception}",
            samples="(无)",
        )
        return

    results = []
    if isinstance(search_result, dict):
        results = search_result.get("results") or []
    raw_count = len(results)
    passed = bool(
        search_result
        and validate_search_result(i18n_manager, search_result, min_items, min_abstract_len=min_abstract_len)
    )
    fail_reason = ""
    if not passed:
        fail_reason = _diagnose_validation_failure(
            i18n_manager, search_result, min_items, min_abstract_len
        )

    samples = []
    for item in results[:3]:
        title = str(item.get("title") or "")[:40]
        abs_len = len(str(item.get("abstract") or "").strip())
        pub = item.get("pub_time") or "无时间"
        url = str(item.get("url") or "")[:60]
        samples.append(f"{title}|摘要{abs_len}字|{pub}|{url}")

    progress_indicator.emit(
        "search_engine_result",
        engine=engine_name,
        raw_count=raw_count,
        passed=passed,
        fail_reason=fail_reason or "",
        samples="; ".join(samples) if samples else "(无样例)",
    )


'''


SEARCH_WEB_OLD = '''    else:
        for engine in LOCALE_SEARCH_ENGINES.get(i18n_manager.locale, "zh"):
            try:
                engine_name = i18n_manager.t(f"search.engine_{engine}")
                progress_indicator.emit("search_process", search_type=engine_name)
                search_result = _search_template(
                    i18n_manager,
                    search_query,
                    max_results,
                    ENGINE_CONFIGS[engine],
                    min_abstract_len,
                    max_abstract_len,
                )
                # 验证搜索结果质量
                if validate_search_result(i18n_manager, search_result, min_items):
                    return search_result
                else:
                    continue
            except Exception:
                continue

        # 所有搜索引擎都失败，返回 None
        return None
'''

SEARCH_WEB_NEW = '''    else:
        for engine in LOCALE_SEARCH_ENGINES.get(i18n_manager.locale, "zh"):
            try:
                engine_name = i18n_manager.t(f"search.engine_{engine}")
                progress_indicator.emit("search_process", search_type=engine_name)
                search_result = _search_template(
                    i18n_manager,
                    search_query,
                    max_results,
                    ENGINE_CONFIGS[engine],
                    min_abstract_len,
                    max_abstract_len,
                )
                _report_engine_search_result(
                    progress_indicator,
                    i18n_manager,
                    engine_name,
                    search_result,
                    min_items=min_items,
                    min_abstract_len=min_abstract_len,
                )
                # 验证搜索结果质量：通过则立即返回，不再尝试后续引擎
                if validate_search_result(
                    i18n_manager, search_result, min_items, min_abstract_len=min_abstract_len
                ):
                    return search_result
                else:
                    continue
            except Exception as e:
                engine_name = i18n_manager.t(f"search.engine_{engine}")
                _report_engine_search_result(
                    progress_indicator,
                    i18n_manager,
                    engine_name,
                    None,
                    min_items=min_items,
                    min_abstract_len=min_abstract_len,
                    exception=e,
                )
                continue

        # 所有搜索引擎都失败，返回 None
        return None
'''


PROGRESS_SYNC_HANDLER = '''
    def handle_search_engine_result(
        self, engine="", raw_count=0, passed=False, fail_reason="", samples=""
    ):
        if self._show_progress and self._i18n_manager:
            status = "通过" if passed else "未通过"
            message = self._i18n_manager.t(
                "progress.search_engine_result",
                engine=engine,
                raw_count=raw_count,
                status=status,
                fail_reason=fail_reason or "-",
                samples=samples or "(无)",
            )
            print(message)

'''

PROGRESS_ASYNC_HANDLER = '''
    async def handle_search_engine_result(
        self, engine="", raw_count=0, passed=False, fail_reason="", samples=""
    ):
        status = "通过" if passed else "未通过"
        message = f"[AIForge]📊 {engine}搜索结果: 原始{raw_count}条, 质量校验{status}"
        if self._show_progress and self._i18n_manager:
            message = self._i18n_manager.t(
                "progress.search_engine_result",
                engine=engine,
                raw_count=raw_count,
                status=status,
                fail_reason=fail_reason or "-",
                samples=samples or "(无)",
            )
            await self.progress_callback(
                {
                    "type": "progress",
                    "message": message,
                    "progress_type": "search_engine_result",
                    "timestamp": time.time(),
                }
            )
            print(message)

'''


def _aiforge_root() -> Path:
    import aiforge

    return Path(aiforge.__file__).resolve().parent


def patch_search_template(root: Path) -> bool:
    path = root / "templates" / "search_template.py"
    text = path.read_text(encoding="utf-8")
    if "_report_engine_search_result" in text:
        print(f"[skip] already patched: {path}")
        return False

    # Insert helpers before search_web
    marker = "\ndef search_web(\n"
    if marker not in text:
        raise RuntimeError(f"未能定位 search_web: {path}")
    text = text.replace(marker, "\n" + HELPER_FUNC + marker, 1)

    if SEARCH_WEB_OLD not in text:
        raise RuntimeError(f"未能匹配 search_web 引擎循环: {path}")
    text = text.replace(SEARCH_WEB_OLD, SEARCH_WEB_NEW, 1)

    # Also report SearXNG outcome
    searx_old = '''                if validate_search_result(i18n_manager, search_result, min_items):
                    return search_result
            except Exception:
                pass
        return None
'''
    searx_new = '''                _report_engine_search_result(
                    progress_indicator,
                    i18n_manager,
                    "SearXNG",
                    search_result,
                    min_items=min_items,
                    min_abstract_len=min_abstract_len,
                )
                if validate_search_result(
                    i18n_manager, search_result, min_items, min_abstract_len=min_abstract_len
                ):
                    return search_result
            except Exception as e:
                _report_engine_search_result(
                    progress_indicator,
                    i18n_manager,
                    "SearXNG",
                    None,
                    min_items=min_items,
                    min_abstract_len=min_abstract_len,
                    exception=e,
                )
        return None
'''
    if searx_old in text:
        text = text.replace(searx_old, searx_new, 1)

    path.write_text(text, encoding="utf-8")
    print(f"[ok] patched: {path}")
    return True


def patch_search_manager(root: Path) -> bool:
    path = root / "core" / "managers" / "search_manager.py"
    text = path.read_text(encoding="utf-8")
    if "search_engine_result" in text and "层级结果" in text:
        print(f"[skip] already patched: {path}")
        return False

    helper = '''
    def _emit_level_result(self, level_name: str, result, passed: bool, extra: str = ""):
        """记录多层级搜索某一层的结果摘要"""
        if not self._progress_indicator:
            return
        data = []
        if isinstance(result, dict):
            data = result.get("data") or result.get("results") or []
        samples = []
        for item in (data or [])[:3]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "")[:40]
            abstract = (
                item.get("abstract")
                or item.get("content")
                or item.get("snippet")
                or item.get("summary")
                or ""
            )
            samples.append(f"{title}|摘要{len(str(abstract).strip())}字")
        self._progress_indicator.emit(
            "search_engine_result",
            engine=level_name,
            raw_count=len(data) if isinstance(data, list) else 0,
            passed=passed,
            fail_reason=extra or ("-" if passed else "未通过质量校验或无数据"),
            samples="; ".join(samples) if samples else "(无样例)",
        )

'''
    if "def _emit_level_result" not in text:
        anchor = "    def is_search_task(self, standardized_instruction: Dict[str, Any]) -> bool:"
        if anchor not in text:
            raise RuntimeError(f"未能定位 is_search_task: {path}")
        text = text.replace(anchor, helper + anchor, 1)

    # After direct search
    old_direct = '''            if search_result:
                self._progress_indicator.emit(
                    "search_complete", count=len(search_result.get("results", 0))
                )
                # 转换为AIForge标准格式
                return self._convert_search_result_to_aiforge_format(
                    search_result, standardized_instruction, "direct_search_web"
                )

            return None
'''
    new_direct = '''            if search_result:
                self._progress_indicator.emit(
                    "search_complete", count=len(search_result.get("results", 0))
                )
                converted = self._convert_search_result_to_aiforge_format(
                    search_result, standardized_instruction, "direct_search_web"
                )
                self._emit_level_result(
                    "直连搜索汇总",
                    converted,
                    True,
                    f"execution_type=direct_search_web, query={search_result.get('search_query','')}",
                )
                return converted

            self._emit_level_result(
                "直连搜索汇总", None, False, "全部本地搜索引擎均未通过质量校验"
            )
            return None
'''
    if old_direct in text:
        text = text.replace(old_direct, new_direct, 1)

    # Cache layer result
    old_cache = '''        cache_result = self._try_cached_search(standardized_instruction, original_instruction)
        if cache_result and self._validate_search_result_quality(
            cache_result, standardized_instruction
        ):
            return cache_result
'''
    new_cache = '''        cache_result = self._try_cached_search(standardized_instruction, original_instruction)
        if cache_result and self._validate_search_result_quality(
            cache_result, standardized_instruction
        ):
            self._emit_level_result("系统缓存", cache_result, True, "命中缓存且质量通过")
            return cache_result
        self._emit_level_result(
            "系统缓存",
            cache_result,
            False,
            "无缓存或质量未通过",
        )
'''
    if old_cache in text:
        text = text.replace(old_cache, new_cache, 1)

    old_template = '''        template_result, success = self._try_template_guided_search(
            standardized_instruction, original_instruction, search_params
        )
        if success:
            return template_result
'''
    new_template = '''        template_result, success = self._try_template_guided_search(
            standardized_instruction, original_instruction, search_params
        )
        self._emit_level_result(
            "AI模板",
            template_result,
            bool(success),
            "代码生成+沙盒执行成功" if success else "AI模板搜索失败(将继续尝试下一层)",
        )
        if success:
            return template_result
'''
    if old_template in text:
        text = text.replace(old_template, new_template, 1)

    old_free = '''        freeform_result, success = self._try_free_form_search(
            standardized_instruction, original_instruction, search_params
        )
        if success:
            return freeform_result
'''
    new_free = '''        freeform_result, success = self._try_free_form_search(
            standardized_instruction, original_instruction, search_params
        )
        self._emit_level_result(
            "AI自由",
            freeform_result,
            bool(success),
            "自由模板执行成功" if success else "AI自由搜索失败",
        )
        if success:
            return freeform_result
'''
    if old_free in text:
        text = text.replace(old_free, new_free, 1)

    path.write_text(text, encoding="utf-8")
    print(f"[ok] patched: {path}")
    return True


def patch_progress_indicator(root: Path) -> bool:
    path = root / "utils" / "progress_indicator.py"
    text = path.read_text(encoding="utf-8")
    if "handle_search_engine_result" in text:
        print(f"[skip] already patched: {path}")
        return False

    sync_anchor = "    def handle_search_complete(self, count: int):\n"
    if sync_anchor not in text:
        raise RuntimeError(f"未能定位 ProgressEventHandler.handle_search_complete: {path}")
    text = text.replace(sync_anchor, PROGRESS_SYNC_HANDLER + sync_anchor, 1)

    async_anchor = "    async def handle_search_complete(self, count: int):\n"
    if async_anchor not in text:
        raise RuntimeError(f"未能定位 StreamingProgressEventHandler.handle_search_complete: {path}")
    text = text.replace(async_anchor, PROGRESS_ASYNC_HANDLER + async_anchor, 1)

    path.write_text(text, encoding="utf-8")
    print(f"[ok] patched: {path}")
    return True


def patch_locale(root: Path, locale: str, message: str) -> bool:
    path = root / "i18n" / "locales" / locale / "ui.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    progress = data.setdefault("progress", {})
    if "search_engine_result" in progress:
        print(f"[skip] already patched: {path}")
        return False
    progress["search_engine_result"] = message
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] patched: {path}")
    return True


def main() -> int:
    root = _aiforge_root()
    print(f"aiforge root: {root}")
    patch_search_template(root)
    patch_search_manager(root)
    patch_progress_indicator(root)
    patch_locale(
        root,
        "zh",
        "[AIForge]📊 {engine}搜索结果: 原始{raw_count}条, 质量校验{status}, 原因: {fail_reason}, 样例: {samples}",
    )
    patch_locale(
        root,
        "en",
        "[AIForge]📊 {engine} search result: raw={raw_count}, validation={status}, reason: {fail_reason}, samples: {samples}",
    )
    print("搜索结果日志已启用。重新启动 AIWriteX 后生效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
