"""A release comes from one exact build, and a review packet gives a reviewer what they need."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from letrasiq.release import build_release
from letrasiq.report import FAILED, PASSED, build_report

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def released(tmp_path_factory):
    root = tmp_path_factory.mktemp("fonts")
    shutil.copytree(
        REPO / "fonts" / "letra-humanist",
        root / "letra-humanist",
        ignore=shutil.ignore_patterns("build", "glyphs", "__pycache__"),
    )
    return root, build_release("letra-humanist", root=root)


def stage(report, name):
    return next(s for stages in report.groups.values() for s in stages if s.name == name)


def test_package_has_desktop_web_and_documentation(released):
    _, out = released
    package = out["package"]
    assert list((package / "Desktop").glob("*.otf")) and list((package / "Desktop").glob("*.ttf"))
    assert list((package / "Web").glob("*.woff2"))
    for name in ("OFL.txt", "README.txt", "Specimen.html", "CHANGELOG.txt"):
        assert (package / "Documentation" / name).exists()
    assert "../Web/LetraHumanist-Regular.woff2" in (package / "Documentation" / "Specimen.html").read_text(encoding="utf-8")


def test_packet_gives_a_reviewer_what_they_need(released):
    _, out = released
    packet = out["packet"]
    text = (packet / "README.md").read_text(encoding="utf-8")
    assert "A warm humanist sans" in text
    assert "## Questions" in text and "## Known weaknesses" in text and "fussy link" in text
    for name in ("tester.html", "report.html", "review.png", "detail.png", "detail-core.png", "design.json", "review.template.json"):
        assert (packet / name).exists(), name
    with zipfile.ZipFile(out["archive"]) as archive:
        assert any(n.endswith("README.md") for n in archive.namelist())


def test_report_shows_release_ready_for_this_build(released):
    root, _ = released
    report = build_report(root / "letra-humanist", run_font_bakery=False)
    for name in ("Release package", "Specimen and documentation", "Review packet"):
        assert stage(report, name).status == PASSED
    assert not report.reviewed


def test_release_goes_stale_when_the_font_changes(released):
    root, _ = released
    d = root / "letra-humanist"
    design = d / "design.json"
    original = design.read_text(encoding="utf-8")
    try:
        design.write_text(original.replace('"stem": 90', '"stem": 91'), encoding="utf-8")
        report = build_report(d, run_font_bakery=False)
        assert stage(report, "Review packet").status == FAILED
        assert "changed" in stage(report, "Review packet").detail
    finally:
        design.write_text(original, encoding="utf-8")
