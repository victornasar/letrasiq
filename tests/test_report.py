"""The report tells the truth about what's finished, and only a person can mark a font reviewed."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from letrasiq.pipeline import build_font
from letrasiq.report import FAILED, PASSED, PERSON, build_report, fingerprint, latin_core, render_report
from letrasiq.spec import FontSpec

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def font_dir(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("fonts")
    shutil.copytree(
        REPO / "fonts" / "letra-humanist",
        root / "letra-humanist",
        ignore=shutil.ignore_patterns("build", "glyphs", "__pycache__", "review.json"),
    )
    d = root / "letra-humanist"
    build_font("letra-humanist", root=root, skip_preview=True)
    # The report looks for these previews, without needing to render them here.
    previews = d / "build" / "previews"
    previews.mkdir(parents=True, exist_ok=True)
    for name in ("tester.html", "review.png", "detail.png"):
        (previews / name).write_text("", encoding="utf-8")
    return d


def stage(report, name):
    return next(s for stages in report.groups.values() for s in stages if s.name == name)


def write_review(d: Path, **changes) -> None:
    review = {
        "reviewer": "A Designer",
        "date": "2026-12-01",
        "version": FontSpec.load(d / "spec.json").version,
        "fingerprint": fingerprint(d),
        "outcome": "approved",
        **changes,
    }
    (d / "review.json").write_text(json.dumps(review), encoding="utf-8")


@pytest.fixture(autouse=True)
def no_review_left_behind(font_dir):
    yield
    (font_dir / "review.json").unlink(missing_ok=True)


def test_latin_core_list_is_a_real_superset_of_basic_latin():
    core = latin_core()
    assert all(code in core for code in range(0x20, 0x7F))
    assert 0x00E9 in core and 0x0159 in core
    assert len(core) > 250


def test_every_stage_has_a_status_and_explanation(font_dir):
    report = build_report(font_dir, run_font_bakery=False)
    assert len(report.groups) == 7
    for stages in report.groups.values():
        assert stages
        for s in stages:
            assert s.status in (PASSED, FAILED, PERSON)
            assert s.detail


def test_unfinished_work_shows_as_failed_and_human_work_as_needing_a_person(font_dir):
    report = build_report(font_dir, run_font_bakery=False)
    assert stage(report, "Latin Core coverage").status == PASSED
    assert stage(report, "Review packet").status == FAILED
    assert stage(report, "Letterform quality").status == PERSON
    assert stage(report, "Control glyphs").status == PASSED


def test_automation_alone_cannot_mark_a_font_reviewed(font_dir):
    report = build_report(font_dir, run_font_bakery=False)
    assert not report.reviewed
    assert stage(report, "Independent design review").status == PERSON
    assert "not reviewed" in report.summary


def test_a_matching_approved_review_marks_it_reviewed(font_dir):
    write_review(font_dir)
    report = build_report(font_dir, run_font_bakery=False)
    assert report.reviewed
    assert "A Designer" in stage(report, "Independent design review").detail


def test_a_review_goes_stale_when_the_font_changes(font_dir):
    write_review(font_dir, fingerprint="an-earlier-state")
    assert not build_report(font_dir, run_font_bakery=False).reviewed


def test_a_review_for_another_version_or_asking_for_changes_does_not_count(font_dir):
    write_review(font_dir, version="0.0.1")
    assert not build_report(font_dir, run_font_bakery=False).reviewed
    write_review(font_dir, outcome="fix the g")
    report = build_report(font_dir, run_font_bakery=False)
    assert not report.reviewed
    assert "fix the g" in stage(report, "Independent design review").detail


def test_incomplete_review_file_fails_clearly(font_dir):
    (font_dir / "review.json").write_text('{"reviewer": "Someone"}', encoding="utf-8")
    report = build_report(font_dir, run_font_bakery=False)
    assert stage(report, "Independent design review").status == FAILED
    assert not report.reviewed


def test_report_page_and_summary_are_written(font_dir):
    page = render_report(font_dir, run_font_bakery=False)
    text = page.read_text(encoding="utf-8")
    assert "Not reviewed by a type designer" in text
    assert "needs a person" in text
    summary = (page.parent / "report-summary.txt").read_text(encoding="utf-8")
    assert summary.startswith("report letra-humanist:") and "not reviewed" in summary


def test_real_font_bakery_results_reach_the_report(font_dir):
    pytest.importorskip("fontbakery")
    report = build_report(font_dir)
    universal = stage(report, "Font Bakery universal checks (TTF)")
    assert universal.status == PASSED
    assert "passed" in universal.detail
