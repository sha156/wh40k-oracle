# tests/test_db_compile_mfm.py
"""mfm：官方 Munitorum Field Manual 页面解析 + 与库内点数比对（离线 fixture）。"""
import json
import sqlite3

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
