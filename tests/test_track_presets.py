# -*- coding: utf-8 -*-

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import pytest

from src.ai_write_x.creative.track_presets import (  # noqa: E402
    ACCOUNT_TRACKS,
    TRACK_PRESETS,
    merge_track_recommendations,
    normalize_tracks,
)


def test_tracks_are_unique_and_have_presets():
    assert len(ACCOUNT_TRACKS) == len(set(ACCOUNT_TRACKS))
    assert set(ACCOUNT_TRACKS) == set(TRACK_PRESETS)


def test_normalize_keeps_first_two_and_dedupes():
    assert normalize_tracks(["生活方式", "情感生活", "生活方式", "游戏"]) == [
        "生活方式",
        "情感生活",
    ]


def test_unknown_track_raises():
    with pytest.raises(ValueError):
        normalize_tracks(["不存在的赛道"])


def test_single_track_recommendation():
    rec = merge_track_recommendations(["情感生活"])
    assert rec["primary"] == "情感生活"
    assert rec["secondary"] is None
    assert rec["auto_dimension_selection"] is False
    assert rec["enabled_dimensions"]["emotion"] is True
    assert rec["selected_options"]["emotion"] == "healing"
    assert rec["conflicts"] == []


def test_dual_track_union_and_primary_wins_conflicts():
    rec = merge_track_recommendations(["生活方式", "情感生活"])
    assert rec["primary"] == "生活方式"
    assert rec["secondary"] == "情感生活"
    assert rec["enabled_dimensions"]["tone"] is True
    assert rec["enabled_dimensions"]["emotion"] is True
    assert rec["selected_options"]["style"] == "prose"
    conflict_dims = {item["dimension"]: item for item in rec["conflicts"]}
    assert "theme" in conflict_dims
    assert conflict_dims["theme"]["chosen"] == "growth"
    assert conflict_dims["theme"]["secondary_option"] == "love"
    assert rec["selected_options"]["theme"] == "growth"
    assert rec["selected_options"]["rhythm"] == "steady"


def test_empty_tracks_raise():
    with pytest.raises(ValueError):
        merge_track_recommendations([])
