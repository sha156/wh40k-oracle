"""[P4 spike] 伤害分配核 —— 全篇最高技术风险的一次性验证。

spec: docs/superpowers/specs/2026-07-09-p4-monte-carlo-simulator-design.md
里程碑判据（第十一节）：一次性验证 numpy 伤害分配核
  （不溢出 + 变长 D + 已损伤优先 + 逐点 FNP + 致命伤池），
  手算对拍 3-4 个分配场景（误差 0），确认三维数组内存与性能可接受。

本文件是 spike：用两套**相互独立**的实现互相对拍。
  1. allocate_scalar —— 纯 Python 逐迭代 oracle，规则显式、显然正确（= 手算的一般化）。
  2. allocate_numpy —— 跨 N 向量化核（受测对象，也是 P4-b sequence.py 将直接复用的 kernel）。
两者吃**同一份预掷好的输入数组**（伤害值 + 逐点 FNP 骰面），故对拍只检验"分配逻辑"，
把"采样"这一变量隔离掉。误差要求 = 逐元素**精确相等**（整数，非容差）。

规则语义锁定（现行 dataslate，见 spec 第七节）：
  - 不溢出：单次伤害/单个暴击造伤对目标模型的溢出伤害作废，不流向下一模型。
  - 已损伤优先：同一模型被打伤后，后续伤害继续落在它身上直到其死亡，再换下一模型
    （在逐槽扫描里天然成立——rem 跨槽携带，归零才重置为 W）。
  - 逐点 FNP：每点伤害独立掷 D6，≥X 免伤（"过 FNP"）；对致命伤池同样逐点生效。
  - 致命伤池（DEVASTATING WOUNDS，现行 dataslate）：本单位正常伤害全部结算后成池，
    每个暴击造伤 = 一份 D 伤害，跳保护（已在 wound/save 阶段处理，进池即无保存），
    **每份最多影响 1 个模型、溢出作废**（= 与正常伤害同样的不溢出），FNP 仍逐点生效。
    ⚠ 这是"不溢出"的 dev wounds，不是会跨模型流的传统致命伤（后者是另一种 instance，本期不涉及）。

Python 3.9 兼容：Optional 而非 `int | None`，from __future__ import annotations。
运行：.\.venv\Scripts\python.exe -m engines.simulator._spike_allocation
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

import numpy as np

# FNP 骰面用 6 面骰。damage 上限（D6）→ 逐点 FNP 三维数组的最后一维宽度。
_FNP_FACES = 6


# ---------------------------------------------------------------------------
# 1. 标量 oracle（显然正确的手算一般化）
# ---------------------------------------------------------------------------
def allocate_scalar(
    m_models: int,
    w_wounds: int,
    normal_dmg: np.ndarray,   # (N, A)  每次攻击的已掷伤害值（未过 FNP）
    normal_fnp: np.ndarray,   # (N, A, Dmax)  每次攻击逐点 FNP 骰面 ∈ [1,6]
    mortal_dmg: np.ndarray,   # (N, Am) 每个暴击造伤（dev wounds）的伤害值
    mortal_fnp: np.ndarray,   # (N, Am, Dmax_m)
    fnp_thresh: Optional[int],  # FNP(X)：骰 ≥ X 免伤；None = 无 FNP
) -> dict:
    """逐迭代、逐攻击的纯 Python 参照实现。慢，但规则显式、可读、可信为真值。"""
    n = normal_dmg.shape[0]
    kills = np.zeros(n, dtype=np.int64)
    effective = np.zeros(n, dtype=np.int64)   # 实际移除的伤（不含溢出浪费）
    through_total = np.zeros(n, dtype=np.int64)  # 过 FNP 的总伤（含随后被溢出浪费的）
    wiped = np.zeros(n, dtype=bool)

    def points_through(dmg_val: int, fnp_row: np.ndarray) -> int:
        if fnp_thresh is None:
            return int(dmg_val)
        cnt = 0
        for j in range(int(dmg_val)):
            if fnp_row[j] < fnp_thresh:   # 骰 < X → FNP 失败 → 该点伤害穿透
                cnt += 1
        return cnt

    for i in range(n):
        rem = w_wounds          # 当前模型剩余 W
        alive = m_models        # 尚存活模型数
        k = 0
        eff = 0
        thru = 0

        def apply(dmg_val: int, fnp_row: np.ndarray) -> None:
            nonlocal rem, alive, k, eff, thru
            if alive <= 0:
                return           # 单位已团灭，后续伤害全废
            through = points_through(dmg_val, fnp_row)
            thru += through
            eff += min(through, rem)   # 该模型至多被移除 rem 点，其余溢出作废
            rem -= through
            if rem <= 0:               # 模型死亡 → 计一杀，换下一满血模型
                k += 1
                alive -= 1
                rem = w_wounds
        # 正常伤害先全部结算……
        for a in range(normal_dmg.shape[1]):
            apply(int(normal_dmg[i, a]), normal_fnp[i, a])
        # ……再成池分配致命伤（携带被打伤模型的 rem 状态）
        for a in range(mortal_dmg.shape[1]):
            apply(int(mortal_dmg[i, a]), mortal_fnp[i, a])

        kills[i] = k
        effective[i] = eff
        through_total[i] = thru
        wiped[i] = alive <= 0

    return {"kills": kills, "effective": effective,
            "through": through_total, "wiped": wiped}


# ---------------------------------------------------------------------------
# 2. numpy 向量化核（受测；P4-b sequence.py 直接复用的 kernel）
# ---------------------------------------------------------------------------
def allocate_numpy(
    m_models: int,
    w_wounds: int,
    normal_dmg: np.ndarray,
    normal_fnp: np.ndarray,
    mortal_dmg: np.ndarray,
    mortal_fnp: np.ndarray,
    fnp_thresh: Optional[int],
) -> dict:
    """跨 N 向量化：在攻击槽维度上小循环（≤ 数十次），每槽在 N 维一次算完。

    状态数组（均 (N,)）：rem=当前模型剩余W，alive=存活模型数，kills，effective，through。
    不溢出 + 已损伤优先都落在"rem 跨槽携带、归零重置为 W"这一累积上。
    逐点 FNP 每槽只需 (N, Dmax) 的瞬态数组，峰值工作内存很小。
    """
    n = normal_dmg.shape[0]
    rem = np.full(n, w_wounds, dtype=np.int64)
    alive = np.full(n, m_models, dtype=np.int64)
    kills = np.zeros(n, dtype=np.int64)
    effective = np.zeros(n, dtype=np.int64)
    through_total = np.zeros(n, dtype=np.int64)

    def apply_column(dmg_col: np.ndarray, fnp_col: np.ndarray) -> None:
        nonlocal rem, alive, kills, effective, through_total
        active = alive > 0                      # 团灭后的行不再吃伤
        # 逐点 FNP：每行只看前 dmg_col[row] 个骰面
        if fnp_thresh is None:
            through = dmg_col.astype(np.int64)
        else:
            dmax = fnp_col.shape[1]
            idx = np.arange(dmax)[None, :]                 # (1, Dmax)
            valid = idx < dmg_col[:, None]                 # (N, Dmax) 有效骰位
            fail = (fnp_col < fnp_thresh) & valid          # 穿透点
            through = fail.sum(axis=1).astype(np.int64)    # (N,)
        through = np.where(active, through, 0)
        rem_before = rem
        take = np.where(active, np.minimum(through, rem_before), 0)
        effective += take
        through_total += through
        rem = rem_before - through
        kill_here = active & (rem <= 0)
        kills += kill_here.astype(np.int64)
        alive -= kill_here.astype(np.int64)
        rem = np.where(kill_here, w_wounds, rem)   # 死了就换满血下一模型（团灭行的值下轮被 active 屏蔽）

    for a in range(normal_dmg.shape[1]):
        apply_column(normal_dmg[:, a], normal_fnp[:, a, :])
    for a in range(mortal_dmg.shape[1]):
        apply_column(mortal_dmg[:, a], mortal_fnp[:, a, :])

    return {"kills": kills, "effective": effective,
            "through": through_total, "wiped": alive <= 0}


# ---------------------------------------------------------------------------
# 3. 测试脚手架
# ---------------------------------------------------------------------------
def _fnp_block(rows: List[List[int]], dmax: int) -> np.ndarray:
    """把每次攻击的 FNP 骰面列表补齐成 (1, A, dmax) 的单迭代块（缺位补 6=最易免伤，永不穿透）。"""
    a = len(rows)
    arr = np.full((1, a, dmax), _FNP_FACES, dtype=np.int64)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            arr[0, i, j] = v
    return arr


def _empty(n: int) -> Tuple[np.ndarray, np.ndarray]:
    """空的致命伤池（无 dev wounds 的场景用）。"""
    return (np.zeros((n, 0), dtype=np.int64),
            np.zeros((n, 0, 1), dtype=np.int64))


class _Anchor:
    """一个手算锚点场景：输入固定，期望值由人手算写死在注释里。"""
    def __init__(self, name, m, w, ndmg, nfnp, mdmg, mfnp, fnp,
                 exp_kills, exp_eff, exp_thru, exp_wiped, note):
        self.name = name
        self.m, self.w = m, w
        self.ndmg, self.nfnp = ndmg, nfnp
        self.mdmg, self.mfnp = mdmg, mfnp
        self.fnp = fnp
        self.exp = (exp_kills, exp_eff, exp_thru, exp_wiped)
        self.note = note


def _build_anchors() -> List[_Anchor]:
    """4 个手算锚点，覆盖：不溢出浪费 / 变长 D 单发不溢出 / 逐点 FNP / 致命伤池携带+FNP。"""
    anchors: List[_Anchor] = []

    # ── A：不溢出 + 已损伤优先。3 个 3W 模型，四发 D2，无 FNP。
    #   手算：m1 3-2=1（不死），1-2=-1→杀(浪费1)；m2 3-2=1，1-2=-1→杀(浪费1)；m3 未被碰。
    #   kills=2；effective=2+1+2+1=6；through=8；wiped=False（还剩 m3）。
    ndmg = np.array([[2, 2, 2, 2]], dtype=np.int64)
    nfnp = np.zeros((1, 4, 1), dtype=np.int64)   # 无 FNP，占位
    md, mf = _empty(1)
    anchors.append(_Anchor("A 不溢出+已损伤优先(3×W3, 4发D2, 无FNP)",
                           3, 3, ndmg, nfnp, md, mf, None,
                           2, 6, 8, False,
                           "四发 D2 打三个 3W：连打同一模型至死，每杀浪费 1，剩 1 个模型"))

    # ── B：变长 D 单发不溢出。1 个 1W 模型吃一发 D6=6；再看 1 个 12W 巨兽吃两发 D6=6。
    #   B1: kills=1, effective=1, through=6, wiped=True（浪费5）。
    ndmg = np.array([[6]], dtype=np.int64)
    nfnp = np.zeros((1, 1, 1), dtype=np.int64)
    md, mf = _empty(1)
    anchors.append(_Anchor("B1 变长D单发不溢出(1×W1, D6=6, 无FNP)",
                           1, 1, ndmg, nfnp, md, mf, None,
                           1, 1, 6, True,
                           "D6=6 打 1W：杀 1 浪费 5，单发只影响 1 个模型"))
    #   B2: 12W 巨兽，两发 D6=6：12-6=6，6-6=0→杀。kills=1, effective=12, through=12, wiped=True。
    ndmg = np.array([[6, 6]], dtype=np.int64)
    nfnp = np.zeros((1, 2, 1), dtype=np.int64)
    md, mf = _empty(1)
    anchors.append(_Anchor("B2 多点单模型累加(1×W12, 两发D6=6, 无FNP)",
                           1, 12, ndmg, nfnp, md, mf, None,
                           1, 12, 12, True,
                           "两发 6 累加打满 12W：伤害在同一模型上累积不重置"))

    # ── C：逐点 FNP。1 个 6W 模型，FNP 5+（骰≥5 免伤）。
    #   发1 D=6，骰[5,3,6,2,4,5]→穿透=<5 的个数: 3,2,4 →3；rem 6-3=3（不死）。
    #   发2 D=6，骰[1,1,1,1,1,1]→全穿6；rem 3-6=-3→杀(浪费3)。
    #   kills=1；effective=min(3,6)+min(6,3)=3+3=6；through=3+6=9；wiped=True。
    ndmg = np.array([[6, 6]], dtype=np.int64)
    nfnp = _fnp_block([[5, 3, 6, 2, 4, 5], [1, 1, 1, 1, 1, 1]], dmax=6)
    md, mf = _empty(1)
    anchors.append(_Anchor("C 逐点FNP(1×W6, 两发D6, FNP5+)",
                           1, 6, ndmg, nfnp, md, mf, 5,
                           1, 6, 9, True,
                           "FNP5+ 每点独立掷：发1 六点里 3 点免伤，发2 全穿"))

    # ── D：致命伤池（dev wounds）在正常伤害后成池，携带被打伤模型，逐点 FNP。
    #   2 个 3W 模型，FNP 6+（骰≥6 免伤）。
    #   正常：一发 D=2，骰[1,1]→全穿2；m1 3-2=1（打伤，rem=1）。
    #   致命池：dev1 D=2 骰[1,1]→穿2；落在 m1(rem1)：1-2=-1→杀(浪费1)，reset rem=3；kills=1。
    #            dev2 D=2 骰[6,1]→骰1=6 免伤、骰2=1 穿 →穿1；落在 m2(rem3)：3-1=2（不死）。
    #   kills=1；effective: 正常 min(2,3)=2 + dev1 min(2,1)=1 + dev2 min(1,3)=1 = 4；
    #   through=2+2+1=5；wiped=False（m2 剩 2W）。
    ndmg = np.array([[2]], dtype=np.int64)
    nfnp = _fnp_block([[1, 1]], dmax=2)
    mdmg = np.array([[2, 2]], dtype=np.int64)
    mfnp = _fnp_block([[1, 1], [6, 1]], dmax=2)   # (1, 2, 2)
    anchors.append(_Anchor("D 致命伤池携带+逐点FNP(2×W3, 正常1发+dev2份, FNP6+)",
                           2, 3, ndmg, nfnp, mdmg, mfnp, 6,
                           1, 4, 5, False,
                           "dev 池在正常伤害后结算，接续被打伤的 m1；每份 dev 不溢出，FNP 逐点生效"))
    return anchors


def run_anchors() -> bool:
    """跑 4 个手算锚点：numpy 结果必须与手写死的期望值逐项精确相等。"""
    print("=" * 74)
    print("[1] 手算锚点对拍（numpy vs 人手算期望值，要求逐项精确相等）")
    print("=" * 74)
    ok = True
    for anc in _build_anchors():
        got = allocate_numpy(anc.m, anc.w, anc.ndmg, anc.nfnp,
                             anc.mdmg, anc.mfnp, anc.fnp)
        g = (int(got["kills"][0]), int(got["effective"][0]),
             int(got["through"][0]), bool(got["wiped"][0]))
        passed = g == anc.exp
        ok = ok and passed
        tag = "PASS" if passed else "**FAIL**"
        print(f"  [{tag}] {anc.name}")
        print(f"         期望 kills/eff/through/wiped = {anc.exp}")
        print(f"         实得 kills/eff/through/wiped = {g}")
        if not passed:
            print(f"         >>> 不一致！{anc.note}")
    print()
    return ok


def _gen_case(rng: np.random.Generator, n: int) -> dict:
    """随机生成一个分配场景（跨 N 迭代共享同一 M/W/维度，逐迭代独立掷骰）。"""
    m = int(rng.integers(1, 13))          # 1-12 个模型
    w = int(rng.integers(1, 13))          # 1-12 W（含单模型巨兽）
    a = int(rng.integers(0, 15))          # 0-14 次正常攻击
    am = int(rng.integers(0, 6))          # 0-5 份致命伤
    # 伤害：混合常量与变长 D（1..6），刻意压向易溢出的大 D
    dmax = 6
    ndmg = rng.integers(1, dmax + 1, size=(n, a), dtype=np.int64) if a else np.zeros((n, 0), np.int64)
    mdmg = rng.integers(1, dmax + 1, size=(n, am), dtype=np.int64) if am else np.zeros((n, 0), np.int64)
    nfnp = rng.integers(1, _FNP_FACES + 1, size=(n, a, dmax), dtype=np.int64) if a else np.zeros((n, 0, dmax), np.int64)
    mfnp = rng.integers(1, _FNP_FACES + 1, size=(n, am, dmax), dtype=np.int64) if am else np.zeros((n, 0, dmax), np.int64)
    # FNP 档：None / 4+ / 5+ / 6+ 轮换
    fnp = rng.choice(np.array([0, 4, 5, 6]))
    fnp_thresh = None if fnp == 0 else int(fnp)
    return {"m": m, "w": w, "ndmg": ndmg, "nfnp": nfnp,
            "mdmg": mdmg, "mfnp": mfnp, "fnp": fnp_thresh}


def run_duipai(cases: int = 400, n: int = 200, seed: int = 40000) -> bool:
    """随机对拍：每个场景喂同一份输入给 scalar oracle 与 numpy，逐元素要求精确相等。"""
    print("=" * 74)
    print(f"[2] 随机对拍 scalar-oracle vs numpy（{cases} 场景 × N={n} = "
          f"{cases * n} 次独立迭代，要求 0 误差）")
    print("=" * 74)
    rng = np.random.default_rng(seed)
    total_iters = 0
    mismatches = 0
    first_bad = None
    for c in range(cases):
        cs = _gen_case(rng, n)
        sc = allocate_scalar(cs["m"], cs["w"], cs["ndmg"], cs["nfnp"],
                             cs["mdmg"], cs["mfnp"], cs["fnp"])
        nu = allocate_numpy(cs["m"], cs["w"], cs["ndmg"], cs["nfnp"],
                            cs["mdmg"], cs["mfnp"], cs["fnp"])
        for key in ("kills", "effective", "through", "wiped"):
            bad = int(np.count_nonzero(sc[key] != nu[key]))
            if bad and first_bad is None:
                idx = int(np.argmax(sc[key] != nu[key]))
                first_bad = (c, key, cs["m"], cs["w"], cs["fnp"],
                             int(sc[key][idx]), int(nu[key][idx]))
            mismatches += bad
        total_iters += n
    print(f"  场景数        : {cases}")
    print(f"  总迭代        : {total_iters}")
    print(f"  不一致元素数  : {mismatches}")
    if first_bad:
        print(f"  首个不一致    : 场景#{first_bad[0]} 字段={first_bad[1]} "
              f"M={first_bad[2]} W={first_bad[3]} FNP={first_bad[4]} "
              f"scalar={first_bad[5]} numpy={first_bad[6]}")
    print(f"  结论          : {'PASS（误差 0）' if mismatches == 0 else '**FAIL**'}")
    print()
    return mismatches == 0


def run_benchmark(n: int = 10000) -> bool:
    """性能 + 三维数组内存核查（spec 判据：万次迭代亚秒级，(N,maxA,maxD) 内存可接受）。"""
    print("=" * 74)
    print(f"[3] 性能与内存核查（N={n}，贴近满编重火力最坏情形）")
    print("=" * 74)
    rng = np.random.default_rng(20260709)
    m, w = 10, 3
    a, am, dmax = 40, 10, _FNP_FACES     # 40 攻击槽 + 10 份 dev + D6
    # 预掷输入（含 spec 关注的三维 FNP 数组）
    t0 = time.perf_counter()
    ndmg = rng.integers(1, dmax + 1, size=(n, a), dtype=np.int64)
    mdmg = rng.integers(1, dmax + 1, size=(n, am), dtype=np.int64)
    nfnp = rng.integers(1, _FNP_FACES + 1, size=(n, a, dmax), dtype=np.int8)
    mfnp = rng.integers(1, _FNP_FACES + 1, size=(n, am, dmax), dtype=np.int8)
    t_gen = time.perf_counter() - t0

    t1 = time.perf_counter()
    res = allocate_numpy(m, w, ndmg, nfnp.astype(np.int64),
                         mdmg, mfnp.astype(np.int64), fnp_thresh=5)
    t_alloc = time.perf_counter() - t1

    mb = 1024 * 1024
    fnp3d_mb = (nfnp.nbytes + mfnp.nbytes) / mb
    cells = n * (a + am) * dmax
    print(f"  三维 FNP 数组 : (N,{a + am},{dmax}) = {cells:,} cell，"
          f"int8 实占 {fnp3d_mb:.2f} MB")
    print(f"  掷骰生成耗时  : {t_gen * 1000:.1f} ms")
    print(f"  分配核耗时    : {t_alloc * 1000:.1f} ms  （{a + am} 个攻击槽 × N={n} 向量化）")
    print(f"  抽检输出      : E[kills]={res['kills'].mean():.3f}  "
          f"E[eff]={res['effective'].mean():.3f}  "
          f"团灭率={res['wiped'].mean() * 100:.1f}%")
    sub_second = t_alloc < 1.0
    mem_ok = fnp3d_mb < 64
    print(f"  结论          : 亚秒={'是' if sub_second else '否'}，"
          f"内存可接受={'是' if mem_ok else '否'}")
    print()
    return sub_second and mem_ok


def main() -> int:
    print("\nP4 分配核 spike —— 不溢出 / 变长D / 已损伤优先 / 逐点FNP / 致命伤池\n")
    a_ok = run_anchors()
    d_ok = run_duipai()
    b_ok = run_benchmark()
    print("=" * 74)
    verdict = a_ok and d_ok and b_ok
    print(f"总判定：{'✅ 全绿——分配核已去风险，可进入 P4-b' if verdict else '❌ 存在失败项，见上'}")
    print("=" * 74)
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
