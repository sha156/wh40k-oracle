# tests/test_db_compile_mfm.py
"""mfm：官方 Munitorum Field Manual 页面解析 + 与库内点数比对（离线 fixture）。"""
import json
import sqlite3

import pytest

from db_compile.mfm import check_points, is_base_tier, parse_mfm_html

# 模拟 MFM 阵营页：RSC 占位符回填 + 2026 梯度点数（同一单位第 N 份价格不同）
_UNIT = (
    '<div class="px-1 py-0.5 bg-slate-500 dark:bg-slate-800 font-bold text-xl text-white">'
    '{name}</div>'
)
_TIER = (
    '<div class="bg-slate-200 dark:bg-slate-600 px-1 py-0.5 font-bold text-black '
    'dark:text-white">{tier}</div><ul class="leaders bg-yellow">{lis}</ul>'
)
_LI = '<li><span>{models}</span><template id="P:{pid}"></template></li>'
_SEG = '<div hidden id="S:{pid}"><span>{pts} pts</span></div><script>$RS("S:{pid}","P:{pid}")</script>'
# 真实页面首个隐藏段的 script 带函数定义前缀——解析器必须也能吃这种
_SEG_FN = ('<div hidden id="S:{pid}"><span>{pts} pts</span></div>'
           '<script>$RS=function(a,b){{a=1}};$RS("S:{pid}","P:{pid}")</script>')

FIXTURE_HTML = (
    "<html><body>"
    '<h3 class="text-4xl font-header p-1">UNITS</h3>'
    + _UNIT.format(name="INTERCESSOR SQUAD")
    + _TIER.format(tier="YOUR UNIT COSTS",
                   lis=_LI.format(models="5 models", pid="8")
                       + _LI.format(models="10 models", pid="9"))
    + _UNIT.format(name="CASTIGATOR")
    + _TIER.format(tier="YOUR 1ST TO 2ND UNITS COST",
                   lis=_LI.format(models="1 model", pid="a"))
    + _TIER.format(tier="YOUR 3RD + UNIT COSTS",
                   lis=_LI.format(models="1 model", pid="b"))
    # 借调价小节：同名单位另一套价，必须被排除（真实页面如 Imperial Agents）
    + '<h3 class="text-3xl font-header p-1">EVERY MODEL HAS THE <b>IMPERIUM</b> KEYWORD</h3>'
    + _UNIT.format(name="INTERCESSOR SQUAD")
    + _TIER.format(tier="YOUR UNIT COSTS",
                   lis='<li><span>5 models</span><span>999 pts</span></li>')
    + _SEG_FN.format(pid="8", pts=80) + _SEG.format(pid="9", pts=150)
    + _SEG.format(pid="a", pts=165) + _SEG.format(pid="b", pts=175)
    # 无对应占位符的孤儿段（模拟被切掉小节的段）：内容不得泄漏为前一单位的档位
    + '<div hidden id="S:ff"><div class="space-y-1"><div class="bg-slate-200 x '
      'font-bold x">YOUR 1ST UNIT COSTS</div><ul><li><span>1 model</span>'
      '<span>888 pts</span></li></ul></div></div><script>$RS("S:ff","P:ff")</script>'
    + "</body></html>"
)


class TestParseMfmHtml:
    def test_resolves_placeholders_and_extracts_rows(self):
        rows = parse_mfm_html(FIXTURE_HTML)
        assert ("INTERCESSOR SQUAD", "YOUR UNIT COSTS", "5 models", 80) in rows
        assert ("INTERCESSOR SQUAD", "YOUR UNIT COSTS", "10 models", 150) in rows

    def test_captures_tiered_pricing_separately(self):
        # 2026 梯度机制：同一单位第 1-2 份 165、第 3+ 份 175，必须分行不混
        rows = parse_mfm_html(FIXTURE_HTML)
        assert ("CASTIGATOR", "YOUR 1ST TO 2ND UNITS COST", "1 model", 165) in rows
        assert ("CASTIGATOR", "YOUR 3RD + UNIT COSTS", "1 model", 175) in rows

    def test_empty_html_returns_empty(self):
        assert parse_mfm_html("<html></html>") == []

    def test_allied_pricing_section_excluded(self):
        # 借调价小节（EVERY MODEL HAS THE ... KEYWORD）里的 999 不得混入
        rows = parse_mfm_html(FIXTURE_HTML)
        assert all(pts != 999 for _u, _t, _m, pts in rows)

    def test_leftover_hidden_segments_do_not_pollute_previous_unit(self):
        # 隐藏段源块必须删除（浏览器 $RS 是搬运不是复制）——孤儿段的 888
        # 不得被算到它前面那个单位头上（真实案例：War Dog Stalker 395/415）
        rows = parse_mfm_html(FIXTURE_HTML)
        assert all(pts != 888 for _u, _t, _m, pts in rows)


# 2026-07 MFM 改版：变价单位表头改成色块（emerald 降价 / red 涨价 / amber 重构），
# 名字挪进 <span class="text-xl keep-all">；分数档加 class 着色 + ▲/▼ (±N) 变动标记前缀。
# 旧解析器只认 slate 表头 + 裸 pts span，会静默丢掉整批变价单位（fetch 最该抓到的那批）。
_UNIT_COLORED = (
    '<div class="flex flex-row justify-between px-1 py-0.5 {color} font-bold '
    'text-white"><span class="text-xl keep-all">{name}</span>'
    '<span class="text-sm self-end pl-2 text-nowrap">▼</span></div>'
)
_LI_MARKED = (
    '<li><span>{models}</span><span class="{color}">{arrow} ({delta}) '
    '{pts} pts</span></li>'
)


class TestParseMfmHtmlNewFormat:
    """2026-07 改版后色块表头 + 变动标记分数档的解析（回归）。"""

    def _html(self):
        return (
            "<html><body>"
            '<h3 class="text-4xl font-header p-1">UNITS</h3>'
            # 降价单位（emerald 表头 + ▼ 标记）——旧解析器完全丢失
            + _UNIT_COLORED.format(color="bg-emerald-600", name="ANGRON")
            + _TIER.format(tier="YOUR UNIT COSTS",
                           lis=_LI_MARKED.format(models="1 model",
                                                 color="text-emerald-600",
                                                 arrow="▼", delta="-20", pts=330))
            # 涨价单位（red 表头 + ▲ 标记）
            + _UNIT_COLORED.format(color="bg-red-500", name="DEFILER")
            + _TIER.format(tier="YOUR 2ND + UNIT COSTS",
                           lis=_LI_MARKED.format(models="1 model",
                                                 color="text-red-500",
                                                 arrow="▲", delta="+10", pts=310))
            # 未变价单位仍走旧式 slate 表头 + 裸 pts span（新旧必须共存）
            + _UNIT.format(name="CHAOS SPAWN")
            + _TIER.format(tier="YOUR UNIT COSTS",
                           lis='<li><span>1 model</span><span>65 pts</span></li>')
            + "</body></html>"
        )

    def test_colored_header_decrease_unit_captured(self):
        rows = parse_mfm_html(self._html())
        assert ("ANGRON", "YOUR UNIT COSTS", "1 model", 330) in rows

    def test_colored_header_increase_unit_captured(self):
        rows = parse_mfm_html(self._html())
        assert ("DEFILER", "YOUR 2ND + UNIT COSTS", "1 model", 310) in rows

    def test_old_style_units_still_parse_alongside(self):
        rows = parse_mfm_html(self._html())
        assert ("CHAOS SPAWN", "YOUR UNIT COSTS", "1 model", 65) in rows

    def test_marker_delta_not_mistaken_for_points(self):
        # ▼ (-20) 的 20 不得被当成分数——只取末尾 330
        rows = parse_mfm_html(self._html())
        assert all(pts not in (20, 10) for _u, _t, _m, pts in rows)


class TestParseMfmHtmlThousandsSeparator:
    """四位数分数官网写作 `2,200 pts`；旧 `(\\d+)` 正则对它零容忍且不报错。

    真实后果：泰坦军团（全部单位都是四位数）两页常年解析出 0 行，缓存里是空 list，
    `mfm --check` 因此从未覆盖库内 7 个 ≥1000 分单位（4 泰坦 + 灵族幽魂/幻影泰坦
    + 钛族 Manta）。fixture 取自 2026-07-27 抓下来的真实 titan-legions 页形态。
    """

    def _html(self, lis):
        return ("<html><body>"
                '<h3 class="text-4xl font-header p-1">UNITS</h3>'
                + _UNIT.format(name="WARLORD TITAN")
                + _TIER.format(tier="YOUR UNIT COSTS", lis=lis)
                + "</body></html>")

    def test_four_digit_points_with_comma_parsed(self):
        rows = parse_mfm_html(self._html(
            '<li><span>1 model</span><span>3,500 pts</span></li>'))
        assert rows == [("WARLORD TITAN", "YOUR UNIT COSTS", "1 model", 3500)]

    def test_comma_form_also_works_on_colored_marked_tier(self):
        # 变价档（色块 + ▲/▼ 标记）同样可能是四位数
        rows = parse_mfm_html(self._html(
            '<li><span>1 model</span><span class="text-red-500">'
            '▲ (+100) 2,600 pts</span></li>'))
        assert rows == [("WARLORD TITAN", "YOUR UNIT COSTS", "1 model", 2600)]

    def test_plain_digits_still_parse(self):
        # 负向成对：三位数裸数字（官网多数单位）不得被逗号形态挤掉
        rows = parse_mfm_html(self._html(
            '<li><span>1 model</span><span>330 pts</span></li>'))
        assert rows == [("WARLORD TITAN", "YOUR UNIT COSTS", "1 model", 330)]


class TestSilentParseFailureDetection:
    """「有单位表头却 0 条分数」= 解析器对该页断裂，必须与「该阵营没单位」分开。

    只看行数分辨不出这两者——泰坦军团两页 0 行伪装成空阵营，混过了
    fetch 的新旧缓存掉行对账（0→0 不算掉行），才会一直没人发现。
    """

    def _page(self, pts_span):
        return ("<html><body>"
                '<h3 class="text-4xl font-header p-1">UNITS</h3>'
                + _UNIT.format(name="WARHOUND TITAN")
                + _TIER.format(tier="YOUR UNIT COSTS",
                               lis='<li><span>1 model</span>'
                                   + pts_span + '</li>')
                + "</body></html>")

    def test_headers_counted_independently_of_price_rows(self):
        from db_compile.mfm import count_unit_headers

        broken = self._page('<span>1 100 kredits</span>')  # 认不出的分数形态
        assert count_unit_headers(broken) == 1
        assert parse_mfm_html(broken) == []

    def test_pageless_html_has_no_headers(self):
        from db_compile.mfm import count_unit_headers

        # 负向成对：真的没有单位的页面 0 表头 0 行 —— 不该被判断裂
        assert count_unit_headers("<html></html>") == 0

    def test_fetch_faction_raises_on_headers_without_rows(self, monkeypatch):
        import db_compile.mfm as mfm

        monkeypatch.setattr(mfm, "_fetch",
                            lambda url, timeout=40: self._page(
                                '<span>1 100 kredits</span>'))
        monkeypatch.setattr(mfm.time, "sleep", lambda s: None)
        with pytest.raises(mfm.MfmParseBroken, match="解析器对该页断裂"):
            mfm.fetch_faction("titan-legions", max_retries=2)

    def test_fetch_faction_ok_when_rows_parse(self, monkeypatch):
        import db_compile.mfm as mfm

        monkeypatch.setattr(mfm, "_fetch",
                            lambda url, timeout=40: self._page(
                                '<span>1,100 pts</span>'))
        monkeypatch.setattr(mfm.time, "sleep", lambda s: None)
        rows = mfm.fetch_faction("titan-legions", max_retries=2)
        assert rows == [("WARHOUND TITAN", "YOUR UNIT COSTS", "1 model", 1100)]

    def test_fetch_all_refuses_to_write_broken_cache(self, tmp_path, monkeypatch):
        import db_compile.mfm as mfm

        home = '<a href="/en/titan-legions">t</a>'
        broken = self._page('<span>1 100 kredits</span>')
        monkeypatch.setattr(
            mfm, "_fetch",
            lambda url, timeout=40: home if url.endswith("/en") else broken)
        monkeypatch.setattr(mfm.time, "sleep", lambda s: None)
        out = tmp_path / "mfm.json"
        with pytest.raises(RuntimeError, match="解析断裂"):
            mfm.fetch_all(out, sleep_s=0, max_retries=1)
        assert not out.exists()  # 断裂页不许写成「这个阵营没单位」

    def test_fetch_all_force_writes_and_records_parse_broken(
            self, tmp_path, monkeypatch):
        import db_compile.mfm as mfm

        home = '<a href="/en/titan-legions">t</a>'
        broken = self._page('<span>1 100 kredits</span>')
        monkeypatch.setattr(
            mfm, "_fetch",
            lambda url, timeout=40: home if url.endswith("/en") else broken)
        monkeypatch.setattr(mfm.time, "sleep", lambda s: None)
        out = tmp_path / "mfm.json"
        mfm.fetch_all(out, sleep_s=0, max_retries=1, force=True)
        saved = json.loads(out.read_text(encoding="utf-8"))
        # --force 放行也要留痕，不能让断裂在缓存里查无此事
        assert saved["parse_broken"] and "titan-legions" in saved["parse_broken"][0]
        assert saved["failed"] == []  # 解析断裂不冒充网络失败


class TestIsBaseTier:
    def test_base_tiers(self):
        assert is_base_tier("YOUR UNIT COSTS")
        assert is_base_tier("YOUR 1ST UNIT COSTS")
        assert is_base_tier("YOUR 1ST TO 2ND UNITS COST")

    def test_surcharge_tiers(self):
        assert not is_base_tier("YOUR 3RD + UNIT COSTS")
        assert not is_base_tier("YOUR 2ND + UNIT COSTS")


def _make_db(tmp_path):
    db = tmp_path / "wh40k.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
        "points_json TEXT,keywords_json TEXT,version TEXT)")
    conn.execute(
        "INSERT INTO units VALUES('1','SM','Intercessor Squad',NULL,?,NULL,NULL)",
        (json.dumps({"points": 160, "items": [
            {"line": "1", "desc": "5 models", "cost": 80},
            {"line": "2", "desc": "10 models", "cost": 160},  # MFM 现为 150 → 应报差异
        ]}),))
    conn.execute(
        "INSERT INTO units VALUES('2','SM','Castigator',NULL,?,NULL,NULL)",
        (json.dumps({"points": 165, "items": [
            {"line": "1", "desc": "1 model", "cost": 165}]}),))  # 与基准梯度一致
    conn.commit()
    conn.close()
    return db


class TestCheckPoints:
    # {slug: rows}：space-marines 页 + sororitas 页（Castigator 属 AS，但 fixture 单位都挂 SM，
    # 故这里全走 space-marines 页以命中 faction_id='SM'）
    MFM_FACTIONS = {
        "space-marines": [
            ("INTERCESSOR SQUAD", "YOUR UNIT COSTS", "5 models", 80),
            ("INTERCESSOR SQUAD", "YOUR UNIT COSTS", "10 models", 150),
            ("CASTIGATOR", "YOUR 1ST TO 2ND UNITS COST", "1 model", 165),
            ("CASTIGATOR", "YOUR 3RD + UNIT COSTS", "1 model", 175),
        ],
    }

    def test_compares_base_tier_only(self, tmp_path):
        rep = check_points(_make_db(tmp_path), self.MFM_FACTIONS)
        # 加价档（3RD+）不参与比对：可比 = 2(Intercessor) + 1(Castigator 基准)
        assert rep["compared"] == 3
        assert rep["agree"] == 2  # 5 models=80 一致 + Castigator 165 一致
        assert len(rep["diffs"]) == 1
        d = rep["diffs"][0]
        assert (d["unit"], d["models"], d["db"], d["mfm"]) == (
            "Intercessor Squad", "10 models", 160, 150)

    def test_tiered_units_reported(self, tmp_path):
        rep = check_points(_make_db(tmp_path), self.MFM_FACTIONS)
        assert rep["tiered_units"] == ["CASTIGATOR"]

    def test_mfm_units_missing_in_db_counted(self, tmp_path):
        rep = check_points(
            _make_db(tmp_path),
            {"space-marines": [("NO SUCH UNIT", "YOUR UNIT COSTS", "1 model", 50)]})
        assert rep["compared"] == 0
        assert rep["mfm_only"] == ["NO SUCH UNIT"]

    def test_faction_scoped_matching_no_cross_faction_pollution(self, tmp_path):
        # 跨阵营同名不同价（如 Ministorum Priest）：各按所属阵营比对，互不污染
        db = _make_db(tmp_path)
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO units VALUES('3','AS','Shared Priest',NULL,?,NULL,NULL)",
            (json.dumps({"points": 50, "items": [
                {"line": "1", "desc": "1 model", "cost": 50}]}),))
        conn.execute(
            "INSERT INTO units VALUES('4','AM','Shared Priest',NULL,?,NULL,NULL)",
            (json.dumps({"points": 35, "items": [
                {"line": "1", "desc": "1 model", "cost": 35}]}),))
        conn.commit(); conn.close()
        rep = check_points(db, {
            "adepta-sororitas": [("SHARED PRIEST", "YOUR UNIT COSTS", "1 model", 50)],
            "astra-militarum": [("SHARED PRIEST", "YOUR UNIT COSTS", "1 model", 35)],
        })
        assert rep["compared"] == 2
        assert rep["agree"] == 2  # 各自阵营价都对——名字级混比会误报

    def test_duplicate_rows_same_faction_all_checked(self, tmp_path):
        # 同阵营同名两行（Wahapedia 跨战团重复收录，如 SM Impulsor×2）、其中一行
        # 残留旧值 → 必须报不符。旧 dict 实现 last-write-wins 只看最后一行：
        # 旧值行在前、新值行在后时恰好漏检（与 apply_points 的 list 结构不对称）。
        db = _make_db(tmp_path)
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO units VALUES('10','SM','Impulsor',NULL,?,NULL,NULL)",
            (json.dumps({"points": 90, "items": [
                {"line": "1", "desc": "1 model", "cost": 90}]}),))  # 旧值（在前）
        conn.execute(
            "INSERT INTO units VALUES('11','SM','Impulsor',NULL,?,NULL,NULL)",
            (json.dumps({"points": 80, "items": [
                {"line": "1", "desc": "1 model", "cost": 80}]}),))  # 新值（在后）
        conn.commit(); conn.close()
        rep = check_points(db, {"space-marines": [
            ("IMPULSOR", "YOUR UNIT COSTS", "1 model", 80)]})
        imp_diffs = [d for d in rep["diffs"] if d["unit"] == "Impulsor"]
        assert len(imp_diffs) == 1  # 旧值行被逮到，不被新值行遮蔽
        assert (imp_diffs[0]["db"], imp_diffs[0]["mfm"]) == (90, 80)

    def test_generic_sm_page_wins_over_chapter_page(self, tmp_path):
        # 战团页（black-templars 85）不覆盖通用页（space-marines 100）
        db = _make_db(tmp_path)
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO units VALUES('5','SM','Sternguard',NULL,?,NULL,NULL)",
            (json.dumps({"points": 100, "items": [
                {"line": "1", "desc": "5 models", "cost": 100}]}),))
        conn.commit(); conn.close()
        rep = check_points(db, {
            "black-templars": [("STERNGUARD", "YOUR UNIT COSTS", "5 models", 85)],
            "space-marines": [("STERNGUARD", "YOUR UNIT COSTS", "5 models", 100)],
        })
        stern = [d for d in rep["diffs"] if d["unit"] == "Sternguard"]
        assert stern == []  # 通用页 100 与库一致，战团价不参与


class TestSubFactionSectionCoverage:
    """非主小节的两种相反语义必须靠**数据**区分，不靠小节名（2026-07-27 覆盖缺口）。

    旧实现整段切除 UNITS/FORTIFICATIONS 之外的小节，把 38 个「阵营自己的单位列在
    子标题下」（基里曼在 space-marines 页的 ULTRAMARINES 小节里）一起误伤——
    和千分位丢行同一个失效模式：不报错、指标好看、覆盖面无声塌掉。
    """

    def _page(self, sections):
        """sections = [(h3 标题, [(单位名, 模型数, 分数)])] → 页面 HTML。"""
        out = ["<html><body>"]
        for title, units in sections:
            out.append(f'<h3 class="text-4xl font-header p-1">{title}</h3>')
            for name, models, pts in units:
                out.append(_UNIT.format(name=name))
                out.append(_TIER.format(
                    tier="YOUR UNIT COSTS",
                    lis=f"<li><span>{models}</span>"
                        f"<span>{pts} pts</span></li>"))
        return "".join(out) + "</body></html>"

    def test_sub_faction_section_units_are_kept(self):
        # ULTRAMARINES 小节里的单位主小节没有 ⇒ 是该阵营自己的单位，必须收
        html = self._page([
            ("UNITS", [("INTERCESSOR SQUAD", "5 models", 75)]),
            ("ULTRAMARINES", [("ROBOUTE GUILLIMAN", "1 model", 355)]),
        ])
        rows = parse_mfm_html(html)
        assert ("ROBOUTE GUILLIMAN", "YOUR UNIT COSTS", "1 model", 355) in rows

    def test_second_price_for_already_priced_unit_is_dropped(self):
        # 负向成对：主小节已定过价的单位，小节里的第二套价（条件价）必须丢
        html = self._page([
            ("UNITS", [("INQUISITOR", "1 model", 55)]),
            ("EVERY MODEL HAS THE IMPERIUM KEYWORD",
             [("INQUISITOR", "1 model", 65)]),
        ])
        rows = parse_mfm_html(html)
        assert ("INQUISITOR", "YOUR UNIT COSTS", "1 model", 55) in rows
        assert all(pts != 65 for _u, _t, _m, pts in rows)

    def test_both_semantics_resolved_on_one_page(self):
        # 同一页同时有两种语义时各判各的——这正是靠小节名猜会翻车的地方
        html = self._page([
            ("UNITS", [("INQUISITOR", "1 model", 55)]),
            ("EVERY MODEL HAS THE IMPERIUM KEYWORD",
             [("INQUISITOR", "1 model", 65), ("NAVIGATOR", "1 model", 75)]),
        ])
        names = {u for u, _t, _m, _p in parse_mfm_html(html)}
        assert names == {"INQUISITOR", "NAVIGATOR"}
        assert ("NAVIGATOR", "YOUR UNIT COSTS", "1 model", 75) in parse_mfm_html(html)

    def test_headerless_page_still_parsed_whole(self):
        # 异常版式（一个 h3 都没有）仍整篇当主小节，宁多勿漏
        html = (_UNIT.format(name="LONE UNIT")
                + _TIER.format(tier="YOUR UNIT COSTS",
                               lis="<li><span>1 model</span>"
                                   "<span>40 pts</span></li>"))
        assert parse_mfm_html(html) == [
            ("LONE UNIT", "YOUR UNIT COSTS", "1 model", 40)]

    def test_header_count_does_not_share_section_filtering(self):
        # count_unit_headers 必须**不走**小节筛选：校验器和被校验对象共享前提
        # 就会一起瞎（旧版跟着切小节，所以对整段误伤全无感知）
        from db_compile.mfm import count_unit_headers

        html = self._page([
            ("UNITS", [("INQUISITOR", "1 model", 55)]),
            ("EVERY MODEL HAS THE IMPERIUM KEYWORD",
             [("INQUISITOR", "1 model", 65)]),
        ])
        assert count_unit_headers(html) == 2   # 两个表头都数进来
        assert len(parse_mfm_html(html)) == 1  # 但只留主小节那一套价

    def test_chapter_page_bulk_reprint_does_not_beat_generic_page(self, tmp_path):
        # 战团页把通用 SM 名录整段重渲染（BA 页 'SPACE MARINES' 小节 84 个单位），
        # 这些单位在**战团页自己的**主小节里没有，故会被本页规则收下——
        # 跨页那一层由 _rows_by_faction 的「通用页优先」收敛，战团差异价不得夺权
        db = _make_db(tmp_path)
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO units VALUES('6','SM','Assault Intercessor Squad',"
            "NULL,?,NULL,NULL)",
            (json.dumps({"points": 75, "items": [
                {"line": "1", "desc": "5 models", "cost": 75}]}),))
        conn.commit(); conn.close()
        chapter = self._page([
            ("UNITS", [("DEATH COMPANY MARINES", "5 models", 100)]),
            ("SPACE MARINES", [("ASSAULT INTERCESSOR SQUAD", "5 models", 80)]),
        ])
        chapter_rows = parse_mfm_html(chapter)
        # 本页规则确实收下了它（战团差异价保留在 mfm json 里备用）
        assert ("ASSAULT INTERCESSOR SQUAD", "YOUR UNIT COSTS",
                "5 models", 80) in chapter_rows
        rep = check_points(db, {
            "blood-angels": chapter_rows,
            "space-marines": [("ASSAULT INTERCESSOR SQUAD",
                               "YOUR UNIT COSTS", "5 models", 75)],
        })
        assert rep["diffs"] == []  # 通用页 75 与库一致，战团 80 不参与比对


class TestNameNormalizationMatching:
    """精确名匹配失败后的兜底：单复数归一 + 显式别名 + 唯一命中护栏（回归）。

    背景：官网 MFM "VYPER"/"WARTRAKK" 对不上库里 "Vypers"/"Wartrakks"，过期分数
    被静默归入 mfm_only 而非 diffs——精确名匹配对单复数零容忍是更新的隐性漏检口。
    """

    def _db_singular_mfm_plural(self, tmp_path):
        db = tmp_path / "wh40k.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT)")
        # 库内复数名 Vypers，2 models 残留旧值 150（官方现为 140）
        conn.execute(
            "INSERT INTO units VALUES('1','AE','Vypers',NULL,?,NULL,NULL)",
            (json.dumps({"points": 225, "items": [
                {"line": "1", "desc": "1 model", "cost": 75},
                {"line": "2", "desc": "2 models", "cost": 150}]}),))
        conn.commit(); conn.close()
        return db

    # 官方页写单数 VYPER，库内是复数 Vypers
    MFM = {"aeldari": [
        ("VYPER", "YOUR UNIT COSTS", "1 model", 75),
        ("VYPER", "YOUR UNIT COSTS", "2 models", 140)]}

    def test_singular_plural_stale_now_detected_by_check(self, tmp_path):
        rep = check_points(self._db_singular_mfm_plural(tmp_path), self.MFM)
        assert "VYPER" not in rep["mfm_only"]  # 不再漏进 mfm_only
        stale = [d for d in rep["diffs"] if d["models"] == "2 models"]
        assert len(stale) == 1 and (stale[0]["db"], stale[0]["mfm"]) == (150, 140)

    def test_singular_plural_applied(self, tmp_path):
        from db_compile.mfm import apply_points
        db = self._db_singular_mfm_plural(tmp_path)
        apply_points(db, self.MFM, fetched_at="2026-07-23")
        conn = sqlite3.connect(str(db))
        pj = json.loads(conn.execute(
            "SELECT points_json FROM units WHERE name_en='Vypers'").fetchone()[0])
        conn.close()
        costs = {it["desc"]: it["cost"] for it in pj["items"]}
        assert costs["2 models"] == 140  # 归一匹配后 apply 成功刷新

    def test_variant_label_does_not_pollute_base_unit(self, tmp_path):
        # ERADICATOR SQUAD WITH HEAVY BOLTERS(80) 是独立装配，不得错配到基础
        # Eradicator Squad(90)——归一后名字仍不同，应留在 mfm_only 不动基础价
        db = tmp_path / "wh40k.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT)")
        conn.execute(
            "INSERT INTO units VALUES('1','SM','Eradicator Squad',NULL,?,NULL,NULL)",
            (json.dumps({"points": 90, "items": [
                {"line": "1", "desc": "3 models", "cost": 90}]}),))
        conn.commit(); conn.close()
        rep = check_points(db, {"space-marines": [
            ("ERADICATOR SQUAD WITH HEAVY BOLTERS", "YOUR UNIT COSTS",
             "3 models", 80)]})
        assert rep["mfm_only"] == ["ERADICATOR SQUAD WITH HEAVY BOLTERS"]
        assert rep["diffs"] == []  # 基础 90 未被 80 污染

    def test_ambiguous_normalization_not_matched(self, tmp_path):
        # 归一后同阵营两个候选（Ravager / Ravagers 同时存在）→ 拒绝兜底，避免错配
        db = tmp_path / "wh40k.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT)")
        for uid, nm, cost in [("1", "Ravager", 100), ("2", "Ravagers", 110)]:
            conn.execute(
                "INSERT INTO units VALUES(?,'DRU',?,NULL,?,NULL,NULL)",
                (uid, nm, json.dumps({"points": cost, "items": [
                    {"line": "1", "desc": "1 model", "cost": cost}]})))
        conn.commit(); conn.close()
        # MFM 写 "RAVAGERZ"（都不精确命中）→ 归一 ravagerz≠ravager，且即便撞也两候选
        rep = check_points(db, {"drukhari": [
            ("RAVAGERR", "YOUR UNIT COSTS", "1 model", 120)]})
        assert "RAVAGERR" in rep["mfm_only"]  # 有歧义时安全跳过，不乱配

    def test_explicit_alias_resolves(self, tmp_path, monkeypatch):
        # 归一兜不住的不规则改名走显式别名表
        import db_compile.mfm as mfm
        monkeypatch.setattr(mfm, "_MFM_NAME_ALIASES", {"old mfm name": "New DB Name"})
        db = tmp_path / "wh40k.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT)")
        conn.execute(
            "INSERT INTO units VALUES('1','ORK','New DB Name',NULL,?,NULL,NULL)",
            (json.dumps({"points": 50, "items": [
                {"line": "1", "desc": "1 model", "cost": 50}]}),))
        conn.commit(); conn.close()
        rep = check_points(db, {"orks": [
            ("OLD MFM NAME", "YOUR UNIT COSTS", "1 model", 60)]})
        assert "OLD MFM NAME" not in rep["mfm_only"]
        assert len(rep["diffs"]) == 1 and rep["diffs"][0]["mfm"] == 60


class TestFetchAll:
    def test_reuses_fetch_faction_and_records_failures(self, tmp_path, monkeypatch):
        # fetch_all 的单页抓取已收敛到 fetch_faction（不再有第二份参数不一致的
        # 内联重试循环）；单阵营抓不下来记入 failed 继续，不炸整轮
        import db_compile.mfm as mfm

        home = '<a href="/en/orks">o</a><a href="/en/necrons">n</a>'

        def fake_fetch(url, timeout=40):
            if url.endswith("/en"):
                return home
            if "orks" in url:
                return "<html></html>"  # 成功但 0 行
            raise OSError("proxy EOF")  # necrons 永远失败

        monkeypatch.setattr(mfm, "_fetch", fake_fetch)
        monkeypatch.setattr(mfm.time, "sleep", lambda s: None)
        out = tmp_path / "mfm.json"
        data = mfm.fetch_all(out, sleep_s=0, max_retries=2)
        assert data["orks"] == []
        assert data["necrons"] == []  # 失败降级为空行
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["failed"] == ["necrons"]


class TestCheckPointsUnparsed:
    """gnhf 审查模块 4 H1 配套：points_json NULL/损坏的行不许从对账口径无声蒸发。"""

    def test_null_points_json_reported_not_swallowed(self, tmp_path):
        db = tmp_path / "wh40k.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE units(id TEXT,faction_id TEXT,name_en TEXT,name_zh TEXT,"
            "points_json TEXT,keywords_json TEXT,version TEXT)")
        # fp_errata 新插单位重建后 points_json=NULL 的形态
        conn.execute(
            "INSERT INTO units VALUES('1','ORK','Bigboss',NULL,NULL,NULL,NULL)")
        conn.execute(
            "INSERT INTO units VALUES('2','ORK','Warboss',NULL,?,NULL,NULL)",
            (json.dumps({"points": 65, "items": [
                {"line": "1", "desc": "1 model", "cost": 65}]}),))
        conn.commit(); conn.close()
        rep = check_points(db, {"orks": [
            ("BIGBOSS", "YOUR UNIT COSTS", "1 model", 55),
            ("WARBOSS", "YOUR UNIT COSTS", "1 model", 65)]})
        # NULL 行进 db_unparsed 桶（此前裸 continue：不进 compared/diffs/mfm_only）
        assert rep["db_unparsed"] == ["Bigboss"]
        assert "BIGBOSS" not in rep["mfm_only"]
        # 负向成对：健康行不受影响，正常参与对账
        assert rep["compared"] == 1 and rep["agree"] == 1


class TestFetchRegressionGuard:
    """gnhf 审查模块 4 H2 配套：fetch 写盘前与旧缓存对账，系统性掉行拒绝覆盖
    （2026-07-22 官网改版事故的护栏从复盘记忆落进代码）。"""

    def _wire(self, monkeypatch, new_rows):
        import db_compile.mfm as mfm
        home = '<a href="/en/orks">o</a>'
        monkeypatch.setattr(mfm, "_fetch", lambda url, timeout=40: home)
        monkeypatch.setattr(mfm, "fetch_faction",
                            lambda slug, max_retries=3: list(new_rows))
        monkeypatch.setattr(mfm.time, "sleep", lambda s: None)
        return mfm

    def _old_cache(self, tmp_path, n):
        out = tmp_path / "mfm.json"
        rows = [["YOUR UNIT COSTS", f"u{i}", "1 model", 10] for i in range(n)]
        out.write_text(json.dumps({"factions": {"orks": rows}}),
                       encoding="utf-8")
        return out

    def test_systematic_drop_refuses_overwrite(self, tmp_path, monkeypatch):
        # 旧缓存 20 行 → 新抓只剩 2 行（掉 90%）= 解析器断裂形态 → raise 且旧缓存保住
        mfm = self._wire(monkeypatch, [("YOUR UNIT COSTS", "x", "1 model", 10)] * 2)
        out = self._old_cache(tmp_path, 20)
        before = out.read_text(encoding="utf-8")
        with pytest.raises(RuntimeError, match="拒绝覆盖"):
            mfm.fetch_all(out, sleep_s=0, max_retries=1)
        assert out.read_text(encoding="utf-8") == before  # 好缓存未被清

    def test_force_overwrites_after_manual_confirmation(self, tmp_path, monkeypatch):
        mfm = self._wire(monkeypatch, [("YOUR UNIT COSTS", "x", "1 model", 10)] * 2)
        out = self._old_cache(tmp_path, 20)
        mfm.fetch_all(out, sleep_s=0, max_retries=1, force=True)
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert len(saved["factions"]["orks"]) == 2  # 显式 --force 才允许覆盖

    def test_small_fluctuation_passes(self, tmp_path, monkeypatch):
        # 负向成对：小幅波动（20→18，掉 10% 未过阈）正常写盘，不误伤日常刷新
        mfm = self._wire(monkeypatch, [("YOUR UNIT COSTS", "x", "1 model", 10)] * 18)
        out = self._old_cache(tmp_path, 20)
        mfm.fetch_all(out, sleep_s=0, max_retries=1)
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert len(saved["factions"]["orks"]) == 18


class TestApplyPoints:
    def test_updates_stale_costs_and_min_points(self, tmp_path):
        from db_compile.mfm import apply_points

        db = _make_db(tmp_path)
        rep = apply_points(db, TestCheckPoints.MFM_FACTIONS,
                           fetched_at="2026-07-08")
        assert rep["units_updated"] >= 1  # Intercessor 10 models 160→150
        conn = sqlite3.connect(str(db))
        pj = json.loads(conn.execute(
            "SELECT points_json FROM units WHERE name_en='Intercessor Squad'"
        ).fetchone()[0])
        conn.close()
        costs = {it["desc"].lower(): it["cost"] for it in pj["items"]}
        assert costs["10 models"] == 150
        # 顶层 points 修正为基准档最小值（原为各档累加的错误语义）
        assert pj["points"] == 80
        assert pj["mfm"]["fetched_at"] == "2026-07-08"

    def test_stores_tier_surcharges_in_mfm_block(self, tmp_path):
        from db_compile.mfm import apply_points

        db = _make_db(tmp_path)
        apply_points(db, TestCheckPoints.MFM_FACTIONS, fetched_at="2026-07-08")
        conn = sqlite3.connect(str(db))
        pj = json.loads(conn.execute(
            "SELECT points_json FROM units WHERE name_en='Castigator'"
        ).fetchone()[0])
        conn.close()
        tiers = pj["mfm"]["tiers"]
        assert {"tier": "YOUR 3RD + UNIT COSTS", "models": "1 model",
                "cost": 175} in tiers

    def test_unmatched_db_units_untouched(self, tmp_path):
        from db_compile.mfm import apply_points

        db = _make_db(tmp_path)
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO units VALUES('9','SM','Untouched Unit',NULL,?,NULL,NULL)",
            (json.dumps({"points": 55, "items": [
                {"line": "1", "desc": "1 model", "cost": 55}]}),))
        conn.commit(); conn.close()
        apply_points(db, TestCheckPoints.MFM_FACTIONS, fetched_at="2026-07-08")
        conn = sqlite3.connect(str(db))
        pj = json.loads(conn.execute(
            "SELECT points_json FROM units WHERE name_en='Untouched Unit'"
        ).fetchone()[0])
        conn.close()
        assert pj == {"points": 55,
                      "items": [{"line": "1", "desc": "1 model", "cost": 55}]}
