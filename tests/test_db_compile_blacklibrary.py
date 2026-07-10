# tests/test_db_compile_blacklibrary.py
"""blacklibrary：黑图书馆开放 API 翻页抓取的对账与错误载荷判别（mock session，不触网）。

锁死两条纪律：
- 「最后一页」（data 键存在且为空列表）≠「业务错误载荷」（无 data 键）——
  后者必须抛错，不能被误判为抓完了导致静默漏抓整库；
- 结束时与接口宣称的 total 对账，不一致打显眼差额警告。
"""
import pytest

import db_compile.blacklibrary as bl


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeSession:
    """按调用次序回放 payload 列表；越界后回空 data（保险，正常不应触及）。"""

    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = 0
        self.trust_env = True  # fetch_unit_list 会置 False

    def post(self, url, json=None, headers=None, timeout=None):
        payload = (self.pages[self.calls] if self.calls < len(self.pages)
                   else {"data": []})
        self.calls += 1
        return _FakeResp(payload)


def _install(monkeypatch, pages):
    fake = _FakeSession(pages)
    monkeypatch.setattr(bl.requests, "Session", lambda: fake)
    return fake


def _units(start, n):
    return [{"id": i, "unitName": f"单位{i}", "unitEnglishName": f"Unit {i}"}
            for i in range(start, start + n)]


class TestFetchUnitList:
    def test_paginates_until_partial_page_no_warning(self, monkeypatch, capsys):
        _install(monkeypatch, [
            {"data": _units(0, bl.PAGE_SIZE), "total": 80},
            {"data": _units(bl.PAGE_SIZE, 30), "total": 80},
        ])
        units = bl.fetch_unit_list()
        assert len(units) == 80
        assert "对账不符" not in capsys.readouterr().out

    def test_total_mismatch_prints_reconciliation_warning(self, monkeypatch, capsys):
        _install(monkeypatch, [
            {"data": _units(0, bl.PAGE_SIZE), "total": 100},
            {"data": _units(bl.PAGE_SIZE, 10), "total": 100},
        ])
        units = bl.fetch_unit_list()
        assert len(units) == 60
        out = capsys.readouterr().out
        assert "目标 100 vs 实际 60" in out

    def test_error_payload_without_data_key_raises(self, monkeypatch):
        # 业务错误载荷（无 data 键）必须抛错——旧实现当成「最后一页」正常 break，
        # 接口报错时静默返回空/半截列表
        _install(monkeypatch, [{"code": 500, "msg": "系统繁忙"}])
        with pytest.raises(RuntimeError, match="业务错误载荷"):
            bl.fetch_unit_list()

    def test_error_payload_mid_pagination_raises(self, monkeypatch):
        # 第 2 页才报错：同样不能吞——否则前一半数据被当成全量
        _install(monkeypatch, [
            {"data": _units(0, bl.PAGE_SIZE), "total": 80},
            {"code": 500, "msg": "限流"},
        ])
        with pytest.raises(RuntimeError, match="第 2 页"):
            bl.fetch_unit_list()

    def test_empty_data_list_is_normal_last_page(self, monkeypatch):
        # data 键存在且为空列表 → 正常翻页结束，不抛错
        _install(monkeypatch, [{"data": [], "total": 0}])
        assert bl.fetch_unit_list() == []

    def test_dedupes_by_id_across_pages(self, monkeypatch):
        # 翻页间重复 id 去重（接口偶发换页重叠）
        page1 = _units(0, bl.PAGE_SIZE)
        page2 = _units(bl.PAGE_SIZE - 1, 10)  # 首条与上页末条重复
        _install(monkeypatch, [
            {"data": page1, "total": None},
            {"data": page2, "total": None},
        ])
        units = bl.fetch_unit_list()
        assert len(units) == bl.PAGE_SIZE + 9
