"""The constrained MVP generator produces a working, tested product within its declared scope."""

from __future__ import annotations

import shutil

import pytest

from app.demo.scenarios import MAIN
from app.schemas.agent_io import MvpCopy, ProductSpec
from app.services.mvp_template import build_mvp, bundle_preview, render_files

SPEC = ProductSpec.model_validate(MAIN[("product_architect", "specify_mvp")][0])
COPY = MvpCopy.model_validate(MAIN[("mvp_builder", "write_mvp_copy")][0])


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required to run the generated tests")
def test_generated_mvp_tests_pass():
    result = build_mvp(SPEC, COPY, node_binary="node", timeout=60)
    assert result.test_executed and result.exit_code == 0
    assert result.tests_failed == 0 and result.tests_passed >= 8


def test_rendered_files_and_docs():
    files, unsupported = render_files(SPEC, COPY)
    assert not unsupported
    assert {"index.html", "app.js", "app-core.js", "styles.css", "README.md", "SPEC.md", "config.json", "tests/core.test.js"} <= set(files)
    assert "STUBBED" in files["README.md"]  # out-of-scope items are labelled
    preview = bundle_preview(files)
    assert "<script src=" not in preview and "MateCore" in preview


def test_missing_runner_is_reported_not_faked():
    result = build_mvp(SPEC, COPY, node_binary="definitely-not-node", timeout=5)
    assert result.test_executed is False and result.tests_passed == 0 and "not found" in result.output_tail


def test_spec_rejects_reserved_or_unsafe_field_keys():
    data = MAIN[("product_architect", "specify_mvp")][0]
    bad = {**data, "entity": {**data["entity"], "fields": [{"key": "status", "label": "x", "type": "text"}]}}
    with pytest.raises(ValueError):
        ProductSpec.model_validate(bad)
    bad = {**data, "entity": {**data["entity"], "fields": [{"key": "x'); alert(1)//", "label": "x", "type": "text"}]}}
    with pytest.raises(ValueError):
        ProductSpec.model_validate(bad)
