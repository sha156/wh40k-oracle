# tests/test_db_compile_entity_resolver.py
"""entity_resolver：中文名/英文名/社区俗名 → canonical id（离线 fixture + 一个真实数据回归）。"""
import json
from pathlib import Path

from db_compile.entity_resolver import EntityResolver, load_unit_aliases

TERMS_JSON = json.dumps({
    "source": "test",
    "pairs": [
        {"zh": "影阳指挥官", "en": "Commander Shadowsun",
         "canonical_id": "000000407", "faction_id": "TAU",
         "book": "test", "pages": [1], "confidence": "exact"},
        {"zh": "远见指挥官", "en": "Commander Farsight",
         "canonical_id": "000000406", "faction_id": "TAU",
         "book": "test", "pages": [1], "confidence": "exact"},
    ],
})

FAKE_APP_PY = (
    "UNIT_ALIASES = {\n"
    '    "冷言": "影阳指挥官",\n'
    '    "查无此人": "不存在的规则书译名",\n'
    "}\n"
)


def _write_fixtures(tmp_path):
    terms_path = tmp_path / "terms.json"
    terms_path.write_text(TERMS_JSON, encoding="utf-8")
    app_path = tmp_path / "app.py"
    app_path.write_text(FAKE_APP_PY, encoding="utf-8")
    return terms_path, app_path


class TestLoadUnitAliases:
    def test_extracts_dict_without_executing_module(self, tmp_path):
        _, app_path = _write_fixtures(tmp_path)
        aliases = load_unit_aliases(app_path)
        assert aliases["冷言"] == "影阳指挥官"

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_unit_aliases(tmp_path / "no_such_app.py") == {}


class TestEntityResolverFixture:
    def test_resolves_exact_zh_name(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("影阳指挥官")

        assert result.canonical_id == "000000407"
        assert result.name_en == "Commander Shadowsun"
        assert result.confidence == "exact"

    def test_resolves_exact_en_name_case_insensitive(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("commander shadowsun")

        assert result.canonical_id == "000000407"

    def test_resolves_community_alias_through_canonical_zh_name(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("冷言")

        assert result.canonical_id == "000000407"
        assert result.name_en == "Commander Shadowsun"

    def test_alias_pointing_to_unpaired_name_stays_unresolved(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("查无此人")

        assert result.canonical_id is None

    def test_fuzzy_match_typo(self, tmp_path):
        # 单独用只有一个词条的术语表，避免 "Commander Shadowsun"/"Commander Farsight"
        # 共享前缀导致模糊匹配出现真实的歧义候选（ambiguous 本身在别的用例里验证）。
        terms_path = tmp_path / "terms_single.json"
        terms_path.write_text(json.dumps({
            "source": "test",
            "pairs": [{"zh": "影阳指挥官", "en": "Commander Shadowsun",
                       "canonical_id": "000000407", "faction_id": "TAU",
                       "book": "test", "pages": [1], "confidence": "exact"}],
        }), encoding="utf-8")
        resolver = EntityResolver(terms_path=terms_path)

        result = resolver.resolve("Commander Shadowsu")  # 少一个字母

        assert result.canonical_id == "000000407"
        assert result.confidence == "fuzzy"

    def test_fuzzy_match_ambiguous_returns_candidates(self, tmp_path):
        """契约：模糊命中真有多个势均力敌的候选时报 ambiguous，绝不静默挑一个。

        ⚠️ fixture 2026-07-27 换过：原来用 "Commander Shadowsu" 配
        Shadowsun/Farsight 两个词条——但那不是**真的**两可（离 Shadowsun 差 1 个字母、
        离 Farsight 差 8 个），只是 difflib 的比例阈值把八竿子打不着的那个也放了进来。
        加了绝对编辑距离判据后它会（正确地）纠错成 Shadowsun，故换成两个与查询串
        等距的名字来考同一条契约。
        """
        terms_path = tmp_path / "terms_twins.json"
        terms_path.write_text(json.dumps({"source": "test", "pairs": [
            {"zh": "影阳指挥官甲", "en": "Commander Shadowsun", "canonical_id": "000000407",
             "faction_id": "TAU", "book": "test", "pages": [1], "confidence": "exact"},
            {"zh": "影阳指挥官乙", "en": "Commander Shadowsul", "canonical_id": "000000408",
             "faction_id": "TAU", "book": "test", "pages": [1], "confidence": "exact"},
        ]}), encoding="utf-8")
        resolver = EntityResolver(terms_path=terms_path)

        result = resolver.resolve("Commander Shadowsuk")  # 与两个英文名各差 1 个字母

        assert result.canonical_id is None
        assert result.confidence == "ambiguous"
        assert len(result.candidates) >= 2

    def test_unknown_name_returns_none_confidence(self, tmp_path):
        terms_path, app_path = _write_fixtures(tmp_path)
        resolver = EntityResolver(terms_path=terms_path, app_path=app_path)

        result = resolver.resolve("完全不存在的单位名字XYZ")

        assert result.canonical_id is None
        assert result.confidence == "none"


class TestSeparatorNormalizedZhNames:
    """音译名分隔号写法差异算**同名**，必须判 exact（2026-07-27，基准 #113）。

    病灶：库内 `_zh_to_id` 自己就不统一（30 个键用「·」、6 个用「.」，含
    `罗伯特.基里曼`），而题面/用户写的是通行的「·」。于是精确表查空、落到 fuzzy，
    而 `datasheet.find_datasheet` 出于防错配**只信 exact** ⇒ 数值权威路径整条查不到
    ⇒ Agent 判空降级经典链 ⇒ 从民间译本 PDF 答出过期的 320 分（官方是 355）。
    """

    @staticmethod
    def _resolver(tmp_path, pairs):
        terms_path = tmp_path / "terms_sep.json"
        terms_path.write_text(json.dumps({"source": "test", "pairs": [
            {"zh": zh, "en": en, "canonical_id": cid, "faction_id": "X",
             "book": "test", "pages": [1], "confidence": "exact"}
            for zh, en, cid in pairs]}), encoding="utf-8")
        return EntityResolver(terms_path=terms_path)

    def test_interpunct_variant_of_indexed_name_resolves_exact(self, tmp_path):
        # 库里存的是半角句点写法，用户敲中文间隔号
        resolver = self._resolver(
            tmp_path, [("罗伯特.基里曼", "Roboute Guilliman", "000000138")])

        result = resolver.resolve("罗伯特·基里曼")

        # 判 exact 是关键：fuzzy 会被 find_datasheet 拒绝，等价于没修
        assert result.canonical_id == "000000138"
        assert result.confidence == "exact"

    def test_normalization_is_symmetric(self, tmp_path):
        # 反方向（库里存「·」、用户敲「.」）同样要命中
        resolver = self._resolver(
            tmp_path, [("卡尔多·德拉可", "Kaldor Draigo", "000000200")])

        assert resolver.resolve("卡尔多.德拉可").confidence == "exact"
        assert resolver.resolve("卡尔多德拉可").canonical_id == "000000200"

    def test_colliding_normalized_key_refuses_to_guess(self, tmp_path):
        """两个不同实体归一后同名 ⇒ 真歧义，宁可不解析也不静默取先入者。"""
        resolver = self._resolver(tmp_path, [
            ("甲·乙", "Alpha Beta", "000000001"),
            ("甲.乙", "Gamma Delta", "000000002"),
        ])

        # 各自的精确写法仍旧各查各的，一个都不许被归一索引顶掉
        assert resolver.resolve("甲·乙").canonical_id == "000000001"
        assert resolver.resolve("甲.乙").canonical_id == "000000002"
        # 而归一键本身是冲突的：第三种写法不许被猜成其中任意一个
        assert resolver.resolve("甲乙").canonical_id is None

    def test_unrelated_name_still_unresolved(self, tmp_path):
        """归一化只抹分隔号，不得顺手放宽「另一个名字」的判定。"""
        resolver = self._resolver(
            tmp_path, [("罗伯特.基里曼", "Roboute Guilliman", "000000138")])

        assert resolver.resolve("罗伯特·古里曼XYZ").canonical_id is None


class TestFuzzySilentMismatchGate:
    """模糊匹配静默命中不相干单位（2026-07-27）：`Flamestorm Drake`（不存在的名字）
    以 ratio 0.606 命中 `Firestorm Redoubt`，报 fuzzy + canonical_id，上层于是
    found=True 地端回另一张真实兵牌——每一层都是成功路径，界面上毫无破绽。

    判据是**绝对字符编辑距离 ≤2，外加「查询串是命中名的子串」单向豁免**（简称）；
    不是把 FUZZY_CUTOFF 调高——实测两类命中的 ratio 区间重叠，且调高 cutoff 会把
    「多命中 ambiguous（不给 id）」滤成「单命中 fuzzy（给 id）」，反而更糟。
    """

    @staticmethod
    def _resolver(tmp_path, pairs):
        terms_path = tmp_path / "terms_gate.json"
        terms_path.write_text(json.dumps({"source": "test", "pairs": [
            {"zh": zh, "en": en, "canonical_id": cid, "faction_id": "X",
             "book": "test", "pages": [1], "confidence": "exact"}
            for zh, en, cid in pairs]}), encoding="utf-8")
        return EntityResolver(terms_path=terms_path)

    def test_far_hit_is_reported_as_miss_not_as_another_unit(self, tmp_path):
        """病灶本体：旧实现这里返回 fuzzy + 000000918（Firestorm Redoubt）。"""
        r = self._resolver(tmp_path, [("烈焰风暴堡垒", "Firestorm Redoubt", "000000918")])

        result = r.resolve("Flamestorm Drake")

        assert result.canonical_id is None
        assert result.confidence == "none"
        # 近似名只能作为猜测回报，且**不得**混进 candidates（那是可原样回填重查的候选）
        assert result.suggestions == ["FIRESTORM REDOUBT"]
        assert result.candidates == []

    def test_one_char_typo_still_corrects(self, tmp_path):
        """不许一刀切：拼错一个字母就查不到是另一种糟糕体验。"""
        r = self._resolver(tmp_path, [("烈焰风暴堡垒", "Firestorm Redoubt", "000000918")])

        result = r.resolve("Firestorm Redout")   # 少一个 b

        assert result.canonical_id == "000000918"
        assert result.confidence == "fuzzy"

    def test_abbreviation_survives_the_edit_distance_gate(self, tmp_path):
        """基准 #63 的形状：「坦克指挥官」是「黎曼鲁斯坦克指挥官」的子串、距离却有 4。
        只按编辑距离切会把正主滤掉、只剩距离 2 的「远见指挥官」，翻成 fuzzy 报错单位。"""
        r = self._resolver(tmp_path, [
            ("黎曼鲁斯坦克指挥官", "Leman Russ Tank Commander", "000000001"),
            ("远见指挥官", "Commander Farsight", "000000406")])

        result = r.resolve("坦克指挥官")

        assert result.canonical_id is None
        assert result.confidence == "ambiguous"
        assert "黎曼鲁斯坦克指挥官" in result.candidates

    def test_extra_words_do_not_count_as_abbreviation(self, tmp_path):
        """反向包含（真名 + 自造修饰词）必须挡住：双向豁免会让造名命中数 3 → 45。"""
        r = self._resolver(tmp_path, [("幽冥骑士", "Wraithknight", "000000002")])

        result = r.resolve("Decimus Wraithknight")

        assert result.canonical_id is None
        assert result.confidence == "none"
        assert result.suggestions == ["WRAITHKNIGHT"]

    def test_nothing_similar_at_all_reports_plain_miss(self, tmp_path):
        """连近似名都没有时不许伪造 suggestions（下游据它区分两种空手）。"""
        r = self._resolver(tmp_path, [("幽冥骑士", "Wraithknight", "000000002")])

        result = r.resolve("完全不着边际的名字ZZZQQQ")

        assert result.confidence == "none"
        assert result.suggestions == []


class TestRealDbCommunityAliasRegression:
    """真实库回归（v3 基准四缺陷，2026-07-11）：这四个俗名必须解析到唯一本尊。
    其中混沌教徒/机械教游侠是撞名单位（库内同 name_en 多行），经 canonical id 直取；
    若重建后丢失（community 层未重灌）本组即红。"""
    import pytest as _pytest
    from pathlib import Path as _Path
    pytestmark = _pytest.mark.skipif(
        not _Path("db/wh40k.sqlite").exists(), reason="需要 db/wh40k.sqlite")

    EXPECT = {
        "混沌教徒": ("000000946", "Cultist Mob"),                # #23，CSM 本尊（三行撞名）
        "复仇者小队": ("000000593", "Dire Avengers"),            # #48，库内名「狂暴复仇者」
        "机械教游侠": ("000000848", "Skitarii Rangers"),         # #65，AdM 本尊（两行撞名）
        "死亡连无畏机兵": ("000000166", "Death Company Dreadnought"),  # #76，「机兵」口语形
    }

    def test_v3_bench_names_resolve_exact(self):
        resolver = EntityResolver(db_path=Path("db/wh40k.sqlite"))
        for name, (cid, en) in self.EXPECT.items():
            r = resolver.resolve(name)
            assert r.canonical_id == cid, f"{name} → {r.canonical_id}（期望 {cid}）"
            assert r.name_en == en
            assert r.confidence == "exact"


class TestCrossFactionSameNameCollision:
    """评审 #25（基准地狱兽答错阵营）：同一 name_en 存在于多个阵营时，
    英文名精确命中必须报 ambiguous + 阵营限定候选，绝不静默取先入库的那行。"""

    @staticmethod
    def _resolver_with_db(tmp_path):
        import sqlite3
        db = tmp_path / "mini.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE datasheets (id TEXT, name TEXT, faction_id TEXT)")
        conn.executemany(
            "INSERT INTO datasheets VALUES (?,?,?)",
            [("000000954", "Helbrute", "CSM"),
             ("000002632", "Helbrute", "WE"),
             ("000000407", "Commander Shadowsun", "TAU")])
        conn.execute("CREATE TABLE aliases (alias TEXT, canonical_id TEXT, "
                     "lang TEXT, source TEXT)")
        conn.execute("INSERT INTO aliases VALUES ('地狱兽','000002632','zh','test')")
        conn.commit()
        conn.close()
        return EntityResolver(db_path=db)

    def test_exact_en_collision_returns_ambiguous_with_factions(self, tmp_path):
        r = self._resolver_with_db(tmp_path).resolve("Helbrute")
        assert r.canonical_id is None
        assert r.confidence == "ambiguous"
        assert set(r.candidates) == {"Helbrute (CSM)", "Helbrute (WE)"}

    def test_faction_qualified_candidate_round_trips(self, tmp_path):
        resolver = self._resolver_with_db(tmp_path)
        assert resolver.resolve("Helbrute (WE)").canonical_id == "000002632"
        assert resolver.resolve("Helbrute（CSM）").canonical_id == "000000954"
        assert resolver.resolve("helbrute (we)").confidence == "exact"

    def test_zh_alias_bypasses_collision(self, tmp_path):
        # 中文别名指向确定阵营，不受英文名碰撞影响
        r = self._resolver_with_db(tmp_path).resolve("地狱兽")
        assert r.canonical_id == "000002632"
        assert r.confidence == "exact"

    def test_unique_name_unaffected(self, tmp_path):
        r = self._resolver_with_db(tmp_path).resolve("Commander Shadowsun")
        assert r.canonical_id == "000000407"
        assert r.confidence == "exact"

    def test_fuzzy_hit_on_collision_key_also_ambiguous(self, tmp_path):
        r = self._resolver_with_db(tmp_path).resolve("Helbrutee")  # 拼写多一个字母
        assert r.confidence == "ambiguous"
        assert any("(WE)" in c for c in r.candidates)


class TestEntityResolverRealData:
    """用真实 wiki/terms.json + app.py 验证：中文单位名能解析到 canonical id
    （gnhf 停止条件③的直接验证）。"""

    def test_resolves_real_tau_unit_from_wiki_terms(self):
        repo_root = Path(__file__).parent.parent
        resolver = EntityResolver(
            terms_path=repo_root / "wiki" / "terms.json",
            app_path=repo_root / "app.py",
        )

        result = resolver.resolve("影阳指挥官")

        assert result.canonical_id == "000000407"
        assert result.name_en == "Commander Shadowsun"
        assert result.confidence == "exact"

    def test_resolves_second_real_tau_unit_from_wiki_terms(self):
        repo_root = Path(__file__).parent.parent
        resolver = EntityResolver(
            terms_path=repo_root / "wiki" / "terms.json",
            app_path=repo_root / "app.py",
        )

        result = resolver.resolve("远见指挥官")

        assert result.canonical_id == "000000406"
        assert result.name_en == "Commander Farsight"

    def test_current_unit_aliases_do_not_yet_overlap_pilot_terms(self):
        """诚实回归护栏：app.py 的 UNIT_ALIASES 是 P0 之前为其他阵营写的社区俗名，
        当前 wiki/terms.json 只配对了钛帝国/吞世者两个试点阵营（P1），二者暂无交集。
        一旦未来 wiki_compile 覆盖到这些阵营，此测试会失败，提示需要更新用例
        （而不是让 resolver 悄悄返回 None 却没人注意到）。"""
        repo_root = Path(__file__).parent.parent
        aliases = load_unit_aliases(repo_root / "app.py")
        resolver = EntityResolver(
            terms_path=repo_root / "wiki" / "terms.json",
            app_path=repo_root / "app.py",
        )

        resolved_any = any(
            resolver.resolve(nickname).canonical_id is not None
            for nickname in aliases
        )

        assert resolved_any is False
