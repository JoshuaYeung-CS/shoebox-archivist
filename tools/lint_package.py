#!/usr/bin/env python3
"""Lint the Shoebox Archivist skill package and build its submission ZIP.

The checks combine two rule sets:

* the UGREEN Hackathon 2026 Round 1 package rules (ZIP and uncompressed size
  at most 10 MB, at most 1 MB per file, at most 100 files, no scripts,
  executables, binaries or manifests, SKILL.md frontmatter limits), and
* the rules enforced by the static checker shipped in the Uliya Skill Kit
  0.7.3 (scripts/check-lib.mjs), re-implemented here so the lint works
  without the kit or Node.js installed.

When Node.js and the kit are present, the kit checker is also run on the
source folder and on a fresh extraction of the built ZIP, and any result of
"not-uploadable" fails the lint.

Exit status: 0 when there are no errors (warnings allowed), 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SKILL = REPO / "skill" / "shoebox-archivist"
DEFAULT_DIST = REPO / "dist"
DEFAULT_KIT = REPO / "vendor-kit" / "extracted" / "uliya-skill-kit"
DEFAULT_ROUND1 = REPO / "docs" / "round1.md"

KIT_URL = (
    "https://cdn.shopify.com/s/files/1/0630/9416/1602/files/"
    "uliya-skill-kit-0.7.3-en.zip?v=1790578898"
)
KIT_SHA256 = "cf557e5a022e4297892f39768132855154232efdedeb726b2845450ccd70e1b3"

MAX_FILE_BYTES = 1024 * 1024
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
MAX_FILES = 100
MAX_DESCRIPTION_CHARS = 1024
NAME_MIN, NAME_MAX = 2, 64
BODY_RECOMMENDED_LINES = 500

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# The task brief states the rule as ^[a-z0-9-]{2,64}$; the kit checker is
# stricter (no leading, trailing or doubled hyphens). Both must hold.
NAME_PATTERN_BRIEF = re.compile(r"^[a-z0-9-]{2,64}$")

# CLI to registered expert mapping, as fixed in the kit checker and catalog.
CLI_AGENTS = {
    "ug-music": "media-agent",
    "ug-video": "media-agent",
    "ug-surveillance": "security-monitor-agent",
    "ug-filesystem": "file-agent",
    "ug-filemgr": "file-agent",
    "file-workflow": "file-agent",
    "ug-document": "document-agent",
    "ug-knowledge": "knowledge-agent",
    "ug-photo": "photo-agent",
}
ALLOWED_AGENTS = set(CLI_AGENTS.values())
STATUS_TOKENS = ["completed", "failed", "cancelled", "waiting_user", "waiting_approval"]

REQUIRED_SECTIONS = [
    (re.compile(r"^# (?:目标|Goal)\s*$", re.M | re.I), "Goal"),
    (re.compile(r"^# (?:必需输入|Required input)\s*$", re.M | re.I), "Required input"),
    (re.compile(r"^# (?:专家编排|Workflow|Orchestration)\s*$", re.M | re.I), "Orchestration"),
    (re.compile(r"^# (?:完成与失败|Failure handling|Completion and failure)\s*$", re.M | re.I), "Completion and failure"),
]
EVIDENCE_HEADING = re.compile(r"^# (?:生成期能力依据|Generation-time capability evidence)\s*$", re.M | re.I)
EVIDENCE_LINE = re.compile(r"^\s*-\s+`([a-z][a-z0-9-]*)`\s+→\s+`([a-z][a-z0-9-]*)`\s*$", re.M)
EVIDENCE_ASCII_ARROW = re.compile(r"^\s*-\s+`?[a-z][a-z0-9-]*`?\s+->\s+`?[a-z][a-z0-9-]*`?\s*$", re.M)

PLACEHOLDER = re.compile(r"replace-with-|\bTODO\b|\bTBD\b|待定")
OPEN_BLANK = re.compile(r"\[JOSHUA TO FILL[^\]]*\]")
REFERENCE_LINK = re.compile(r"\]\((references/[A-Za-z0-9._/-]+\.md)(?:#[^)\s]+)?\)")
ANY_MD_LINK = re.compile(r"\]\(([^)\s]+)\)")

# Security patterns, mirroring the kit checker line by line.
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
CREDENTIAL = re.compile(r"\b(?:password|passwd|token|api[_-]?key|secret)\s*[:=]\s*[\"'][^\"'\n]+[\"']", re.I)
REMOTE_DOWNLOAD = re.compile(r"\b(?:curl|wget)\b|https?://\S+\s*\|\s*(?:sh|bash)\b", re.I)
RUNTIME_FENCE = re.compile(
    r"^```\s*(?:bash|sh|shell|zsh|python|py|javascript|js|node|typescript|ts|powershell|ps1|ruby|perl|php|go|lua)\b",
    re.I,
)
DIRECT_FILE_API = re.compile(r"\b(?:readFile|writeFile|unlink|pathlib|fs\.|open\s*\(|cp\s+|mv\s+|rm\s+|cat\s+)\b", re.I)
HTTP_CALL = re.compile(r"\b(?:fetch|axios|XMLHttpRequest|http\.request|https\.request)\s*\(", re.I)
NAS_PATH = re.compile(r"(?:^|[\s\"'])/(?:nas|mnt|volume\d*|shares?)(?:/|\b)", re.I)
BYPASS = re.compile(
    r"\b(?:bypass|skip|disable|ignore|绕过|跳过|关闭)\b[^\n]{0,40}\b(?:gateway|approval|permission|audit|审批|权限|审计)\b",
    re.I,
)
INTERNAL = re.compile(r"\b(?:ug-ai|HERMES(?:\s+action)?|Host CLI|expert[-_ ]?id|correlation[-_ ]?id|request[-_ ]?id)\b", re.I)
COMPACT_PROFILE = re.compile(r"\b(?:compact-main-agent|compact-unified-agent|compact profile)\b", re.I)
CLI_INVOKE = re.compile(r"\bcli\.invoke\b")
CLI_INVOKE_NEGATED = re.compile(
    r"(?:不|不要|不得|禁止|避免)[^\n]{0,24}(?:直接)?(?:执行|调用|使用)?\s*`?cli\.invoke\b"
    r"|(?:do not|don't|never|must not|without)[^\n]{0,24}\bcli\.invoke\b",
    re.I,
)
TRIGGER = re.compile(r"(?:当用户|用户(?:说|问|要|需要|希望|要求|提到)|适用于|使用于|用于|供[^，。;；]{1,40}使用|when\b|use when\b)", re.I)
HARDCODED_HOME = re.compile(r"/home/(?!<|\{|\$|某个?用户|用户名|user(?:name)?\b)[A-Za-z0-9._-]+(?:/|\b)", re.I)
UNRESOLVED_VALUE = re.compile(
    r"<[^>\n]{1,80}>|(?:该路径|该目录|上一步(?:的)?(?:路径|目录|结果|文件|文本|内容|ID|标识)|刚才(?:的)?(?:结果|路径|目录|内容))"
)
QUERY_INTENT = re.compile(r"(?:查询|查找|搜索|筛选|扫描|盘点|检索|列出|浏览|query|search|find|scan|filter|list|report)", re.I)
EMPTY_HANDLING = re.compile(
    r"(?:空结果|空列表|空集合|无结果|无匹配(?:结果|项)?|没有匹配|没有找到|未找到|目录为空|返回为空|no results?|empty (?:result|list|set)|zero matches?)",
    re.I,
)
RESULT_PASSING = re.compile(r"(真实|real)[^\n]{0,40}(结果|result)|上一步|upstream|下游|downstream", re.I)

# Anything that looks like a program, binary, archive or manifest.
FORBIDDEN_SUFFIXES = {
    ".sh", ".bash", ".zsh", ".py", ".pyc", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".php",
    ".exe", ".bat", ".cmd", ".ps1", ".bin", ".so", ".dylib", ".dll", ".jar", ".class", ".wasm",
    ".zip", ".tar", ".gz", ".tgz", ".7z", ".json", ".yaml", ".yml", ".toml", ".xml", ".ini",
    ".cfg", ".plist", ".lock", ".env",
}
MANIFEST_NAMES = {"manifest", "manifest.md", "package.json", "skill.json", "skill.yaml", "pyproject.toml"}
BINARY_MAGIC = [b"\x7fELF", b"MZ", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"PK\x03\x04", b"\x00asm"]

ZIP_DATE = (2026, 11, 1, 0, 0, 0)


@dataclass
class Diagnostic:
    code: str
    severity: str  # "error" or "warning"
    message: str
    file: str = ""
    line: int | None = None

    def render(self) -> str:
        where = self.file
        if self.line is not None:
            where += f":{self.line}"
        where = f" [{where}]" if where else ""
        return f"{self.severity.upper():7} {self.code}{where}: {self.message}"


def _err(code, message, file="", line=None):
    return Diagnostic(code, "error", message, file, line)


def _warn(code, message, file="", line=None):
    return Diagnostic(code, "warning", message, file, line)


def _line_of(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def parse_frontmatter(source: str):
    """Return (fields, body, diagnostics) using the kit checker grammar."""
    diags: list[Diagnostic] = []
    match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)", source)
    if not match:
        return None, source, [_err("SKILL_FRONTMATTER_INVALID", "SKILL.md must start with --- frontmatter holding name and description", "SKILL.md", 1)]
    fields: dict[str, str] = {}
    for index, line in enumerate(match.group(1).split("\n")):
        line = line.rstrip("\r")
        lineno = index + 2
        sep = line.find(":")
        if sep <= 0:
            diags.append(_err("SKILL_FRONTMATTER_INVALID", "frontmatter line is not a simple key: value pair", "SKILL.md", lineno))
            continue
        key, raw = line[:sep].strip(), line[sep + 1:].strip()
        if key not in ("name", "description") or key in fields or not raw or re.match(r"^[\[{&*!>|]", raw):
            diags.append(_err("SKILL_FRONTMATTER_INVALID", "frontmatter allows only single-line, non-empty, non-repeated name and description", "SKILL.md", lineno))
            continue
        quoted = re.match(r"^(?:\"([\s\S]*)\"|'([\s\S]*)')$", raw)
        fields[key] = (quoted.group(1) or quoted.group(2) or "") if quoted else raw
    for key in ("name", "description"):
        if key not in fields:
            diags.append(_err("SKILL_FRONTMATTER_INVALID", f"frontmatter is missing {key}", "SKILL.md", 1))
    return fields, source[match.end():], diags


def _delegate_command(line: str, start: int) -> str:
    opening = line.rfind("`", 0, start + 1)
    if opening != -1:
        closing = line.find("`", start)
        if closing != -1:
            return line[start:closing]
    return re.sub(r"[`),.;，。；]+$", "", line[start:].strip())


def check_delegates(source: str):
    diags: list[Diagnostic] = []
    targets: list[tuple[str, int]] = []
    count = 0
    for index, line in enumerate(source.split("\n")):
        start = line.find("delegate --")
        if start == -1:
            continue
        count += 1
        lineno = index + 1
        command = _delegate_command(line, start)
        if re.search(r"\$\(|`[^`]+`|\|\||&&|\s[|<>]\s", command):
            diags.append(_err("DELEGATE_FORMAT_INVALID", "delegate command contains a pipe, redirect, substitution or chain", "SKILL.md", lineno))
            continue
        target_matches = list(re.finditer(r"(?:^|\s)--target(?:\s+([^\s]+))?", command))
        instruction_matches = list(re.finditer(r"(?:^|\s)--instruction(?:\s+('(?:[^']|'\"'\"')*'|\"[^\"]*\"|[^\s]+))?", command))
        if len(target_matches) != 1 or len(instruction_matches) != 1 or re.search(r"\s--(?!target\b|instruction\b)[a-z0-9-]+", command, re.I):
            diags.append(_err("DELEGATE_FORMAT_INVALID", "delegate must have exactly one --target and one --instruction and no other flags", "SKILL.md", lineno))
            continue
        target = re.sub(r"[`),.;，。；]+$", "", (target_matches[0].group(1) or "").strip())
        raw = instruction_matches[0].group(1) or ""
        if not target:
            diags.append(_err("DELEGATE_FORMAT_INVALID", "delegate has no target", "SKILL.md", lineno))
        elif target not in ALLOWED_AGENTS:
            diags.append(_err("DELEGATE_TARGET_UNKNOWN", f"delegate target {target!r} is not a registered expert", "SKILL.md", lineno))
        else:
            targets.append((target, lineno))
        if raw in ("", "''", '""'):
            diags.append(_err("DELEGATE_INSTRUCTION_EMPTY", "delegate instruction is missing or empty", "SKILL.md", lineno))
        if not re.fullmatch(r"'(?:[^']|'\"'\"')*'", raw):
            diags.append(_err("DELEGATE_FORMAT_INVALID", "delegate instruction must be one shell single-quoted string", "SKILL.md", lineno))
        elif command[instruction_matches[0].end():].strip():
            # Stricter than the kit checker: an unescaped apostrophe ends the
            # quoted instruction early and leaves stray text behind it.
            diags.append(_err("DELEGATE_FORMAT_INVALID", "text after the quoted instruction (unescaped apostrophe?)", "SKILL.md", lineno))
        if HARDCODED_HOME.search(raw):
            diags.append(_warn("DELEGATE_HARDCODED_HOME_PATH", "delegate instruction hard-codes a personal home folder", "SKILL.md", lineno))
        if UNRESOLVED_VALUE.search(raw):
            diags.append(_warn("DELEGATE_DYNAMIC_VALUE_UNRESOLVED", "delegate instruction contains an unresolved placeholder", "SKILL.md", lineno))
    if count == 0:
        diags.append(_warn("DELEGATION_WORKFLOW_STATIC_VALIDATION_INCOMPLETE", "no delegate command found", "SKILL.md"))
    missing = [token for token in STATUS_TOKENS if token not in source]
    if missing:
        diags.append(_err("DELEGATION_RESULT_HANDLING_MISSING", "missing delegation states: " + ", ".join(missing), "SKILL.md"))
    if count > 1 and not RESULT_PASSING.search(source):
        diags.append(_warn("DELEGATION_WORKFLOW_STATIC_VALIDATION_INCOMPLETE", "multi-step workflow does not say that only real upstream results are passed on", "SKILL.md"))
    if count > 0 and QUERY_INTENT.search(source) and not EMPTY_HANDLING.search(source):
        diags.append(_warn("EMPTY_RESULT_HANDLING_MISSING", "query workflow has no explicit empty-result handling", "SKILL.md"))
    return diags, targets, count


def check_capability_evidence(source: str, targets):
    diags: list[Diagnostic] = []
    heading = EVIDENCE_HEADING.search(source)
    evidence = []
    if heading:
        rest = source[heading.end():]
        nxt = re.search(r"^#\s+", rest, re.M)
        section = rest if nxt is None else rest[: nxt.start()]
        for match in EVIDENCE_LINE.finditer(section):
            evidence.append((match.group(1), match.group(2), _line_of(source, heading.end() + match.start())))
        for match in EVIDENCE_ASCII_ARROW.finditer(section):
            diags.append(_err("CAPABILITY_EVIDENCE_ARROW", "capability evidence must use the form - `cli` → `agent` (Unicode arrow), not ->", "SKILL.md", _line_of(source, heading.end() + match.start())))
    if targets and not evidence:
        diags.append(_err("CAPABILITY_EVIDENCE_MISSING", "delegating skill has no '# Generation-time capability evidence' list", "SKILL.md"))
        return diags
    seen, evidenced_agents = set(), set()
    for cli, agent, lineno in evidence:
        if cli in seen:
            diags.append(_err("CAPABILITY_EVIDENCE_DUPLICATE", f"CLI {cli} listed twice", "SKILL.md", lineno))
            continue
        seen.add(cli)
        expected = CLI_AGENTS.get(cli)
        if expected is None:
            diags.append(_err("CAPABILITY_EVIDENCE_CLI_UNKNOWN", f"CLI {cli} is not in the capability catalog", "SKILL.md", lineno))
            continue
        if agent != expected:
            diags.append(_err("CAPABILITY_EVIDENCE_AGENT_MISMATCH", f"CLI {cli} belongs to {expected}, not {agent}", "SKILL.md", lineno))
            continue
        evidenced_agents.add(agent)
    for target, lineno in targets:
        if target not in evidenced_agents:
            diags.append(_err("DELEGATE_TARGET_EVIDENCE_MISSING", f"delegate target {target} has no CLI evidence line", "SKILL.md", lineno))
    return diags


def scan_security(name: str, source: str):
    diags: list[Diagnostic] = []
    for index, line in enumerate(source.split("\n")):
        lineno = index + 1
        if RUNTIME_FENCE.search(line):
            diags.append(_err("SECURITY_SCRIPT_EXECUTION_UNSUPPORTED", "runtime script code block", name, lineno))
        if PRIVATE_KEY.search(line) or CREDENTIAL.search(line):
            diags.append(_err("SECURITY_CREDENTIAL_LITERAL", "credential literal", name, lineno))
        if REMOTE_DOWNLOAD.search(line):
            diags.append(_err("SECURITY_REMOTE_DOWNLOAD", "remote download or download-and-run pattern", name, lineno))
        if CLI_INVOKE.search(line) and not CLI_INVOKE_NEGATED.search(line):
            diags.append(_err("RUNTIME_DIRECT_CLI_INVOKE", "the parent skill must not call cli.invoke directly", name, lineno))
        if INTERNAL.search(line):
            diags.append(_err("SECURITY_INTERNAL_CAPABILITY", "reference to an internal capability or correlation identifier", name, lineno))
        if COMPACT_PROFILE.search(line):
            diags.append(_err("RUNTIME_PROFILE_UNSUPPORTED", "claims an unsupported compact profile", name, lineno))
        if BYPASS.search(line):
            diags.append(_err("SECURITY_GATEWAY_BYPASS", "wording matches the approval/permission bypass pattern (negation does not help; rephrase)", name, lineno))
        if "delegate --" not in line and (DIRECT_FILE_API.search(line) or HTTP_CALL.search(line) or NAS_PATH.search(line)):
            diags.append(_err("SECURITY_DIRECT_FILE_ACCESS", "direct file, network or NAS path access outside a delegation", name, lineno))
        if PLACEHOLDER.search(line):
            diags.append(_err("SKILL_PLACEHOLDER_REMAINS", "unfinished placeholder (TODO, TBD, replace-with-)", name, lineno))
        if OPEN_BLANK.search(line):
            diags.append(_warn("DISCLOSURE_BLANK_OPEN", "a [JOSHUA TO FILL] blank is still open", name, lineno))
    return diags


def _looks_binary(data: bytes) -> bool:
    return any(data.startswith(magic) for magic in BINARY_MAGIC) or b"\0" in data


def check_files(skill_dir: Path):
    """Package layout, limits and file-type rules. Returns (diags, sources)."""
    diags: list[Diagnostic] = []
    sources: dict[str, str] = {}
    if not skill_dir.is_dir():
        return [_err("TARGET_NOT_DIRECTORY", f"{skill_dir} is not a directory")], sources
    for entry in sorted(skill_dir.iterdir()):
        if entry.name == "SKILL.md" and entry.is_file() and not entry.is_symlink():
            continue
        if entry.name == "references" and entry.is_dir() and not entry.is_symlink():
            continue
        diags.append(_err("RESOURCE_UNSUPPORTED", "only SKILL.md and references/ are allowed at the package root", entry.name))
    if not (skill_dir / "SKILL.md").is_file():
        diags.append(_err("FILE_REQUIRED_MISSING", "SKILL.md is required", "SKILL.md"))
    count, total = 0, 0
    for path in sorted(skill_dir.rglob("*")):
        rel = path.relative_to(skill_dir).as_posix()
        if path.is_symlink():
            diags.append(_err("RESOURCE_PATH_INVALID", "symbolic links are not allowed", rel))
            continue
        if path.is_dir():
            continue
        count += 1
        size = path.stat().st_size
        total += size
        if size > MAX_FILE_BYTES:
            diags.append(_err("PACKAGE_FILE_SIZE_EXCEEDED", f"{size} bytes exceeds the 1 MB per-file limit", rel))
        if path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            diags.append(_err("EXECUTABLE_FILE", "file has an executable permission bit", rel))
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.lower() in MANIFEST_NAMES:
            diags.append(_err("FORBIDDEN_FILE_TYPE", "scripts, executables, binaries, archives and manifests are not allowed", rel))
        if path.suffix != ".md":
            diags.append(_err("RESOURCE_UNSUPPORTED", "only Markdown (.md) files are allowed", rel))
            continue
        data = path.read_bytes()
        if _looks_binary(data):
            diags.append(_err("RESOURCE_UNSUPPORTED", "file is binary, not Markdown text", rel))
            continue
        if data.startswith(b"#!"):
            diags.append(_err("FORBIDDEN_FILE_TYPE", "file starts with a shebang line", rel))
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            diags.append(_err("RESOURCE_UNSUPPORTED", "file is not valid UTF-8", rel))
            continue
        if "�" in text:
            diags.append(_err("RESOURCE_UNSUPPORTED", "file contains replacement characters", rel))
            continue
        sources[rel] = text
    if count > MAX_FILES:
        diags.append(_err("PACKAGE_FILE_COUNT_EXCEEDED", f"{count} files exceeds the 100-file limit"))
    if total > MAX_PACKAGE_BYTES:
        diags.append(_err("PACKAGE_TOTAL_SIZE_EXCEEDED", f"{total} bytes exceeds the 10 MB package limit"))
    return diags, sources


def lint_skill(skill_dir: Path) -> list[Diagnostic]:
    skill_dir = Path(skill_dir)
    diags, sources = check_files(skill_dir)
    skill = sources.get("SKILL.md")
    if skill is None:
        return diags
    fields, body, fm_diags = parse_frontmatter(skill)
    diags += fm_diags
    for pattern, label in REQUIRED_SECTIONS:
        if not pattern.search(body):
            diags.append(_err("SKILL_REQUIRED_SECTION_MISSING", f"missing required '# {label}' section", "SKILL.md"))
    if fields and "name" in fields:
        name = fields["name"]
        if not (NAME_MIN <= len(name) <= NAME_MAX):
            diags.append(_err("SKILL_NAME_LENGTH_INVALID", f"name has {len(name)} characters; 2 to 64 required", "SKILL.md", 2))
        if not NAME_PATTERN.match(name) or not NAME_PATTERN_BRIEF.match(name):
            diags.append(_err("SKILL_NAME_INVALID", "name must be lowercase letters and digits in single-hyphen segments", "SKILL.md", 2))
        elif name != skill_dir.name:
            diags.append(_err("SKILL_NAME_MISMATCH", f"folder name {skill_dir.name!r} differs from name {name!r}", "SKILL.md", 2))
    if fields and "description" in fields:
        description = fields["description"]
        if len(description) > MAX_DESCRIPTION_CHARS:
            diags.append(_err("DESCRIPTION_LENGTH_EXCEEDED", f"description has {len(description)} characters; at most 1024", "SKILL.md", 3))
        if not TRIGGER.search(description):
            diags.append(_warn("DESCRIPTION_TRIGGER_MISSING", "description does not say when to use the skill", "SKILL.md", 3))
    body_lines = body.count("\n") + (0 if body.endswith("\n") or not body else 1)
    if body_lines > BODY_RECOMMENDED_LINES:
        diags.append(_warn("SKILL_BODY_LINES_RECOMMENDATION_EXCEEDED", f"body has {body_lines} lines; 500 recommended", "SKILL.md"))
    links = set(REFERENCE_LINK.findall(skill))
    for rel in sources:
        if rel != "SKILL.md" and rel not in links:
            diags.append(_err("RESOURCE_UNREFERENCED", "reference is not linked directly from SKILL.md", rel))
    for link in sorted(links):
        if link not in sources:
            diags.append(_err("RESOURCE_PATH_INVALID", f"SKILL.md links to a missing reference: {link}", "SKILL.md"))
    for rel, text in sources.items():
        for target in ANY_MD_LINK.findall(text):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            base = (skill_dir / rel).parent
            if not (base / target.split("#", 1)[0]).resolve().is_file():
                diags.append(_err("BROKEN_LINK", f"link target does not exist: {target}", rel))
    delegate_diags, targets, _ = check_delegates(skill)
    diags += delegate_diags
    diags += check_capability_evidence(skill, targets)
    for rel, text in sources.items():
        diags += scan_security(rel, text)
    return diags


def build_zip(skill_dir: Path, zip_path: Path) -> Path:
    """Write a deterministic ZIP with the skill folder as its single top-level entry."""
    skill_dir = Path(skill_dir)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in skill_dir.rglob("*") if p.is_file() and p.name != ".DS_Store")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            arcname = f"{skill_dir.name}/{path.relative_to(skill_dir).as_posix()}"
            info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE)
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return zip_path


def check_zip(zip_path: Path, skill_name: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    size = zip_path.stat().st_size
    if size > MAX_PACKAGE_BYTES:
        diags.append(_err("ZIP_SIZE_EXCEEDED", f"ZIP is {size} bytes; at most 10 MB", zip_path.name))
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(infos) > MAX_FILES:
            diags.append(_err("ZIP_FILE_COUNT_EXCEEDED", f"ZIP holds {len(infos)} entries; at most 100", zip_path.name))
        if sum(i.file_size for i in infos) > MAX_PACKAGE_BYTES:
            diags.append(_err("ZIP_UNCOMPRESSED_SIZE_EXCEEDED", "uncompressed contents exceed 10 MB", zip_path.name))
        for info in infos:
            if info.file_size > MAX_FILE_BYTES:
                diags.append(_err("ZIP_FILE_SIZE_EXCEEDED", f"{info.filename} exceeds 1 MB", zip_path.name))
            if not info.filename.startswith(f"{skill_name}/") or ".." in info.filename or info.filename.startswith("/"):
                diags.append(_err("ZIP_LAYOUT_INVALID", f"unexpected entry {info.filename}", zip_path.name))
            if "__MACOSX" in info.filename or info.filename.endswith(".DS_Store"):
                diags.append(_err("ZIP_LAYOUT_INVALID", f"system file {info.filename}", zip_path.name))
            if info.flag_bits & 0x1:
                diags.append(_err("ZIP_ENCRYPTED", "password-protected entries are prohibited", zip_path.name))
        if f"{skill_name}/SKILL.md" not in names:
            diags.append(_err("ZIP_LAYOUT_INVALID", f"{skill_name}/SKILL.md missing from ZIP", zip_path.name))
    return diags


def run_kit_checker(kit_dir: Path, target: Path) -> tuple[str | None, list[Diagnostic], dict | None]:
    """Run the kit's own checker. Returns (status, diagnostics, raw result); status None when unavailable."""
    checker = kit_dir / "scripts" / "check-skill.mjs"
    node = shutil.which("node")
    if not checker.is_file() or node is None:
        return None, [_warn("KIT_CHECKER_UNAVAILABLE", "kit checker or Node.js not found; only the built-in rules ran")], None
    proc = subprocess.run([node, str(checker), str(target)], capture_output=True, text=True, timeout=120)
    if proc.returncode == 2 or not proc.stdout.strip():
        return "error", [_err("KIT_CHECKER_FAILED", (proc.stderr or "no output").strip())], None
    result = json.loads(proc.stdout)
    diags = []
    for item in result.get("diagnostics", []):
        maker = _err if item.get("severity") == "error" else _warn
        diags.append(maker("KIT_" + item.get("code", "UNKNOWN"), item.get("message", ""), item.get("file", ""), item.get("line")))
    return result.get("status"), diags, result


def verify_kit_archive(vendor_dir: Path) -> list[Diagnostic]:
    archive = vendor_dir / "uliya-skill-kit-0.7.3-en.zip"
    if not archive.is_file():
        return [_warn("KIT_ARCHIVE_MISSING", f"kit archive not found; download it from {KIT_URL}")]
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != KIT_SHA256:
        return [_err("KIT_ARCHIVE_HASH_MISMATCH", f"kit archive SHA-256 is {digest}, expected {KIT_SHA256}")]
    return []


def check_open_blanks(path: Path) -> list[Diagnostic]:
    if not path.is_file():
        return []
    diags = []
    for index, line in enumerate(path.read_text(encoding="utf-8").split("\n")):
        if OPEN_BLANK.search(line):
            diags.append(_warn("DISCLOSURE_BLANK_OPEN", "a [JOSHUA TO FILL] blank is still open", path.name, index + 1))
    return diags


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skill-dir", type=Path, default=DEFAULT_SKILL)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--kit-dir", type=Path, default=DEFAULT_KIT)
    parser.add_argument("--round1", type=Path, default=DEFAULT_ROUND1)
    parser.add_argument("--no-kit", action="store_true", help="skip the kit checker even if available")
    parser.add_argument("--no-zip", action="store_true", help="lint only; do not build the ZIP")
    args = parser.parse_args(argv)

    skill_dir = args.skill_dir.resolve()
    diags = lint_skill(skill_dir)
    diags += check_open_blanks(args.round1)
    if not args.no_kit:
        diags += verify_kit_archive(args.kit_dir.parent.parent)

    zip_path = None
    if not any(d.severity == "error" for d in diags) and not args.no_zip:
        zip_path = build_zip(skill_dir, args.dist / f"{skill_dir.name}.zip")
        diags += check_zip(zip_path, skill_dir.name)

    kit_statuses = []
    if not args.no_kit:
        status, kit_diags, _ = run_kit_checker(args.kit_dir, skill_dir)
        diags += kit_diags
        kit_statuses.append(("source folder", status))
        if zip_path is not None and status is not None:
            with tempfile.TemporaryDirectory() as tmp:
                with zipfile.ZipFile(zip_path) as archive:
                    archive.extractall(tmp)
                status, kit_diags, _ = run_kit_checker(args.kit_dir, Path(tmp) / skill_dir.name)
                diags += kit_diags
                kit_statuses.append(("extracted ZIP", status))

    for diag in diags:
        print(diag.render())
    errors = sum(d.severity == "error" for d in diags)
    warnings = sum(d.severity == "warning" for d in diags)
    for where, status in kit_statuses:
        if status is not None:
            print(f"kit checker ({where}): {status}")
    if zip_path is not None and errors == 0:
        print(f"built {zip_path.relative_to(REPO) if zip_path.is_relative_to(REPO) else zip_path} "
              f"({zip_path.stat().st_size} bytes)")
    print(f"lint: {errors} error(s), {warnings} warning(s)")
    if errors and zip_path is not None and zip_path.exists():
        zip_path.unlink()
        print("removed the ZIP because the lint failed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
