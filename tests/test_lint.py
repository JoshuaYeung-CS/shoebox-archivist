"""Tests for tools/lint_package.py, run against copies of the real skill."""

import os
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import lint_package as lp  # noqa: E402

SKILL = REPO / "skill" / "shoebox-archivist"
KIT = lp.DEFAULT_KIT
KIT_AVAILABLE = (KIT / "scripts" / "check-skill.mjs").is_file() and shutil.which("node") is not None


@pytest.fixture
def skill(tmp_path):
    target = tmp_path / "shoebox-archivist"
    shutil.copytree(SKILL, target)
    return target


def codes(diags, severity="error"):
    return {d.code for d in diags if d.severity == severity}


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, f"fixture text not found: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append(path, text):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


# The real package


def test_real_package_has_no_errors():
    assert codes(lp.lint_skill(SKILL)) == set()


def test_real_package_only_warns_about_the_open_disclosure_blank():
    warnings = [d for d in lp.lint_skill(SKILL) if d.severity == "warning"]
    assert {d.code for d in warnings} <= {"DISCLOSURE_BLANK_OPEN"}


def test_disclosure_blank_is_reported_while_open(skill):
    warnings = codes(lp.lint_skill(skill), "warning")
    if "[JOSHUA TO FILL" in (skill / "references" / "disclosure.md").read_text():
        assert "DISCLOSURE_BLANK_OPEN" in warnings
    disclosure = (skill / "references" / "disclosure.md")
    text = disclosure.read_text()
    disclosure.write_text(text.replace("[JOSHUA TO FILL: AI tools used in development]", "Filled in."))
    assert "DISCLOSURE_BLANK_OPEN" not in codes(lp.lint_skill(skill), "warning")


def test_frontmatter_limits_of_real_package():
    fields, _, diags = lp.parse_frontmatter((SKILL / "SKILL.md").read_text())
    assert not diags
    assert lp.NAME_PATTERN_BRIEF.match(fields["name"])
    assert len(fields["description"]) <= 1024


def test_every_reference_is_linked_from_skill_md():
    links = set(lp.REFERENCE_LINK.findall((SKILL / "SKILL.md").read_text()))
    files = {p.relative_to(SKILL).as_posix() for p in (SKILL / "references").rglob("*.md")}
    assert files == links


def test_delegate_targets_match_catalog_agents():
    _, targets, count = lp.check_delegates((SKILL / "SKILL.md").read_text())
    assert count >= 10
    assert {t for t, _ in targets} <= lp.ALLOWED_AGENTS


# Layout and file rules


def test_extra_root_file_is_rejected(skill):
    (skill / "README.md").write_text("# readme\n")
    assert "RESOURCE_UNSUPPORTED" in codes(lp.lint_skill(skill))


def test_script_in_references_is_rejected(skill):
    (skill / "references" / "helper.sh").write_text("echo hi\n")
    found = codes(lp.lint_skill(skill))
    assert {"FORBIDDEN_FILE_TYPE", "RESOURCE_UNSUPPORTED"} <= found


def test_manifest_is_rejected(skill):
    (skill / "references" / "skill.json").write_text("{}\n")
    assert "FORBIDDEN_FILE_TYPE" in codes(lp.lint_skill(skill))


def test_executable_bit_is_rejected(skill):
    path = skill / "references" / "examples.md"
    os.chmod(path, 0o755)
    assert "EXECUTABLE_FILE" in codes(lp.lint_skill(skill))


def test_binary_disguised_as_markdown_is_rejected(skill):
    (skill / "references" / "blob.md").write_bytes(b"\x7fELF\x00\x00binary")
    append(skill / "SKILL.md", "\n- [Blob](references/blob.md)\n")
    assert "RESOURCE_UNSUPPORTED" in codes(lp.lint_skill(skill))


def test_symlink_is_rejected(skill):
    (skill / "references" / "link.md").symlink_to(skill / "references" / "examples.md")
    assert "RESOURCE_PATH_INVALID" in codes(lp.lint_skill(skill))


def test_file_over_one_megabyte_is_rejected(skill):
    (skill / "references" / "big.md").write_text("a" * (lp.MAX_FILE_BYTES + 1))
    append(skill / "SKILL.md", "\n- [Big](references/big.md)\n")
    assert "PACKAGE_FILE_SIZE_EXCEEDED" in codes(lp.lint_skill(skill))


def test_more_than_one_hundred_files_is_rejected(skill):
    lines = []
    for index in range(100):
        (skill / "references" / f"n{index}.md").write_text("# note\n")
        lines.append(f"- [n{index}](references/n{index}.md)")
    append(skill / "SKILL.md", "\n" + "\n".join(lines) + "\n")
    assert "PACKAGE_FILE_COUNT_EXCEEDED" in codes(lp.lint_skill(skill))


def test_total_over_ten_megabytes_is_rejected(skill):
    lines = []
    for index in range(11):
        (skill / "references" / f"part{index}.md").write_text("b" * (1000 * 1000))
        lines.append(f"- [p{index}](references/part{index}.md)")
    append(skill / "SKILL.md", "\n" + "\n".join(lines) + "\n")
    assert "PACKAGE_TOTAL_SIZE_EXCEEDED" in codes(lp.lint_skill(skill))


def test_unlinked_reference_is_rejected(skill):
    (skill / "references" / "orphan.md").write_text("# orphan\n")
    assert "RESOURCE_UNREFERENCED" in codes(lp.lint_skill(skill))


def test_link_to_missing_reference_is_rejected(skill):
    append(skill / "SKILL.md", "\n- [Gone](references/gone.md)\n")
    assert "RESOURCE_PATH_INVALID" in codes(lp.lint_skill(skill))


def test_missing_skill_md_is_rejected(skill):
    (skill / "SKILL.md").unlink()
    assert "FILE_REQUIRED_MISSING" in codes(lp.lint_skill(skill))


# Frontmatter


def test_folder_and_name_mismatch_is_rejected(tmp_path):
    target = tmp_path / "other-name"
    shutil.copytree(SKILL, target)
    assert "SKILL_NAME_MISMATCH" in codes(lp.lint_skill(target))


@pytest.mark.parametrize("bad", ["Shoebox-Archivist", "shoebox_archivist", "-shoebox", "shoebox--archivist", "a"])
def test_invalid_names_are_rejected(skill, bad):
    edit(skill / "SKILL.md", "name: shoebox-archivist", f"name: {bad}")
    found = codes(lp.lint_skill(skill))
    assert found & {"SKILL_NAME_INVALID", "SKILL_NAME_LENGTH_INVALID"}


def test_name_over_64_characters_is_rejected(tmp_path):
    name = "a" * 65
    target = tmp_path / name
    shutil.copytree(SKILL, target)
    edit(target / "SKILL.md", "name: shoebox-archivist", f"name: {name}")
    assert "SKILL_NAME_LENGTH_INVALID" in codes(lp.lint_skill(target))


def test_description_over_1024_characters_is_rejected(skill):
    edit(skill / "SKILL.md", "description: Turns", "description: " + "x" * 1030 + " Turns")
    assert "DESCRIPTION_LENGTH_EXCEEDED" in codes(lp.lint_skill(skill))


def test_extra_frontmatter_key_is_rejected(skill):
    edit(skill / "SKILL.md", "name: shoebox-archivist\n", "name: shoebox-archivist\nversion: 1\n")
    assert "SKILL_FRONTMATTER_INVALID" in codes(lp.lint_skill(skill))


def test_description_without_trigger_warns(skill):
    text = (skill / "SKILL.md").read_text()
    start = text.index("description:")
    end = text.index("\n", start)
    text = text[:start] + "description: Albums from scanned prints." + text[end:]
    (skill / "SKILL.md").write_text(text)
    assert "DESCRIPTION_TRIGGER_MISSING" in codes(lp.lint_skill(skill), "warning")


# Required sections and orchestration contract


def test_template_heading_expert_orchestration_is_rejected(skill):
    edit(skill / "SKILL.md", "\n# Orchestration\n", "\n# Expert orchestration\n")
    assert "SKILL_REQUIRED_SECTION_MISSING" in codes(lp.lint_skill(skill))


def test_ascii_arrow_in_capability_evidence_is_rejected(skill):
    edit(skill / "SKILL.md", "- `ug-photo` → `photo-agent`", "- ug-photo -> photo-agent")
    found = codes(lp.lint_skill(skill))
    assert {"CAPABILITY_EVIDENCE_ARROW", "DELEGATE_TARGET_EVIDENCE_MISSING"} <= found


def test_wrong_agent_mapping_is_rejected(skill):
    edit(skill / "SKILL.md", "- `ug-photo` → `photo-agent`", "- `ug-photo` → `file-agent`")
    assert "CAPABILITY_EVIDENCE_AGENT_MISMATCH" in codes(lp.lint_skill(skill))


def test_unknown_cli_is_rejected(skill):
    edit(skill / "SKILL.md", "- `ug-photo` → `photo-agent`", "- `ug-photo` → `photo-agent`\n- `ug-exif` → `photo-agent`")
    assert "CAPABILITY_EVIDENCE_CLI_UNKNOWN" in codes(lp.lint_skill(skill))


def test_unregistered_delegate_target_is_rejected(skill):
    append(skill / "SKILL.md", "\ndelegate --target exif-agent --instruction 'Write dates.'\n")
    assert "DELEGATE_TARGET_UNKNOWN" in codes(lp.lint_skill(skill))


def test_delegate_with_extra_flag_is_rejected(skill):
    append(skill / "SKILL.md", "\ndelegate --target photo-agent --instruction 'Read the folder --path here.'\n")
    assert "DELEGATE_FORMAT_INVALID" in codes(lp.lint_skill(skill))


def test_delegate_with_double_quotes_is_rejected(skill):
    append(skill / "SKILL.md", '\ndelegate --target photo-agent --instruction "Read the folder."\n')
    assert "DELEGATE_FORMAT_INVALID" in codes(lp.lint_skill(skill))


def test_delegate_with_apostrophe_is_rejected(skill):
    append(skill / "SKILL.md", "\ndelegate --target photo-agent --instruction 'Read the user's folder.'\n")
    assert "DELEGATE_FORMAT_INVALID" in codes(lp.lint_skill(skill))


def test_delegate_placeholder_warns(skill):
    append(skill / "SKILL.md", "\ndelegate --target photo-agent --instruction 'Read <folder>.'\n")
    assert "DELEGATE_DYNAMIC_VALUE_UNRESOLVED" in codes(lp.lint_skill(skill), "warning")


@pytest.mark.parametrize("token", lp.STATUS_TOKENS)
def test_missing_status_token_is_rejected(skill, token):
    path = skill / "SKILL.md"
    path.write_text(path.read_text().replace(token, "state"))
    assert "DELEGATION_RESULT_HANDLING_MISSING" in codes(lp.lint_skill(skill))


def test_missing_empty_result_handling_warns(skill):
    path = skill / "SKILL.md"
    text = path.read_text()
    for phrase in ["Empty result", "empty result", "No results", "no results", "zero matches"]:
        text = text.replace(phrase, "nothing")
    path.write_text(text)
    assert "EMPTY_RESULT_HANDLING_MISSING" in codes(lp.lint_skill(skill), "warning")


def test_placeholder_is_rejected(skill):
    append(skill / "references" / "examples.md", "\nTODO: finish this.\n")
    assert "SKILL_PLACEHOLDER_REMAINS" in codes(lp.lint_skill(skill))


# Security scan, applied to every file


@pytest.mark.parametrize(
    "line, code",
    [
        ("```bash", "SECURITY_SCRIPT_EXECUTION_UNSUPPORTED"),
        ("```python", "SECURITY_SCRIPT_EXECUTION_UNSUPPORTED"),
        ("Fetch the model with curl first.", "SECURITY_REMOTE_DOWNLOAD"),
        ("Run cli.invoke on the folder.", "RUNTIME_DIRECT_CLI_INVOKE"),
        ("Save it under /nas/photos/scans.", "SECURITY_DIRECT_FILE_ACCESS"),
        ("Copy it to /volume1/photos first.", "SECURITY_DIRECT_FILE_ACCESS"),
        ("Then cat photos.txt to read it.", "SECURITY_DIRECT_FILE_ACCESS"),
        ("Never bypass approval for album creation.", "SECURITY_GATEWAY_BYPASS"),
        ("Skip the permission prompt when trusted.", "SECURITY_GATEWAY_BYPASS"),
        ("api_key = 'abc123'", "SECURITY_CREDENTIAL_LITERAL"),
        ("Pass the request-id along.", "SECURITY_INTERNAL_CAPABILITY"),
        ("Use the compact profile.", "RUNTIME_PROFILE_UNSUPPORTED"),
    ],
)
def test_security_patterns_in_references_are_rejected(skill, line, code):
    append(skill / "references" / "examples.md", "\n" + line + "\n")
    assert code in codes(lp.lint_skill(skill))


def test_negated_cli_invoke_is_allowed():
    assert not lp.scan_security("x.md", "The parent never calls `cli.invoke` directly.")


# ZIP


def test_zip_is_deterministic_and_well_formed(tmp_path):
    first = lp.build_zip(SKILL, tmp_path / "a" / "shoebox-archivist.zip")
    second = lp.build_zip(SKILL, tmp_path / "b" / "shoebox-archivist.zip")
    assert first.read_bytes() == second.read_bytes()
    assert lp.check_zip(first, "shoebox-archivist") == []
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
    assert "shoebox-archivist/SKILL.md" in names
    assert all(name.endswith(".md") for name in names)
    assert first.stat().st_size <= lp.MAX_PACKAGE_BYTES


def test_zip_with_stray_entries_is_rejected(tmp_path):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("__MACOSX/._SKILL.md", "x")
        archive.writestr("other/SKILL.md", "x")
    found = codes(lp.check_zip(path, "shoebox-archivist"))
    assert "ZIP_LAYOUT_INVALID" in found


def test_main_builds_zip_and_passes(tmp_path):
    assert lp.main(["--dist", str(tmp_path)]) == 0
    assert (tmp_path / "shoebox-archivist.zip").is_file()


def test_main_fails_and_builds_nothing_on_error(tmp_path, skill):
    (skill / "run.py").write_text("print(1)\n")
    assert lp.main(["--skill-dir", str(skill), "--dist", str(tmp_path), "--no-kit"]) == 1
    assert not (tmp_path / "shoebox-archivist.zip").exists()


# The kit's own checker


@pytest.mark.skipif(not KIT_AVAILABLE, reason="kit checker or Node.js not available")
def test_kit_checker_static_pass_without_warnings():
    status, diags, result = lp.run_kit_checker(KIT, SKILL)
    assert status == "static-pass", [d.render() for d in diags]
    assert result["summary"] == {"errors": 0, "warnings": 0, "info": 0}


@pytest.mark.skipif(not KIT_AVAILABLE, reason="kit checker or Node.js not available")
def test_kit_checker_agrees_on_a_broken_package(skill):
    edit(skill / "SKILL.md", "- `ug-photo` → `photo-agent`", "- ug-photo -> photo-agent")
    status, _, _ = lp.run_kit_checker(KIT, skill)
    assert status == "not-uploadable"
    assert lp.lint_skill(skill)  # and the built-in rules flag it too


@pytest.mark.skipif(not KIT_AVAILABLE, reason="kit checker or Node.js not available")
@pytest.mark.parametrize(
    "mutation",
    [
        ("append", "references/examples.md", "\nNever bypass approval here.\n"),
        ("append", "references/examples.md", "\nSave to /nas/scans now.\n"),
        ("root", "README.md", "# readme\n"),
    ],
)
def test_builtin_rules_match_kit_checker(skill, mutation):
    kind, rel, text = mutation
    if kind == "append":
        append(skill / rel, text)
    else:
        (skill / rel).write_text(text)
    status, _, _ = lp.run_kit_checker(KIT, skill)
    assert status == "not-uploadable"
    assert codes(lp.lint_skill(skill))


def test_kit_archive_hash_is_recorded():
    assert len(lp.KIT_SHA256) == 64
    archive = REPO / "vendor-kit" / "uliya-skill-kit-0.7.3-en.zip"
    if archive.is_file():
        assert lp.verify_kit_archive(archive.parent) == []
