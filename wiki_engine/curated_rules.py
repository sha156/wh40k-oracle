"""Reconcile three curated rules against the reviewed retained snapshot.

This is deliberately separate from the chapter and database generators. The
Chinese explanations below were reviewed against these exact sources; a changed
or missing input must fail before publication, rather than reuse stale prose.
No network, LLM, retired cache or newer staged source is used.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Dict

import fitz
import yaml

from wiki_engine.build_outputs import build_log_entry, write_log
from wiki_engine.html_md import html_to_markdown
from wiki_engine.pdf_sections import CONTROL_CHARS
from wiki_engine._io import (GEN_HASHES_NAME, atomic_write_text, load_gen_hashes,
                             save_gen_hashes, text_sha256)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SLUGS = ("cleave", "dark-pact", "oath-of-moment")
REVIEWED_DATE = "2026-10-01"
# Whole-file hashes from the iteration-07 retained PDF/CSV evidence. These are
# snapshot guards, not a claim of coverage of a newer full Codex or official GW
# provenance for the Wahapedia mirror.
SOURCES = {
    "core_en": ("data/Core Rules - New 40K Core Rules.pdf",
                "f6a2443a44627ac5f0ef08407d29aa5ec7e97339998f05bc35f3ae37bf276833"),
    "core_zh": ("data/官方中文/chi_01-06_warhammer40k_new40k_core_rules-gihrxgzhgo-iickazpeog.pdf",
                "18e40276dc81034357d6b7a852b9ce808e0094bc6263e849ef8849b8d210198b"),
    "oath_en": ("data/Faction Pack Space-Marines.pdf",
                "f1f96c0a3dda8dfc2d5686b4aa60e7959697651edbc51f5a344439ff6ac1a1f9"),
    "oath_zh": ("data/官方中文/chi_22-07_warhammer_40,000_faction_pack_space_marines-xd5tub2eai-bf3f24cqu6.pdf",
                "263dfcb8e5b1436a3a008930564f1fc01c4ad2594a8925301ced741b5cc7986b"),
    "csm_pack": ("data/Faction Pack Chaos Space Marines.pdf",
                 "f3a8d05ed88bad5085d014bf76fad684b60336f92cf75cf3aed30b989a33a495"),
    "abilities": ("db_sources/wahapedia/Abilities.csv",
                  "7bcd46ac51565119ab26f2457aa3806b037db9fd87ee2564ef2b07d998caef1e"),
}


def verified_sources(source_root: Path) -> Dict[str, Path]:
    """Preflight every input before reading templates or writing any page."""
    paths = {}
    for key, (relative, expected) in SOURCES.items():
        path = source_root / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Unreviewed curated-rule source: {} (SHA-256 {})".format(path, actual))
        paths[key] = path
    return paths


def _page(path: Path, number: int) -> str:
    with fitz.open(path) as doc:
        return CONTROL_CHARS.sub("", doc[number - 1].get_text())


def _between(text: str, start: str, end: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("Curated-rule extraction boundaries changed: {} / {}".format(start, end))
    body = text.split(start, 1)[1].split(end, 1)[0].strip()
    if not body:
        raise ValueError("Empty curated-rule source text")
    return body


def _prose(text: str, chinese: bool = False) -> str:
    """Remove PDF line wrapping while retaining examples and bullet boundaries."""
    text = text.replace("▪", "\n- ")
    text = re.sub(r"(?m)^\s*(Example:|示例：)", r"\n\n\1", text)
    paragraphs = re.split(r"\n\s*\n|\n(?=- )", text.strip())
    joiner = "" if chinese else " "
    return "\n\n".join(joiner.join(line.strip() for line in p.splitlines() if line.strip())
                        for p in paragraphs if p.strip())


def _dark_pacts(path: Path) -> str:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = [row for row in csv.DictReader(stream, delimiter="|")
                if row["id"] == "000008359" and row["faction_id"] == "CSM"]
    if len(rows) != 1 or rows[0]["name"] != "Dark Pacts":
        raise ValueError("Expected exactly one CSM Dark Pacts identity (000008359)")
    body, warnings = html_to_markdown(rows[0]["description"])
    if not body or warnings:
        raise ValueError("Incomplete Dark Pacts conversion: {}".format(warnings))
    return body


def render_bodies(paths: Dict[str, Path]) -> Dict[str, str]:
    cleave_en = _prose(_between(_page(paths["core_en"], 79), "[CLEAVE] 24.06", "\n79"))
    cleave_zh = _prose(_between(_page(paths["core_zh"], 79), "[劈砍] 24.06", "\n79"), True)
    oath_en = _prose(_between(_page(paths["oath_en"], 60),
                             "Oath of Moment\nChange to:", "\nSpace Marine Chapters"))
    oath_zh = _prose(_between(_page(paths["oath_zh"], 56),
                             "破敌重誓\n改为：", "\n星际战士战团"), True)
    dark = _dark_pacts(paths["abilities"])
    return {
        "cleave": """劈砍按目标单位规模增加攻击骰，要求这把武器的全部攻击只选择一个目标。

## 劈砍 CLEAVE

【劈砍】总是以【劈砍 X】的形式出现。为这把武器收集攻击骰时，若它的全部攻击只选择一个目标，则按选择目标步骤中该单位的模型数，每 5 个模型（向下取整）增加 X 枚攻击骰。

- 例：A 值为 3 的【劈砍 1】武器攻击一个 16 模型单位，增加 3 枚攻击骰，共 6 枚。
- 这里的单一目标要求适用于这把武器的全部攻击。
- 官方 24.05 的【爆炸】也有【爆炸 X】形式，按目标每 5 个模型增加 X 枚攻击骰；24.06 的【劈砍 X】另外明确要求这把武器只选择一个目标。两条规则应分别按官方正文使用。

## 官方中文原文 · 核心规则 p79 / 24.06

{cleave_zh}

<details>
<summary>官方英文原文 · Core Rules p79 / 24.06</summary>

{cleave_en}

</details>
""".format(cleave_zh=cleave_zh, cleave_en=cleave_en),
        "dark-pact": """混沌星际战士军队规则：向黑暗神明立约，冒领导力风险换武器增益。

## 黑暗契约 DARK PACTS

以下完整规则来自保留的 Wahapedia 结构化镜像 Abilities.csv，CSM 阵营、ID 000008359。Wahapedia 是规则镜像，不是 GW 官方出版物；此处保留英文，不提供未经核实的官方中文全文。

{dark}

## 官方阵营包上下文

保留的官方 Faction Pack Chaos Space Marines 第 37 页列出分队和兵牌更新。包内其他条目引用黑暗契约并调整其交互，但这些内容不构成完整军队规则。完整正文的来源是上面的 Wahapedia 镜像，不能将第 37 页标为完整正文的官方出处。
""".format(dark=dark),
        "oath-of-moment": """破敌重誓是星际战士军队规则：点名一个敌方单位，拥有本能力的模型攻击它时可以重投命中。

## 破敌重誓 OATH OF MOMENT

依据本地保留的官方 Faction Pack Space Marines 英文第 60 页、中文第 56 页：

如果你的军队阵营是阿斯塔特修会（ADEPTUS ASTARTES），在你的指挥阶段开始时，从对手军队中选择一个单位。直到你的下个指挥阶段开始时，该单位是破敌重誓目标。你军队中拥有本能力的模型每次攻击该目标时：

- 可以重投命中骰；
- 如果使用 Codex: Space Marines 分队，且军队既不含圣血天使、暗黑天使、死亡守望、太空野狼关键词单位，也不含 MFM 中归在这四个阵营分类下的单位，则造伤骰还 +1。组军时须同时核对关键词和 MFM 阵营分类。

## 保留的官方中英文本对照

保留的官方中文第 56 页与英文第 60 页都包含目标选择时机、持续时间、重投命中，以及 Codex 分队、四个战团关键词和 MFM 分类条件。这个对照限于本地保留的两份文件，不表明它们是相邻发布的版本，也不证明新完整 Codex 的覆盖范围。

> 部分汉化版本将这一阵营能力译作“誓言时刻”“忠诚誓言”“破敌誓言”等，均指同一枚 Oath of Moment 能力。

## 官方中文原文 · Faction Pack p56

{oath_zh}

<details>
<summary>官方英文原文 · Faction Pack p60</summary>

{oath_en}

</details>
""".format(oath_zh=oath_zh, oath_en=oath_en),
    }


def generate_all(wiki_root: Path, source_root: Path = PROJECT_ROOT) -> dict:
    """Update only the three existing slugs; preserve identity/aliases/other fields.

    All inputs and all existing page identities are validated before the first
    write. Source drift must be independently reviewed before updating the guard.
    Running twice makes no further page or log change.
    """
    paths = verified_sources(source_root)
    bodies = render_bodies(paths)
    root = wiki_root.resolve()
    log_path = wiki_root / "log.md"
    log_path.resolve().relative_to(root)
    (wiki_root / GEN_HASHES_NAME).resolve().relative_to(root)
    gen_hashes = load_gen_hashes(wiki_root)
    sources = {
        "cleave": [
            {"book": "Core Rules - New 40K Core Rules", "pages": [79, "24.06"]},
            {"book": "官方中文核心规则（GW 简体中文下载版）", "pages": [79, "24.06"]},
        ],
        "dark-pact": [
            {"book": "Wahapedia structured mirror: Abilities.csv (CSM, ID 000008359; not GW official)",
             "pages": ["CSM/000008359"]},
            {"book": "Faction Pack Chaos Space Marines (official context, not full army rule)",
             "pages": [37]},
        ],
        "oath-of-moment": [
            {"book": "Faction Pack Space-Marines", "pages": [60]},
            {"book": SOURCES["oath_zh"][0][5:-4], "pages": [56]},
        ],
    }
    pending = []
    for slug in SLUGS:
        path = wiki_root / "core-rules" / (slug + ".md")
        path.resolve().relative_to(root)
        previous = path.read_text(encoding="utf-8")
        rel = path.relative_to(wiki_root).as_posix()
        if rel in gen_hashes and gen_hashes[rel] != text_sha256(previous):
            raise ValueError("Curated-rule manual edit requires review: {}".format(path))
        parts = previous.split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError("Missing curated-rule frontmatter: {}".format(path))
        fm = yaml.safe_load(parts[1])
        if not isinstance(fm, dict) or fm.get("id") != slug or fm.get("type") != "core-rule":
            raise ValueError("Unexpected curated-rule identity: {}".format(path))
        fm["sources"] = sources[slug]
        fm["updated"] = REVIEWED_DATE
        if slug == "dark-pact":
            fm["version"] = dict(fm.get("version") or {})
            fm["version"]["rules"] = "Retained Wahapedia CSM mirror (full text); official pack context separate"
        content = "---\n{}---\n\n{}".format(
            yaml.safe_dump(fm, allow_unicode=True, sort_keys=False), bodies[slug])
        if content != previous:
            pending.append((path, content))
    for path, content in pending:
        atomic_write_text(path, content)
    changed = [path.relative_to(wiki_root).as_posix() for path, _ in pending]
    if changed:
        for path, content in pending:
            gen_hashes[path.relative_to(wiki_root).as_posix()] = text_sha256(content)
        save_gen_hashes(wiki_root, gen_hashes)
        write_log(log_path, build_log_entry(
            "rebuild", "Curated retained-source rules: {}".format(", ".join(SLUGS)), changed))
    return {"reviewed": len(SLUGS), "written": len(changed), "changed": changed,
            "source_sha256": {key: digest for key, (_, digest) in SOURCES.items()}}
