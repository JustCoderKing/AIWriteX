# Phase 1 Writing Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 `UnifiedContentWorkflow` 上增加「大纲 → 成稿 → 轻质检」流水线，提升文章结构与开头钩子质量。

**Architecture:** 新增 `core/writing/` 包：纯规则 QC + 大纲解析与 `WritingPipeline`；通过 `Config.writing` 开关控制。开启时替换 `_generate_base_content` 内部实现；关闭时保持原单 writer 行为。复用 `ContentGenerationEngine` 跑短 Crew 任务。

**Tech Stack:** Python 3.10+、现有 CrewAI/`ContentGenerationEngine`、pytest

**Spec:** `docs/superpowers/specs/2026-10-27-mvp-writing-image-humanize-design.md` §4

## Global Constraints

- 路径 B：流水线增强，不大改多智能体
- 配置可关：`writing.outline_enabled` / `hooks_enabled` / `qc_enabled`
- 质检最多重写 1 次；失败不阻断保存
- 未经用户明确要求不自动 `git commit`
- 搜索工具缺失时降级写作，不中断

## File Map

| 文件 | 职责 |
|------|------|
| `src/ai_write_x/core/writing/hooks.py` | 内置钩子类型常量 |
| `src/ai_write_x/core/writing/models.py` | `OutlineResult` |
| `src/ai_write_x/core/writing/outline_parser.py` | 从 LLM 文本解析大纲 |
| `src/ai_write_x/core/writing/qc.py` | 规则质检 + `QCReport` |
| `src/ai_write_x/core/writing/pipeline.py` | 大纲→写作→质检编排 |
| `src/ai_write_x/core/writing/__init__.py` | 导出 |
| `src/ai_write_x/config/config.py` | `writing` 默认项与 property |
| `src/ai_write_x/core/unified_workflow.py` | 接入 pipeline |
| `tests/test_writing_qc.py` | QC 单测 |
| `tests/test_outline_parser.py` | 大纲解析单测 |

---

### Task 1: QC 规则（纯函数）

**Files:**
- Create: `src/ai_write_x/core/writing/qc.py`
- Create: `src/ai_write_x/core/writing/__init__.py`
- Test: `tests/test_writing_qc.py`

**Interfaces:**
- Produces: `QCReport(passed: bool, reasons: list[str])`, `check_article(title, content, min_len, max_len) -> QCReport`

- [ ] **Step 1:** 写失败测试（字数不足、开头过短、列表过多、正常通过）
- [ ] **Step 2:** 运行 `.\.venv\Scripts\python.exe -m pytest tests/test_writing_qc.py -v` 确认 FAIL
- [ ] **Step 3:** 实现 `qc.py`（中文字数≈去空白后 len；开头取首段；列表行占比阈值）
- [ ] **Step 4:** 测试 PASS
- [ ] **Step 5:** 跳过 commit（除非用户要求）

---

### Task 2: 钩子常量 + Outline 模型与解析

**Files:**
- Create: `src/ai_write_x/core/writing/hooks.py`
- Create: `src/ai_write_x/core/writing/models.py`
- Create: `src/ai_write_x/core/writing/outline_parser.py`
- Test: `tests/test_outline_parser.py`

**Interfaces:**
- Produces: `HOOK_TYPES: list[str]`；`OutlineResult(selected_title, hook_type, sections, candidate_titles)`；`parse_outline(text: str) -> OutlineResult`

- [ ] **Step 1:** 写解析测试（结构化 Markdown 样例）
- [ ] **Step 2:** 测试 FAIL
- [ ] **Step 3:** 实现 hooks/models/parser（容错：缺字段用默认）
- [ ] **Step 4:** 测试 PASS

---

### Task 3: WritingPipeline + 配置

**Files:**
- Create: `src/ai_write_x/core/writing/pipeline.py`
- Modify: `src/ai_write_x/config/config.py`（`default_config["writing"]` + `writing_config` property）
- Modify: `src/ai_write_x/core/unified_workflow.py`（`_generate_base_content` 分支）

**Interfaces:**
- Consumes: Task1/2、`ContentGenerationEngine`、`Config`
- Produces: `WritingPipeline.run(topic, **kwargs) -> ContentResult`

行为：
1. `outline_enabled`：短 Crew 生成大纲文本 → `parse_outline`
2. `hooks_enabled=false` 时大纲提示不强制钩子类型
3. 写作 Crew：注入大纲；保留 search 工具参数
4. `qc_enabled`：不通过则带 reasons 重写最多 `qc_max_rewrite` 次
5. 进度日志：`OUTLINE` / `WRITING` / `QC`
6. 任一步异常：warning + 降级（无大纲直写 / 跳过 QC）

- [ ] **Step 1:** 加 `writing` 默认配置与 property
- [ ] **Step 2:** 实现 `WritingPipeline`
- [ ] **Step 3:** `unified_workflow._generate_base_content` 在 writing 开启时走 pipeline
- [ ] **Step 4:** 冒烟：`outline_enabled=false` 时行为与旧路径等价（可手动或轻量单测 mock）

---

### Task 4: 一期收尾

- [ ] 更新设计文档状态为「一期实现中/已完成」
- [ ] 跑相关 pytest
- [ ] 向用户汇报一期完成，进入二期配图计划与实现

---

## 后续（本会话依次交付，另开计划文件）

- Phase 2：`core/imaging/` 封面+文内图
- Phase 3：`core/humanize/` 规则人味
