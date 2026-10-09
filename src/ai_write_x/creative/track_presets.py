# -*- coding: utf-8 -*-
"""账号赛道 → 创意维度推荐。勾选最多两个赛道，主赛道优先。"""

DIMENSION_KEYS = (
    "style",
    "culture",
    "time",
    "personality",
    "emotion",
    "format",
    "scene",
    "audience",
    "theme",
    "technique",
    "language",
    "tone",
    "perspective",
    "structure",
    "rhythm",
)

ACCOUNT_TRACKS = (
    "动漫二次元",
    "游戏",
    "装修设计",
    "家居生活",
    "创意美学",
    "时尚潮流",
    "美容美妆",
    "服饰穿搭",
    "好物种草",
    "影视影评",
    "娱乐八卦",
    "情感生活",
    "文化文学",
    "生活方式",
    "宗教历史",
    "军事政法",
    "金融财经",
    "房产楼市",
    "科学科普",
    "互联网",
    "数码 3C",
    "新闻媒体",
    "行业资讯",
    "海外资讯",
    "区域生活",
    "健康养生",
    "体育赛事",
    "运动健身",
    "母婴育儿",
    "教育培训",
    "校园生活",
    "职场管理",
    "餐饮美食",
    "星座命理",
    "搞笑幽默",
    "旅游出行",
    "汽车",
    "宠物",
    "音乐",
    "其他",
)


def _preset(enabled, options, intensity=1.0, max_dimensions=5):
    return {
        "intensity": intensity,
        "max_dimensions": max_dimensions,
        "enabled": list(enabled),
        "options": dict(options),
        "priority_categories": list(enabled)[:4],
    }


TRACK_PRESETS = {
    "动漫二次元": _preset(
        ["style", "emotion", "audience", "scene", "language"],
        {
            "style": "fantasy",
            "emotion": "romantic",
            "audience": "gen_z",
            "scene": "futuristic_city",
            "language": "slang",
        },
        intensity=1.2,
    ),
    "游戏": _preset(
        ["style", "emotion", "audience", "scene", "rhythm"],
        {
            "style": "narrative",
            "emotion": "epic",
            "audience": "gen_z",
            "scene": "futuristic_city",
            "rhythm": "fast",
        },
        intensity=1.2,
    ),
    "装修设计": _preset(
        ["style", "tone", "theme", "structure", "audience"],
        {
            "style": "expository",
            "tone": "calm",
            "theme": "cultural_heritage",
            "structure": "spatial",
            "audience": "professionals",
        },
        intensity=0.9,
    ),
    "家居生活": _preset(
        ["style", "tone", "audience", "theme", "scene"],
        {
            "style": "prose",
            "tone": "casual",
            "audience": "parents",
            "theme": "growth",
            "scene": "coffee_shop",
        },
    ),
    "创意美学": _preset(
        ["style", "personality", "theme", "language", "rhythm"],
        {
            "style": "prose",
            "personality": "artist",
            "theme": "cultural_heritage",
            "language": "poetic",
            "rhythm": "variable",
        },
        intensity=1.2,
    ),
    "时尚潮流": _preset(
        ["style", "tone", "audience", "theme", "rhythm"],
        {
            "style": "prose",
            "tone": "enthusiastic",
            "audience": "gen_z",
            "theme": "adventure",
            "rhythm": "fast",
        },
        intensity=1.1,
    ),
    "美容美妆": _preset(
        ["style", "tone", "audience", "format", "structure"],
        {
            "style": "expository",
            "tone": "enthusiastic",
            "audience": "gen_z",
            "format": "manual",
            "structure": "problem_solution",
        },
        intensity=1.1,
    ),
    "服饰穿搭": _preset(
        ["style", "tone", "audience", "theme", "format"],
        {
            "style": "narrative",
            "tone": "casual",
            "audience": "gen_z",
            "theme": "adventure",
            "format": "essay",
        },
        intensity=1.1,
    ),
    "好物种草": _preset(
        ["style", "tone", "audience", "structure", "format"],
        {
            "style": "expository",
            "tone": "enthusiastic",
            "audience": "gen_z",
            "structure": "compare_contrast",
            "format": "report",
        },
        intensity=1.1,
    ),
    "影视影评": _preset(
        ["style", "emotion", "theme", "technique", "structure"],
        {
            "style": "essay",
            "emotion": "philosophical",
            "theme": "human_nature",
            "technique": "symbolism",
            "structure": "thematic",
        },
    ),
    "娱乐八卦": _preset(
        ["style", "tone", "emotion", "audience", "rhythm"],
        {
            "style": "news",
            "tone": "sarcastic",
            "emotion": "humorous",
            "audience": "gen_z",
            "rhythm": "fast",
        },
        intensity=1.2,
    ),
    "情感生活": _preset(
        ["style", "emotion", "personality", "theme", "rhythm"],
        {
            "style": "prose",
            "emotion": "healing",
            "personality": "emotion_healer",
            "theme": "love",
            "rhythm": "slow",
        },
        intensity=1.1,
    ),
    "文化文学": _preset(
        ["style", "culture", "language", "theme", "personality"],
        {
            "style": "prose",
            "culture": "chinese_tradition",
            "language": "classical",
            "theme": "cultural_heritage",
            "personality": "libai",
        },
        intensity=1.1,
    ),
    "生活方式": _preset(
        ["style", "tone", "audience", "theme", "rhythm"],
        {
            "style": "prose",
            "tone": "casual",
            "audience": "gen_z",
            "theme": "growth",
            "rhythm": "steady",
        },
    ),
    "宗教历史": _preset(
        ["style", "culture", "time", "theme", "tone"],
        {
            "style": "essay",
            "culture": "chinese_tradition",
            "time": "ancient_china",
            "theme": "cultural_heritage",
            "tone": "serious",
        },
        intensity=0.9,
    ),
    "军事政法": _preset(
        ["style", "tone", "structure", "theme", "language"],
        {
            "style": "news",
            "tone": "serious",
            "structure": "cause_effect",
            "theme": "social_justice",
            "language": "plain",
        },
        intensity=0.8,
    ),
    "金融财经": _preset(
        ["style", "tone", "audience", "structure", "language"],
        {
            "style": "essay",
            "tone": "serious",
            "audience": "professionals",
            "structure": "cause_effect",
            "language": "technical",
        },
        intensity=0.8,
    ),
    "房产楼市": _preset(
        ["style", "tone", "audience", "structure", "theme"],
        {
            "style": "expository",
            "tone": "calm",
            "audience": "professionals",
            "structure": "compare_contrast",
            "theme": "growth",
        },
        intensity=0.9,
    ),
    "科学科普": _preset(
        ["style", "personality", "audience", "language", "structure"],
        {
            "style": "expository",
            "personality": "scientist",
            "audience": "students",
            "language": "plain",
            "structure": "problem_solution",
        },
        intensity=0.9,
    ),
    "互联网": _preset(
        ["style", "tone", "audience", "theme", "structure"],
        {
            "style": "essay",
            "tone": "casual",
            "audience": "tech_workers",
            "theme": "tech_reflection",
            "structure": "thematic",
        },
    ),
    "数码 3C": _preset(
        ["style", "tone", "audience", "format", "structure"],
        {
            "style": "expository",
            "tone": "enthusiastic",
            "audience": "tech_workers",
            "format": "report",
            "structure": "compare_contrast",
        },
        intensity=1.1,
    ),
    "新闻媒体": _preset(
        ["style", "tone", "structure", "perspective", "rhythm"],
        {
            "style": "news",
            "tone": "serious",
            "structure": "chronological",
            "perspective": "observer",
            "rhythm": "fast",
        },
        intensity=0.9,
    ),
    "行业资讯": _preset(
        ["style", "tone", "audience", "structure", "language"],
        {
            "style": "news",
            "tone": "serious",
            "audience": "professionals",
            "structure": "thematic",
            "language": "technical",
        },
        intensity=0.9,
    ),
    "海外资讯": _preset(
        ["style", "culture", "tone", "structure", "perspective"],
        {
            "style": "news",
            "culture": "western_logic",
            "tone": "calm",
            "structure": "compare_contrast",
            "perspective": "observer",
        },
    ),
    "区域生活": _preset(
        ["style", "tone", "scene", "audience", "theme"],
        {
            "style": "narrative",
            "tone": "casual",
            "scene": "bustling_city",
            "audience": "retirees",
            "theme": "growth",
        },
    ),
    "健康养生": _preset(
        ["style", "tone", "audience", "theme", "structure"],
        {
            "style": "expository",
            "tone": "calm",
            "audience": "seniors",
            "theme": "time_healing",
            "structure": "problem_solution",
        },
        intensity=0.9,
    ),
    "体育赛事": _preset(
        ["style", "emotion", "tone", "rhythm", "audience"],
        {
            "style": "narrative",
            "emotion": "epic",
            "tone": "enthusiastic",
            "rhythm": "fast",
            "audience": "gen_z",
        },
        intensity=1.2,
    ),
    "运动健身": _preset(
        ["style", "tone", "audience", "theme", "structure"],
        {
            "style": "expository",
            "tone": "enthusiastic",
            "audience": "professionals",
            "theme": "growth",
            "structure": "problem_solution",
        },
        intensity=1.1,
    ),
    "母婴育儿": _preset(
        ["style", "tone", "audience", "theme", "emotion"],
        {
            "style": "prose",
            "tone": "calm",
            "audience": "parents",
            "theme": "growth",
            "emotion": "healing",
        },
    ),
    "教育培训": _preset(
        ["style", "tone", "audience", "structure", "theme"],
        {
            "style": "expository",
            "tone": "serious",
            "audience": "students",
            "structure": "problem_solution",
            "theme": "growth",
        },
        intensity=0.9,
    ),
    "校园生活": _preset(
        ["style", "tone", "audience", "scene", "emotion"],
        {
            "style": "narrative",
            "tone": "casual",
            "audience": "students",
            "scene": "university_campus",
            "emotion": "inspiring",
        },
        intensity=1.1,
    ),
    "职场管理": _preset(
        ["style", "tone", "audience", "theme", "structure"],
        {
            "style": "essay",
            "tone": "serious",
            "audience": "professionals",
            "theme": "growth",
            "structure": "problem_solution",
        },
        intensity=0.9,
    ),
    "餐饮美食": _preset(
        ["style", "tone", "scene", "emotion", "language"],
        {
            "style": "prose",
            "tone": "enthusiastic",
            "scene": "coffee_shop",
            "emotion": "romantic",
            "language": "vernacular",
        },
        intensity=1.1,
    ),
    "星座命理": _preset(
        ["style", "emotion", "personality", "theme", "tone"],
        {
            "style": "prose",
            "emotion": "mysterious",
            "personality": "mystery_detective",
            "theme": "human_nature",
            "tone": "mysterious",
        },
        intensity=1.2,
    ),
    "搞笑幽默": _preset(
        ["style", "emotion", "tone", "technique", "rhythm"],
        {
            "style": "narrative",
            "emotion": "humorous",
            "tone": "humorous",
            "technique": "satire",
            "rhythm": "fast",
        },
        intensity=1.3,
    ),
    "旅游出行": _preset(
        ["style", "scene", "audience", "theme", "rhythm"],
        {
            "style": "prose",
            "scene": "seaside_cabin",
            "audience": "travelers",
            "theme": "adventure",
            "rhythm": "variable",
        },
        intensity=1.1,
    ),
    "汽车": _preset(
        ["style", "tone", "audience", "structure", "language"],
        {
            "style": "expository",
            "tone": "enthusiastic",
            "audience": "professionals",
            "structure": "compare_contrast",
            "language": "technical",
        },
    ),
    "宠物": _preset(
        ["style", "emotion", "tone", "audience", "theme"],
        {
            "style": "narrative",
            "emotion": "healing",
            "tone": "casual",
            "audience": "gen_z",
            "theme": "love",
        },
        intensity=1.1,
    ),
    "音乐": _preset(
        ["style", "emotion", "language", "rhythm", "personality"],
        {
            "style": "poetry",
            "emotion": "romantic",
            "language": "poetic",
            "rhythm": "variable",
            "personality": "artist",
        },
        intensity=1.2,
    ),
    "其他": _preset(
        ["style", "tone", "audience", "theme", "rhythm"],
        {
            "style": "prose",
            "tone": "casual",
            "audience": "gen_z",
            "theme": "growth",
            "rhythm": "steady",
        },
    ),
}


def normalize_tracks(tracks):
    """去重、校验，最多两个，顺序即主/辅。"""
    seen = set()
    result = []
    for raw in tracks or []:
        name = (raw or "").strip()
        if not name or name in seen:
            continue
        if name not in TRACK_PRESETS:
            raise ValueError(f"未知赛道: {name}")
        seen.add(name)
        result.append(name)
        if len(result) >= 2:
            break
    return result


def merge_track_recommendations(tracks):
    """
    合并一到两个赛道的推荐。
    冲突维度采用主赛道选项，并在 conflicts 中给出辅赛道备选。
    """
    selected = normalize_tracks(tracks)
    if not selected:
        raise ValueError("请至少选择一个赛道")

    primary = selected[0]
    secondary = selected[1] if len(selected) > 1 else None
    primary_preset = TRACK_PRESETS[primary]
    secondary_preset = TRACK_PRESETS[secondary] if secondary else None

    enabled = {key: False for key in DIMENSION_KEYS}
    options = {}
    sources = {}
    conflicts = []

    for dim in primary_preset["enabled"]:
        enabled[dim] = True
        options[dim] = primary_preset["options"][dim]
        sources[dim] = primary

    if secondary_preset:
        for dim in secondary_preset["enabled"]:
            secondary_option = secondary_preset["options"][dim]
            if not enabled[dim]:
                enabled[dim] = True
                options[dim] = secondary_option
                sources[dim] = secondary
                continue
            primary_option = options[dim]
            if primary_option != secondary_option:
                conflicts.append(
                    {
                        "dimension": dim,
                        "primary_track": primary,
                        "primary_option": primary_option,
                        "secondary_track": secondary,
                        "secondary_option": secondary_option,
                        "chosen": primary_option,
                    }
                )

    enabled_count = sum(1 for value in enabled.values() if value)
    max_dimensions = max(enabled_count, primary_preset["max_dimensions"])
    if secondary_preset:
        max_dimensions = max(max_dimensions, secondary_preset["max_dimensions"], enabled_count)

    return {
        "tracks": selected,
        "primary": primary,
        "secondary": secondary,
        "creative_intensity": primary_preset["intensity"],
        "max_dimensions": min(max_dimensions, 10),
        "auto_dimension_selection": False,
        "enabled_dimensions": enabled,
        "selected_options": options,
        "option_sources": sources,
        "priority_categories": primary_preset["priority_categories"],
        "conflicts": conflicts,
    }


def list_track_catalog():
    return [{"name": name, "enabled": TRACK_PRESETS[name]["enabled"]} for name in ACCOUNT_TRACKS]
