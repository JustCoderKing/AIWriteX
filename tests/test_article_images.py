# -*- coding: utf-8 -*-

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai_write_x.utils.article_images import optimize_article_images  # noqa: E402


def test_optimize_replaces_picsum_and_relative_images(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.ai_write_x.utils.article_images.article_image_dir",
        lambda: tmp_path,
    )
    html = """
    <img src="https://picsum.photos/600/300?random=2" alt="城市">
    <img src="image/1.jpg" alt="封面">
    <img src="/api/articles/media?name=kept.png" alt="已优化">
    """
    updated, count = optimize_article_images(html, "示例文章")
    assert count == 2
    assert "picsum.photos" not in updated
    assert "image/1.jpg" not in updated
    assert updated.count("/api/articles/media?name=") == 3
    assert any(tmp_path.glob("*.png"))
