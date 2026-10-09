# -*- coding: utf-8 -*-

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai_write_x.utils.html_import import adapt_preview_html  # noqa: E402

SAMPLE = """
<html><head><style>
:root { --ink:#112233; --brand:#1f6f8b; }
.toolbar { color:red; }
.phone { background:#fff; padding:20px; }
h2.title { color:var(--brand); font-size:24px; }
p { color:var(--ink); font-size:16px; }
.hl { font-weight:600; }
.foot { color:#999; }
</style></head><body>
<div class="toolbar"><h1>预览工具条</h1></div>
<div class="phone">
  <h2 class="title">为什么我们对外人客气</h2>
  <p>在公司你说好的。<span class="hl">几乎所有中年人</span></p>
</div>
<div class="foot">发布时间建议</div>
</body></html>
"""


def test_import_strips_chrome_and_inlines_styles():
    result = adapt_preview_html(SAMPLE)
    article = result["article_html"]
    assert result["title"] == "为什么我们对外人客气"
    assert "预览工具条" not in article
    assert "发布时间建议" not in article
    assert "color: #1f6f8b" in article or "color:#1f6f8b" in article.replace(" ", "")
    assert "<style" not in article
    assert "几乎所有中年人" in article
    assert "{{内容}}" in result["template_html"]
    assert "几乎所有中年人" not in result["template_html"]
