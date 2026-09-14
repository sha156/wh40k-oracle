"""Lossless official MFM price ledger, including conditional/chapter prices.

The operational units table is a datasheet model. This ledger records every
published price even when no corresponding datasheet exists locally. Matching
and extraction coverage are reported separately from price agreement.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path


class _Node:
    def __init__(self, tag="", attrs=(), parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, _Node):
                yield from child.walk()

    def text(self):
        return "".join(c.text() if isinstance(c, _Node) else c for c in self.children).strip()

    def classes(self):
        return set(self.attrs.get("class", "").split())


class _Tree(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.current = self.root
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.current = node

    def handle_endtag(self, tag):
        node = self.current
        while node.parent is not None:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


_COST = re.compile(r"(?:[▲▼]\s*\([+−-]?[\d,]+\)\s*)?([\d,]+)\s+pts")


def _price(node):
    if node.tag != "li":
        return None
    spans = [c for c in node.walk() if c.tag == "span"]
    if len(spans) != 2:
        return None
    match = _COST.fullmatch(spans[1].text())
    if match:
        return spans[0].text(), int(match.group(1).replace(",", ""))
    return None


def parse_source_page(html):
    """Parse actual card containers and independently account for all price rows."""
    from db_compile.mfm import MfmParseBroken, _resolve_rsc_placeholders

    doc = _resolve_rsc_placeholders(html)
    tree = _Tree(doc)
    nodes = list(tree.root.walk())
    raw_prices = [n for n in nodes if n.tag == "li" and re.search(r"\bpts\b", n.text())]
    rows = []
    detachments = []
    section = "UNITS"
    cards = 0
    for node in nodes:
        if node.tag == "h3":
            section = node.text().upper()
        if "print:break-inside-avoid-page" not in node.classes():
            continue
        contents = list(node.walk())
        prices = [n for n in contents if n.tag == "li" and re.search(r"\bpts\b", n.text())]
        if not prices:
            continue
        headers = [n for n in contents if "text-xl" in n.classes()
                   and ("font-bold" in n.classes() or n.tag == "span")]
        if len(headers) != 1:
            raise MfmParseBroken(f"Source card has {len(headers)} names for {len(prices)} price rows")
        unit = headers[0].text()
        detachment = any(n.text() == "ENHANCEMENTS" for n in contents)
        if detachment:
            dp = [int(n.text()[:-2]) for n in contents
                  if n.tag == "span" and re.fullmatch(r"\d+DP", n.text())]
            disposition = [n.text() for n in contents
                           if n.tag == "div" and "background-color" in n.attrs.get("style", "")]
            detachments.append({"name": unit, "dp": dp[0] if len(dp) == 1 else None,
                                "disposition": disposition})
        tier = None
        cards += 1
        for child in contents:
            text = child.text()
            if child.tag == "div" and (re.fullmatch(r"YOUR .+ COSTS?", text) or text == "ENHANCEMENTS"):
                tier = text
            if child in prices:
                price = _price(child)
                if not tier or price is None:
                    raise MfmParseBroken(f"Unparsed source price: {unit}: {text}")
                models, cost = price
                rows.append({"kind": "enhancement" if detachment else "unit",
                             "section": section, "unit": unit, "tier": tier,
                             "models": models, "cost": cost})
    if len(rows) != len(raw_prices):
        raise MfmParseBroken(f"Source coverage mismatch: {len(raw_prices)} price rows, {len(rows)} extracted")
    if not rows:
        raise MfmParseBroken("Source page contains no independently verified prices")
    return {"rows": rows, "cards": cards, "price_rows": len(raw_prices),
            "detachments": detachments}


def load_snapshot(snapshot_dir):
    """Verify raw page hashes and parse a previously downloaded snapshot."""
    root = Path(snapshot_dir)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    pages = {}
    for slug, meta in manifest["pages"].items():
        raw = (root / (slug + ".html")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError(f"Source hash mismatch: {slug}")
        pages[slug] = dict(parse_source_page(raw.decode("utf-8")), **meta)
    return {"fetched_at": manifest["fetched_at"], "pages": pages}


def write_ledger(conn, snapshot):
    """Replace the complete ledger in the caller's transaction, never silently append."""
    conn.execute("""CREATE TABLE IF NOT EXISTS official_mfm_points (
        faction_slug TEXT NOT NULL, ordinal INTEGER NOT NULL, kind TEXT NOT NULL, section TEXT NOT NULL,
        unit_name TEXT NOT NULL, tier TEXT NOT NULL, models TEXT NOT NULL,
        cost INTEGER NOT NULL CHECK(cost >= 0), source_url TEXT NOT NULL,
        source_sha256 TEXT NOT NULL, fetched_at TEXT NOT NULL,
        PRIMARY KEY (faction_slug, ordinal))""")
    conn.execute("DELETE FROM official_mfm_points")
    count = 0
    for slug, page in snapshot["pages"].items():
        for ordinal, row in enumerate(page["rows"]):
            conn.execute("INSERT INTO official_mfm_points VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (slug, ordinal, row["kind"], row["section"], row["unit"], row["tier"],
                          row["models"], row["cost"], page["url"], page["sha256"],
                          snapshot["fetched_at"]))
            count += 1
    return count


def verify_ledger(db_path, snapshot, *, connection=None):
    expected = []
    for slug, page in snapshot["pages"].items():
        for ordinal, row in enumerate(page["rows"]):
            expected.append((slug, ordinal, row["kind"], row["section"], row["unit"], row["tier"],
                             row["models"], row["cost"], page["url"], page["sha256"],
                             snapshot["fetched_at"]))
    if connection is not None:
        actual = list(connection.execute("SELECT * FROM official_mfm_points"))
    else:
        with closing(sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)) as conn:
            actual = list(conn.execute("SELECT * FROM official_mfm_points"))
    return {"source_rows": len(expected), "database_rows": len(actual),
            "equal": sorted(expected) == sorted(actual)}
