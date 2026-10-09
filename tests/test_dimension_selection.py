# -*- coding: utf-8 -*-

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.ai_write_x.creative.dimensional_engine import DimensionalCreativeEngine  # noqa: E402


def test_manual_dimensions_use_saved_options():
    engine = DimensionalCreativeEngine(
        {
            "enabled_dimensions": {"style": True, "language": False, "tone": True},
            "dimension_options": {
                "style": {
                    "selected_option": "prose",
                    "preset_options": [
                        {"name": "prose", "value": "散文", "weight": 1.0, "description": "形散神聚"},
                        {"name": "novel", "value": "小说", "weight": 1.0, "description": "情节丰富"},
                    ],
                },
                "tone": {
                    "selected_option": "custom",
                    "custom_input": "克制",
                    "preset_options": [],
                },
                "language": {
                    "selected_option": "formal",
                    "preset_options": [
                        {"name": "formal", "value": "正式", "weight": 1.0, "description": "严谨"}
                    ],
                },
            },
        }
    )

    selected = engine.select_dimensions(False, 5)
    chosen = {category: option["value"] for category, option in selected}
    assert chosen == {"style": "散文", "tone": "克制"}
