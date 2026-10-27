# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_write_x.core.imaging.pipeline import replace_placeholder_images  # noqa: E402
from src.ai_write_x.core.imaging.placement import (  # noqa: E402
    find_inline_slots,
    insert_images_at_offsets,
)

MD = """# 标题

开头段落，抓住读者。

## 第一节

第一节内容。

## 第二节

第二节内容。

## 第三节

第三节内容。

## 第四节

第四节内容。
"""


def test_slots_not_at_start_and_bounded():
    slots = find_inline_slots(MD, 2, 4)
    assert 1 <= len(slots) <= 4
    first_para = MD.index("开头段落")
    assert all(s > first_para for s in slots)


def test_insert_images():
    slots = find_inline_slots(MD, 2, 2)
    out = insert_images_at_offsets(MD, slots, [f"![图{i}](/images/{i}.jpg)\n" for i in range(len(slots))])
    assert out.count("![图") == len(slots)
    assert out.startswith("# 标题")


def test_replace_picsum():
    html = '<img src="https://picsum.photos/800/400?random=1"><img src="https://picsum.photos/1/1">'
    out = replace_placeholder_images(html, ["/images/a.jpg"])
    assert "/images/a.jpg" in out
    assert out.count("picsum") == 1
