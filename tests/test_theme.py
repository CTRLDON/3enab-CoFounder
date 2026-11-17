"""Adaptive palettes: classified from the plan, always WCAG AA, muted when stopped."""

from __future__ import annotations

import pytest

from app.services.color_math import contrast_ratio
from app.services.theme_service import ARCHETYPES, build_palette, classify_system
from conftest import make_venture, ok, script, to_workspace


@pytest.mark.parametrize("key", list(ARCHETYPES))
@pytest.mark.parametrize("state", [None, "STOPPED", "PIVOT_REQUIRED"])
def test_every_palette_meets_its_contrast_targets(key, state):
    palette = build_palette(ARCHETYPES[key], state)
    failures = [c for c in palette["contrast"] if not c["passes"]]
    assert not failures, failures
    assert contrast_ratio(palette["tokens"]["text"], palette["tokens"]["bg"]) >= 7


def test_classification_is_explainable():
    result = classify_system([("A scheduling and attendance tool for tutoring centres", 2.0)])
    assert result.archetype.key == "b2b_ops" and "attendance" in result.matched_terms
    assert classify_system([("", 1.0)]).archetype.key == "general"
    assert classify_system([("An API monitoring tool for developers", 1.0)]).archetype.key == "developer"


def test_stopped_state_mutes_the_accent():
    from app.services.color_math import relative_luminance  # noqa: F401

    normal = build_palette(ARCHETYPES["learning"])["tokens"]["accent"]
    muted = build_palette(ARCHETYPES["learning"], "STOPPED")["tokens"]["accent"]
    assert normal != muted


def test_theme_follows_the_current_plan(client, founder_headers):
    vid = make_venture(client, founder_headers)
    assert ok(client.get(f"/api/ventures/{vid}/theme", headers=founder_headers))["source"] == "discussion so far"
    ok(client.post(f"/api/ventures/{vid}/debate", json={"message": script(client)["debate"][1]}, headers=founder_headers))
    assert ok(client.get(f"/api/ventures/{vid}/theme", headers=founder_headers))["archetype"] == "learning"

    vid2 = to_workspace(client, founder_headers)
    theme = ok(client.get(f"/api/ventures/{vid2}/theme", headers=founder_headers))
    assert theme["archetype"] == "b2b_ops" and theme["source"] == "approved plan v1" and theme["all_contrast_checks_pass"]
