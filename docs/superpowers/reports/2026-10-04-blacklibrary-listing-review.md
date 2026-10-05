# October 4 Black Library listing review

The bounded public review is implemented and validated. The fresh inventory contains **1,166 unique rows**, and exactly four detail requests still return wrong identities. All **94** prior empty-listing decisions have been reviewed individually: **43 duplicate listings, 36 existing empty Legends listings, and 15 other empty listings**. Only the 62 image-changed own rows receive renewed complete sanitized-row hashes. The other 32 row bindings remain unchanged. Six stale duplicate bindings are reclassified as other empty listings, with the old counterpart evidence preserved below and in the ignored evidence. No canonical unit or full card is excluded by these decisions.

The tracked change is limited to `db_compile/blacklibrary_listing_policy.json`, the classification assertion in `tests/test_blacklibrary_scope.py`, and this new report. Runtime policy implementation and schema are unchanged. Initial and pre-commit HEAD: `07430047db0ad192ff65a342d000c539e4d54e5c`, branch `codex/review-answer-provenance`. Automatic GNHF commit and the subsequent clean-checkout confirmation remain the orchestrator’s final step; no manual commit, push, merge or deployment was performed in this iteration.

## Public capture and scope

Capture UTC: **2026-10-04T06:06:39.777147+00:00–2026-10-04T06:06:51.797849+00:00** (October 4, approximately 15:06:39–15:06:51 local +09). `Snapshot.fetch_units()` was called once into a new private output directory, then `Snapshot.fetch_details(selected_four_rows)` once. The request interval was 0.3 seconds; all **28 requests completed on attempt 1**. No transport retry or invented request route was needed. The four identity validation failures are retained as actual `failed` request states with their sanitized successful HTTP/business envelopes, not relabelled as empty bodies.

Public POST endpoints:

- https://blackforum.czmakj.com/app/manager/forum/unit/list — `gameId: 2`, empty `unitName`, `pageNum: 1..24`, `pageSize: 50`.
- https://blackforum.czmakj.com/app/unit/detail — exactly the four `gameId`, `topName`, English `unitName` requests below.

Every list page reports `totalCount=1166`, `pageLength=24`, and its correct `currentPageNo`. Pages 1–23 each contain 50 rows; page 24 contains 16. All rows have game 2, a faction, and unique source IDs. Raw stored envelopes and compiled rows use the existing recursive `sanitize`; every stored request/response hash was rechecked. No account metadata, request headers, tokens or credentials were stored. `Snapshot` disables environment proxy discovery, so its session explicitly used the same required local proxy after the shell proxy variables were set.

No other endpoints, full-card recrawl, army rules, powers, catalogue, AoS or KT capture was performed. Images were neither fetched nor read for rule bodies. Own excluded rows have no English lookup key and no inline body, so no supported own full-detail request is obtainable. This is an inventory review supported by retained and fresh own-row evidence, **not a fresh blank detail-response capture**.

Evidence root: `D:/Project/py/RAG/db_sources/blacklibrary-listing-review-owned/20261004/`. `public-capture/` is the actual partial source snapshot; `copied-partial-snapshot/` is its unchanged copied review snapshot. The whole-inventory hash is a review binding; runtime exclusions still bind the **whole individual sanitized row**.

| Input/output binding | SHA-256 |
| --- | --- |
| September reviewed units (`db_sources/blacklibrary/staged-20260926/units.json`) | `ecdb0dc2e226a94349fcea682cb83ad72130724883fa35e325670c3235e91a45` |
| Retained September raw snapshot manifest (`20260926-resume`) | `69bd7facd5740b3b111b7912223884f918dc48caf53e9f55856c811a99084ce8` |
| Fresh sanitized inventory | `92271c395d8eb4ee8b5d2afb4f44d2fe1ce6bd073c3e31dd6a99b26b00b6cc10` |
| Fresh partial snapshot manifest | `d738429198b3c7ad61134458e5dbbe2d830980210f75b6132fbabec426951020` |
| Fresh compiled selected-four details | `26cb7e17e6720837595273cf7283ac5642f482756dd82e29bbca7939532dc4b1` |
| Previous policy (exact original byte hash) | `4308772b82c623bf084629311526ec3be858913ddc90c5cea8ed550f879b6376` |
| Renewed policy | `37b52cf122278a243951e9229f2a16365ff2e0e450a5b611dddf571f1dc2e864` |

## Inventory reconciliation

| Baseline | Before → fresh | Added | Removed | Same-ID changed | Unchanged |
| --- | --- | ---: | ---: | ---: | ---: |
| September reviewed inventory | 1171 → 1166 | 3 | 8 | 1056 | 107 |
| October 4 frozen inventory | 1166 → 1166 | 0 | 0 | 17 | 1149 |

September same-ID field differences overlap: `detailPic` 1,019; `unitScore` 268; `unitName` 26; `goodIcon` 17; `detailPicType` five. `inventory-reconciliation.json` enumerates every added, removed and changed identity with old/fresh row hashes. Absence or renamed listing text is not a canonical deletion, Legends determination or authority for point publication.

| September ID change | Source ID | Faction | Source Chinese name | English lookup key |
| --- | ---: | --- | --- | --- |
| added | 3030 | 星际战士 | 摩托连长 | CAPTAIN ON BIKE |
| added | 3031 | 极限战士 | 凯厄斯·科诺里乌斯 | KAIUS KONORIUS |
| added | 3033 | 星际战士 | 装备热熔步枪的根除者小队 | ERADICATOR SQUAD WITH MELTA RIFLES |
| removed | 6 | 极限战士 | 马涅乌斯.卡尔加（已删除） | Marneus Calgar |
| removed | 8 | 极限战士 | 西卡留斯连长（已删除） | Captain sicarius |
| removed | 9 | 极限战士 | 文崔斯连长 | Captain Uriel Ventris |
| removed | 68 | 星际战士 | 根除者小队 | ERADICATOR SQUAD |
| removed | 480 | 圣血天使 | 装备爆弹步枪的死亡连小队 | Death Company Marines With Bolt Rifles |
| removed | 1063 | 黑色圣堂 | 黑色圣堂肃卫老兵小队 | Black Templars Sternguard Veteran Squad |
| removed | 1064 | 黑色圣堂 | 黑色圣堂终结者小队 | Black Templars Terminator squad |
| removed | 1065 | 黑色圣堂 | 黑色圣堂十字军型兰德掠袭者坦克 | Black Templars Land raider crusader |

Relative to the frozen October 4 list, the 17 material row differences are:

| Source ID | English lookup key | Changed fields and values |
| ---: | --- | --- |
| 10 | CAPTAIN TITUS | detailPic changed (exact old/new URL in evidence); goodIcon changed (exact old/new URL in evidence) |
| 76 | TACTICAL SQUAD | unitName: "战术小队（即将传奇）" → "战术小队" |
| 78 | DEVASTATOR SQUAD | unitName: "破坏者小队（即将传奇）" → "破坏者小队" |
| 79 | CENTURION ASSAULT SQUAD | unitName: "百夫长突击小队（即将传奇）" → "百夫长突击小队" |
| 80 | CENTURION Devastator SQUAD | unitName: "百夫长破坏小队（即将传奇）" → "百夫长破坏小队" |
| 82 | SUPPRESSOR SQUAD | detailPicType: null → 1; unitName: "压制者小队（即将传奇）" → "压制者小队" |
| 92 | WHIRLWIND | unitName: "旋风火箭炮（即将传奇）" → "旋风火箭炮" |
| 93 | PREDATOR DESTRUCTOR | unitName: "破坏者型猎食者坦克（即将传奇）" → "破坏者型猎食者坦克 " |
| 94 | PREDATOR ANNIHILATOR | unitName: "歼灭者型猎食者坦克（即将传奇）" → "歼灭者型猎食者坦克 " |
| 95 | VINDICATOR | unitName: "维护者突击炮（即将传奇）" → "维护者突击炮" |
| 105 | RAZORBACK | unitName: "豪猪装甲车（即将传奇）" → "豪猪装甲车" |
| 111 | STORMHAWK INTERCEPTOR | unitName: "风暴隼拦截机（即将传奇）" → "风暴隼拦截机" |
| 112 | STORMTALON GUNSHIP | detailPicType: null → 1; unitName: "风暴爪炮艇（即将传奇）" → "风暴爪炮艇" |
| 113 | STORMRAVEN GUNSHIP | unitName: "风暴鸦炮艇（即将传奇）" → "风暴鸦炮艇" |
| 132 | HAMMERFALL BUNKER | unitName: "落锤堡（即将传奇）" → "落锤堡" |
| 821 | Khorne Berzerkers | unitScore: 160 → 170 |
| 1603 | WARDENS OF ULTRAMAR | detailPic changed (exact old/new URL in evidence); goodIcon changed (exact old/new URL in evidence) |

These community list changes remain staged evidence only. In particular, removing the source phrase `（即将传奇）` does not establish canonical status, and source 821’s 160→170 community score was not applied to official points.

## All 94 strict decisions

For every row below, both retained and fresh own rows have no English lookup key and no inline detail. The retained own row reproduces its prior policy SHA exactly. The own fresh row is identical or differs **only in `detailPic`**. The 62 image changes are exactly IDs 2742–2795 inclusive, 2798, 2834, 2835, 2905, 2907, 2909, 2910 and 2919. No field is stripped from the new fingerprint.

`review-94.json` retains every full old/fresh sanitized own row, both row SHAs, decision and classification, plus exact current and retained counterpart status and raw lineage. The table’s SHA is the renewed/retained whole-row binding. “Exact pair” means current list Chinese name, source faction and English key agree with the previously captured counterpart; the retained full response was hash-verified. It does **not** claim a freshly recaptured counterpart body. Existing `empty_legends` classifications are carried forward for unchanged own evidence, not inferred from name absence or applied to canonical status.

| Own ID | Source faction/name | Final reason | Own row review | Counterpart evidence | Whole fresh row SHA-256 |
| ---: | --- | --- | --- | --- | --- |
| 1527 | 浴血者 / 叛军首领 | `empty_listing` | retain identical row | No full counterpart asserted | `28f5f800455ee206f70515b9964d7097d14a1e2144e72df60d48dbae2882e727` |
| 2742 | 星际战士 / 战锤40k 星际战士 vsm 渗透者 入侵者 | `empty_listing` | renew image change | No full counterpart asserted | `5321aeee0dd6776d05379ec57ca3de19f2ca651a65d24f6d249a5c26f27d3f0f` |
| 2743 | 星际战士 / 先驱者小队 | `duplicate_listing` | renew image change | 69 exact pair; retained body | `4bd9d480c0d2e8dd6374c8c3558bfddc36c67db005d9bec632b75ae081667641` |
| 2744 | 星际战士 / 根除者小队 | `empty_listing` | renew image change | 68 absent; counterpart unproven | `1381a205da5acd1d1793b660b1b13d289292a06409018b7b5e51510b5725bca6` |
| 2745 | 星际战士 / 侵略者小队 | `duplicate_listing` | renew image change | 67 exact pair; retained body | `4d8bdb4c0302e7faa4f436d7c689343f6ec4f1a53c238049f3a378e231a40f8f` |
| 2746 | 星际战士 / 重装仲裁者小队 | `duplicate_listing` | renew image change | 66 exact pair; retained body | `de80e527c94ae61e6bfc6a4d47b452879e85fb04583970451046a760a789786e` |
| 2747 | 星际战士 / 寂灭者小队 | `duplicate_listing` | renew image change | 63 exact pair; retained body | `9a0e8b517b685969f3621cbf7924f4b6c15a4830b501daf5ecc9685e037335a1` |
| 2748 | 星际战士 / 地狱轰击者小队 | `duplicate_listing` | renew image change | 60 exact pair; retained body | `bf9ef7636a80b34533682030c97d1faad59d52f9ad66bf0d9522b8df047b91a0` |
| 2749 | 星际战士 / 肃卫老兵小队 | `duplicate_listing` | renew image change | 58 exact pair; retained body | `09e997b01970bb97d5a635e149c696407d05e6bc3a903c18c75b1faa4351c01f` |
| 2750 | 星际战士 / 剑卫老兵小队 | `duplicate_listing` | renew image change | 57 exact pair; retained body | `d68b2da156a6c98ada7cfac113aecbdcba67a89fee841ea00f25ddb39b6ab05b` |
| 2751 | 星际战士 / 跳跃背包突击仲裁者小队 | `duplicate_listing` | renew image change | 54 exact pair; retained body | `65c2af42f35195531a1ac4530726dc937679294059c2e2840cdecb59efb1caf7` |
| 2752 | 星际战士 / 连队英雄 | `duplicate_listing` | renew image change | 52 exact pair; retained body | `42da882618cf68d96650ac6177535c11be2eb7187f62d9d5bce71d64626f0227` |
| 2753 | 星际战士 / 终结者旗手 | `empty_listing` | renew image change | 47 renamed to 终结者装甲旗手; counterpart unproven | `d8956d3d12cab648300236971bd262dc26a3fc595980fe766f2093482f164b93` |
| 2754 | 星际战士 / 旗手 | `duplicate_listing` | renew image change | 46 exact pair; retained body | `17da0fa0962335121364909f892ebee7898689847c1e5aee61a3cbb557d257a0` |
| 2755 | 星际战士 / 药剂师 | `duplicate_listing` | renew image change | 44 exact pair; retained body | `c6bb2f390e36358ddff2c76bd02df34f7ec0e0b1a008640e34f8f42db5456f6e` |
| 2756 | 星际战士 / 技术军士 | `duplicate_listing` | renew image change | 43 exact pair; retained body | `bfe8694618f7946b0c2952fe454bf795f7b1f8df283fb3cf550a3018fcb843f8` |
| 2757 | 星际战士 / 摩托牧师 | `duplicate_listing` | renew image change | 41 exact pair; retained body | `a6fbca763889a0ef42130614fd3bbdcbb2601531feae588c83c71bd227683d2c` |
| 2758 | 星际战士 / 终结者牧师 | `empty_listing` | renew image change | 40 renamed to 终结者装甲牧师; counterpart unproven | `90021b2df201ecc003aa5e565c377a8d943e1cf3414c250953a4cad07a62da08` |
| 2759 | 星际战士 / 牧师 | `duplicate_listing` | renew image change | 39 exact pair; retained body | `376a67be06b4fec46f9b59cf6bad60b0190ff8c47a7c6f268ecb5bc434019eaf` |
| 2760 | 星际战士 / 智库 | `empty_listing` | renew image change | 37 renamed to 智库员; counterpart unproven | `16874e958230f27c07f367bc9ca0d51a2f8a329fc550e84bbb71ec8dbd0c34a8` |
| 2761 | 星际战士 / 劫掠者副官 | `duplicate_listing` | renew image change | 34 exact pair; retained body | `4f16c14d498f762a45e73579af49f1501cb878521778a1b7d48b83e693c9860b` |
| 2762 | 星际战士 / 副官 | `duplicate_listing` | renew image change | 33 exact pair; retained body | `961601930749c73c13b00990d7637d613e542d1c4559315c83a317a232ad59bb` |
| 2763 | 星际战士 / 跳跃背包连长 | `duplicate_listing` | renew image change | 32 exact pair; retained body | `8a0429381e924b488e0e345141f6cf5f650cd31c259df7c87a8ddbdf97b0844a` |
| 2764 | 星际战士 / 先锋军连长 | `empty_listing` | renew image change | 30 renamed to 恐惧型装甲连长; counterpart unproven | `16a0d70a417f421312d2836debb66c6e0c36f4397cf1edfce2a473e150d60fef` |
| 2765 | 星际战士 / 连长 | `duplicate_listing` | renew image change | 28 exact pair; retained body | `faeea725565be0694487180cd0bb5d41a88244bbafaee44b164a607133b7d18f` |
| 2766 | 星际战士 / 重装连长 | `empty_listing` | renew image change | 29 renamed to 重装型装甲连长; counterpart unproven | `45df7ec1ddbb3a82ab0349868660232cc2af36a33a3ab6009dd88d1c5dd6021a` |
| 2767 | 星际战士 / 仲裁者小队 | `duplicate_listing` | renew image change | 53 exact pair; retained body | `f0f3a11a6ceae4fe4c139583e2285fe86d9f82631883e4b0fcdffa4ca1c9ab70` |
| 2768 | 星界军 / 女武神炮艇 | `duplicate_listing` | renew image change | 219 exact pair; retained body | `221d2c71ab703c96be00135b0b25c956cc042b0fa81dccd41a7379dc879e50fe` |
| 2769 | 星界军 / 飞龙自行火炮/九头蛇高射炮 | `empty_listing` | renew image change | No full counterpart asserted | `b6c113a6e82403ac928d9922e4d7188f1a3fd0adad209870696126b070ee716e` |
| 2770 | 星界军 / 克里德堡主 | `duplicate_listing` | renew image change | 217 exact pair; retained body | `5ae35b46d300edffd96278b4e0c026040b46379e4ceed53690e727c95fce80a7` |
| 2771 | 星界军 / 风暴忠嗣军小队 | `duplicate_listing` | renew image change | 216 exact pair; retained body | `f242be9ecd90fbfd216cb9d9ef54062f1dd2b293f43bc2ef867fd890718d0c14` |
| 2772 | 星界军 / 风暴天鹰 | `duplicate_listing` | renew image change | 215 exact pair; retained body | `b43561bb35205f3dfeb6fbbb5b5ad402b904f54a79d2f657f6226c8792b9a1e0` |
| 2773 | 星界军 / 技术技师机械教士 | `duplicate_listing` | renew image change | 214 exact pair; retained body | `5ace912fe2bca57ec164f680d6c7df7ae2d6d8d69917882ac732858e0e96f8b3` |
| 2774 | 星界军 / 罗格多恩坦克 | `duplicate_listing` | renew image change | 205 exact pair; retained body | `2431c4eba66205ea4aaaf0aa1dac752de4dd2e5f737314a73e2b0107f887ba22` |
| 2775 | 星界军 / 莱特林 | `duplicate_listing` | renew image change | 204 exact pair; retained body | `aa77d624f8d7d941741e19445d8a27d20a6a7df4c94699da194f8395d42e0f6a` |
| 2776 | 星界军 / 太阳元帅雷昂图斯 | `duplicate_listing` | renew image change | 187 exact pair; retained body | `af20d55d26d78889aeabaacb75ac5ab2765b8ceb91764cfaf896f895089be4ee` |
| 2777 | 星界军 / 大元帅德雷尔 | `duplicate_listing` | renew image change | 185 exact pair; retained body | `0254d51d0c79e32c723dacd9d20668059d567db29ccffa040af6b1708d3a0b12` |
| 2778 | 星界军 / 克里格重型武器小队 | `duplicate_listing` | renew image change | 174 exact pair; retained body | `a29a261e1482d496cddce5945d1a93b72c6e72cf2d0e69d40e7f68b923458d08` |
| 2779 | 星界军 / 克里格指挥组 | `duplicate_listing` | renew image change | 173 exact pair; retained body | `329ab386b416207ab79c037f8d32495254984f724941ebea3c82241eeea5357f` |
| 2780 | 星界军 / 克里格战斗工兵 | `duplicate_listing` | renew image change | 172 exact pair; retained body | `fb20fcc26c8dd6b89a8a9136ce265367ad148933a3264491aa360a9752194198` |
| 2781 | 星界军 / 卡舍津突击队 | `duplicate_listing` | renew image change | 171 exact pair; retained body | `0ce501af8079186c5ba5cc1386adfbb9a66ef60a0b73075cb4cffc3a8675cdbe` |
| 2782 | 星界军 / 刚特的幽灵 | `duplicate_listing` | renew image change | 167 exact pair; retained body | `46de550cb0c16282a64f1367fd97aefd61cda7402b42db57e587e4c997ea946a` |
| 2783 | 星界军 / 野战炮兵 | `duplicate_listing` | renew image change | 166 exact pair; retained body | `e1d04f43e352758f95beb7d440a71f4e6fc4129fbc937bd9314e8126d1148863` |
| 2784 | 星界军 / 死亡骑兵 | `empty_listing` | renew image change | No full counterpart asserted | `e7e4e7a60bf8e1dd29abc61f26a992173871e2f3440bcb54e1125fd632d1c934` |
| 2785 | 星界军 / 克里格死兵队 | `duplicate_listing` | renew image change | 162 exact pair; retained body | `9f6fa9e91b492794f2d5e4d51d2baefbdc56d6d74c980f9e1f47edfcec738980` |
| 2786 | 星界军 / 政委 | `duplicate_listing` | renew image change | 139 exact pair; retained body | `7e42a5f7906a5e8a09dd9905159cc69137567b2bcdb758e37356209b88b6c695` |
| 2787 | 星界军 / 奇美拉装甲车 | `duplicate_listing` | renew image change | 138 exact pair; retained body | `07d0d6fd13e13edfb524445df19dbd1ef4781ecfc84c2097aeea9cd62bd0fe41` |
| 2788 | 星界军 / 卡迪安突击队 | `duplicate_listing` | renew image change | 134 exact pair; retained body | `da2e1f8ee7f5dbc39f4a8cf9212d31dea7179f6deb8689290ef1b7aed997683c` |
| 2789 | 星界军 / 卡迪安指挥组 | `duplicate_listing` | renew image change | 130 exact pair; retained body | `834ef32e7f6f43896cd66fda3205f449ce99ceec7260ebe4d8ccc4c7eccc341b` |
| 2790 | 星界军 / 卡迪安堡主 | `duplicate_listing` | renew image change | 129 exact pair; retained body | `a394a18329a1d7fe87a0dd893da4ca15048535170d0ddf872bcb01aad112cbcc` |
| 2791 | 星界军 / 牛格林/欧格林 | `empty_listing` | renew image change | No full counterpart asserted | `d195bf15cef16dc5e41a71cead23575b59895d5d19794e7521b629d1a1e0831c` |
| 2792 | 星界军 / 毒刃坦克 | `empty_listing` | renew image change | No full counterpart asserted | `28a171674a0e8db08b9138a37c1d65676aeda6cfa0d41d6f2ecd55fabaf1818d` |
| 2793 | 星界军 / 阿提拉蛮骑兵 | `duplicate_listing` | renew image change | 119 exact pair; retained body | `5d767061d65bc2733204a69901035078767ccf78cb4f0b278bfe22e48c2f6e69` |
| 2794 | 星界军 / 炮兵小组 | `duplicate_listing` | renew image change | 118 exact pair; retained body | `8c0a70b48f09ee8dbe577e6efa5afd77f206fd718974cdcf31d3206b8aa01716` |
| 2795 | 星界军 / 哨兵 | `empty_listing` | renew image change | No full counterpart asserted | `0384c7fd096d67db50c7472ea7fd3ea509f13b85061ee388b2834771ab8fa704` |
| 2798 | 星界军 / 黎曼鲁斯战斗坦克 | `duplicate_listing` | renew image change | 175 exact pair; retained body | `aad3c7250faedec85d3a0066982ddad01f105d0bd6cd94bfe48718358f7c085a` |
| 2834 | 星界军 / 哈米吉多顿：战营：星界军 | `empty_listing` | renew image change | No full counterpart asserted | `e69e5bd94fa5f2b73dff887adaf78c4bf90c176af2ccc13f38661af2dbaff061` |
| 2835 | 星界军 / 杀戮小队：德维兰上的惧物 | `empty_listing` | renew image change | No full counterpart asserted | `c0797e7fef3a1d434e9ba327aca827f0f2afeed38f4dccc2d481b6de163ada1f` |
| 2873 | 黑暗天使 / 鸦翼锐爪副长【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `df0a9370a8f99bf550b647c68b58642c7ad532af3e178cd9b2b2d5b24f4351bd` |
| 2874 | 黑暗天使 / 死翼打击副长【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `c2586c7bb1a0dc7f5d88536b2209f7e70c4a3276df1bd10ec31d645a23aefad1` |
| 2876 | 太空野狼 / 乘坐风暴战车的洛根·格里姆纳尔【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `89a86c2fcec7158142c48057965726e402c1dbe74d1a39d449f2a9826f951776` |
| 2877 | 太空野狼 / 克罗姆·龙瞪【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `0c28bf324f35246940aea2d9aadbed1b43d41f9acee7c19a419672f9f870bc1d` |
| 2878 | 太空野狼 / 哈拉尔德·死亡之狼【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `b92ed30ef1cafd5cbfca3d053591163e573f2d993d9b663977c14f7b4ee8fa72` |
| 2879 | 太空野狼 / 卡尼斯·狼生【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `ae9c5574aa6c6fc06f5f291e2417a7442df01d6cd27586cb5d60ffcc56f947f7` |
| 2880 | 太空野狼 / 终结者护甲野狼守卫战斗领袖【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `85e27178e0b2810f985b8d6af452bf8575c0280d97bd1a9ca2ea07dbc13dd503` |
| 2881 | 太空野狼 / 机械狼【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `bc0d67b613a481557e34490ebc79c80d30a9a34a775d587b5718a92525bceeec` |
| 2884 | 太空野狼 / 莫尔凯猎犬【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `cd4b8cbe58c7b17c0e0af3a089992a62fe5e1278064851d39ad18578e803be92` |
| 2885 | 太空野狼 / 长牙【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `af6225bcfeae4f7a4d450ef0fea83267ed7ce7445bea0b36966fd6f72dd0313b` |
| 2886 | 太空野狼 / 天爪【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `6e09bcfbc5e61eadc7a4df2cb9024941cd6ad12a0460c894949e67f3c3175624` |
| 2887 | 太空野狼 / 骗子卢卡斯【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `7c3de22257c1ee69fbc8efb27c6e59b984a4ee888fd87bff9b6bf0a29d3e11e6` |
| 2890 | 太空野狼 / 野狼守卫头狼【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `ae4a19620ae6b6f90bc7d86822ad71171dfb09f5f5f3f0a96ddff29f11c325e9` |
| 2893 | 太空野狼 / 骑雷狼的野狼领主【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `f79121cd3a289777d74dd882a3f80342f7ad1d5b26fb252ed3f117b077b6b621` |
| 2894 | 太空野狼 / 骑雷狼的野狼守卫战斗领袖【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `8b2261b72a929ea282a302c10d7bd703271c5a7821008d73ce8c3099264501c7` |
| 2895 | 太空野狼 / 风暴牙炮艇【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `dbcbd4c008d6fc2099c6578f5b1957a3521d44cad3f51fc6068adc803deaf001` |
| 2897 | 太空野狼 / 狼卫【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `329cb91a296dbc1120fe976a624e7634b969065e8062d878cc5d69d5c0f3e021` |
| 2898 | 太空野狼 / 跳跃背包野狼守卫头狼【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `c9b9b336b4d0509ed304f7c3607d634cb412a2653114766168f808821610ea50` |
| 2899 | 太空野狼 / 终结者护甲野狼守卫头狼【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `8d1f0047ca9fdcfe28639ebb7f56bc3411cc908205e397217f3124e9c9484a41` |
| 2900 | 太空野狼 / 风暴狼【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `0be56555df09dd3571be15edfe47778278916b7b4af4247f730503f053571b3a` |
| 2904 | 星际战士 / 帝国星际战士【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `de8e40233562698789cf21146b36d1e1fbb0284889f026b1ba5595327cb80ec3` |
| 2905 | 星际战士 / 跳跃背包智库【传奇】 | `empty_legends` | renew image change | No full counterpart asserted | `1e31912084d718462eaa62832747df839dafa90a7ae9c2e3824b15368caf737e` |
| 2906 | 星际战士 / 阿斯塔特奴工【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `59fe4e68accd30f3aff2da3e58b274459ce9633492b5b56e5baf8966413ae8c9` |
| 2907 | 星际战士 / 铁卫无畏机甲【传奇】 | `empty_legends` | renew image change | No full counterpart asserted | `ff597d931bb84ddf84d63629730183c195bee7134387439e29f211860f8045f3` |
| 2909 | 星际战士 / 神圣牧师无畏机甲【传奇】 | `empty_legends` | renew image change | No full counterpart asserted | `4fc7584f7f6e0d7e35df8d21519836000a94b6913d9a9a4996df50f3fc05d3db` |
| 2910 | 星际战士 / 神圣无畏机甲【传奇】 | `empty_legends` | renew image change | No full counterpart asserted | `deafec6f85f3f18df71fd91fa8f3a2824e41ca9664dae91e05e1e78236312fee` |
| 2911 | 星际战士 / 德雷都无畏机甲【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `8bf40520bd358150e28ba7b23f56dccdb20bf3166d2f227e76c7d166c9241387` |
| 2916 | 星际战士 / 圣物蔑视者无畏机甲【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `701c32c0cd808c8f096b1982eb875c69d9b70918f45cf79de8303476e89bd3b5` |
| 2917 | 星际战士 / 利维坦无畏机甲【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `196b41a488f6b7496884cca1a17110ca53380a60f0713f877d53df6fde939d47` |
| 2918 | 星际战士 / 奎托斯【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `b5249c3ab951a57f43e4be795babd2746d9cb286dcc105ef380f727d5361189e` |
| 2919 | 星际战士 / 迪莫斯型猎食者【传奇】 | `empty_legends` | renew image change | No full counterpart asserted | `de57ba7afb94ed75df1bdb8b66fbf25192c90b73d19e6d370f81c0af88acf415` |
| 2925 | 星际战士 / 龙卷风型兰德速攻艇【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `83ce68846ab77e4af61c65dfdf8999a77469ee758b301a5cea19bbed43cde207` |
| 2926 | 星际战士 / 风暴型兰德速攻艇【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `13098e3e3c46db03a8a9cf1b8c9d0d0d2004eef101d614afd3c0fb29ee183c3d` |
| 2927 | 星际战士 / 台风型兰德速攻艇【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `393492b7c3209926ef810302aede09a1b8f30d45c152acb40a9d93733ba68372` |
| 2990 | 星际战士 / 乳齿象【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `4c4245607ba4a60daa0198e77b432a5d08390f71cc8027e0b3bdaf7c328d1958` |
| 2991 | 星际战士 / 西卡然战斗坦克【传奇】 | `empty_legends` | retain identical row | No full counterpart asserted | `8d0aec41c3ecc045163ca40197bed1e3aa3ee627ed62a73a5c012d9633b93fa7` |

The six reclassified own listings are 2744→68 (counterpart absent), 2753→47, 2758→40, 2760→37, 2764→30 and 2766→29 (current exact Chinese counterpart names changed). Their old IDs and verified prior body/raw evidence remain in this report and `review-94.json`. Their current policy `full_detail_source_ids` arrays are empty because a current pairing is unproven. Their unchanged own emptiness, with only an image change, supports `empty_listing`; it supplies no full body, alias or canonical mapping.

## Strict guards and four upstream responses

On the actual fresh list, the previous policy accepts **32** and reopens **62**; the reviewed new policy accepts exactly **94**. All **752** independent mutations (94 rows × eight field changes: ID, faction, name, score, image, English key, body, added field) are refused. Every other **1072** fresh inventory row remains unsuppressed, including full counterpart/new-content rows. Both policies were evaluated on independent copies without mutable A/B contamination. `strict-guards.json` enumerates the refusals. Existing unit tests separately cover same-name full cards, inline-body reopening and forged snapshot exclusions.

| Requested listing → canonical | Exact supported request (`gameId=2`) | Actual returned identity | Body / result | Sanitized raw SHA-256 |
| --- | --- | --- | --- | --- |
| 992 → AoI000003812 | 帝国特勤 / Ministorum Priest | 577 / 修女会 / MINISTORUM PRIEST | nonempty object; wrong source ID/faction; refused | `f30bebfa99a39ca8b174009f399356f64746320592465517535b8dd54511455a` |
| 1001 → AoI000003814 | 帝国特勤 / Watch Captain Artemis | 122 / 死亡守望 / WATCH CAPTAIN ARTEMIS | nonempty object; wrong source ID/faction; refused | `e8051bb3f001f6913f9d880349b3d234586eb35edf84c666b208f2d34f645efb` |
| 1002 → AoI000003815 | 帝国特勤 / Watch Master | 121 / 死亡守望 / WATCH MASTER | nonempty object; wrong source ID/faction; refused | `ea42528ceb7630e3525ab77f97ab9956b3bb01627de82711f2df00feefd4a7ec` |
| 1094 → TS000004124 | 闪耀军团 / LORD OF CHANGE | 238 / 混沌恶魔 / LORD OF CHANGE | nonempty object; wrong source ID/faction; refused | `8b74bcb39bb50bb98b77b88299707d310c7c9ad4cae9bdf042fcc10e08303530` |

All four responses have a successful business envelope and nonempty object body, but fail the required source ID and source faction. Their English identity family alone does not validate them. The exact error is `detail response identity differs from the listed unit`. All four active records remain `retained_previous_cache`; `quarantined_detail` still rejects each. No active quarantine was released and no body was imported. `four-responses.json` binds each exact request/hash, raw response hash, returned identity, previous cache hash and compiled selected-four output.

The captured inventory contains 1,166 IDs while compiled details contain only the selected four. Calling the **actual** `merge_snapshot` refuses this snapshot with `Snapshot detail inventory does not reconcile`. The snapshot status remains `partial`; no full completion flag, filler detail rows or subset importer was created. A later valid response would still require separate bound-proof host review before active promotion. The legitimate retained GK Servitor source 2863 and all five identity bridges remain untouched; no global quarantine or identity assignment was added.

## Raw list lineage

The prior hashes below belong to `db_sources/blacklibrary/snapshots/20260926-resume/raw/unit-list/`; fresh hashes belong to the owned `public-capture/raw/unit-list/`. All old files were verified against their retained manifest and preserved byte-exact. `capture-audit.json` also records each complete sanitized request hash, capture time, state and attempt count.

| Page | Fresh rows | Retained raw SHA-256 | Fresh raw SHA-256 |
| ---: | ---: | --- | --- |
| 1 | 50 | `fa79b2674b2a588a30501f358744fed533b770a052b6493d3490db4b7748f2e1` | `27efc0e202a57b7a3e31468629124da02435fd2686b1088d08905b225906dcc7` |
| 2 | 50 | `0fc220ceb1037a790f2bc04c43078ac897d27400c6141c09d12f72ff2fb0765b` | `d06e6abc28d55681ee315065527c896ce8fa849d3ed906b7612d518198c286a0` |
| 3 | 50 | `5c97d773d325acd93545b6b5ad516f44efb9640a888d45cd5b74ecadc3974850` | `71d9e4865e80843670c769bfbe88777405d2409f6394e7f0a88f4d658c944f77` |
| 4 | 50 | `d3683abfd511d432ef349c4e7de01fb3584590e8a81bcec64bac1efc6110fb91` | `99c20163516402bc518b37abe98120e89d5290877e43c5164c1458f1d4c196c9` |
| 5 | 50 | `ca0981050db0eb3e83b1e76155274f3139baca832b02782cf8d133720b5367d4` | `dd1341a7a2b3304a5d35e3869397fd01fb9eb4e23528bb2456f6d4ffe344c402` |
| 6 | 50 | `6c0b8b4243077d1cfd55127df0f2614ad6b786d2eed0467571e017b97a35dcea` | `72dc22a2020c2018c85a570c318b5b844cac12639ee23c2426203a18671305ea` |
| 7 | 50 | `000eda1945bbefbcfd6e27c9c38841b5b63e8741b97e14f8ba5a95d7cff577b7` | `e7939e197c570a6e7d023e4e34dd1302c8d9ad0bbea283a9aa96c7f92f1bf1fe` |
| 8 | 50 | `6bbad2a2151eedeeada11a965801c73f9280d238f56aa3bca4f953a8c671f635` | `2e69539a0454a5f7f2c8aabb0472046bc4a8609a75def35ee11f66d332bd73c2` |
| 9 | 50 | `aadd1cae680af6e82301203b476e68c88c712fa70525c5ba67db0c8b98fd7975` | `dce752df971e424ab2a9a8cd09de24ecf7c3ca8881713669852f228db85612e6` |
| 10 | 50 | `d448c1219cc81a94e3fb4f00cb95dc5a347fbae4056f4335050979208ff69ed0` | `687a3d6258d35059459b674ce61b936cace5ef515f62f44da9b7e3f48aaa4403` |
| 11 | 50 | `bba86c76eaf854a740f8393c8bf554b4aca76c01c536ec58b111ed7bf375efb1` | `5d0d9418bb4694b5ea0faaef48203c2481677de67efea461ffb35cb0812b28ac` |
| 12 | 50 | `68a712e608fb418d1cf750e8c7b665105efa950174f9a31a66545afe12bd2d8f` | `91db8e6f96f5b293f57bc093bbe4636daa9ac986c612a5a1396ab78499687621` |
| 13 | 50 | `37d43d5d6d00747b6c143ae704faa5a69d0bb0d22ae20f0f74a6342b385f248a` | `c52c8c0fffbf47812ed3c336b4e55a5259a78b48d34ad9d803fa70380f6d1649` |
| 14 | 50 | `cf10fdb1493631db66e70e0e92bd67c691e55b51eba78dda7c1e4a7dbb9929d2` | `850c746d03a69760e11cbfddd16ca7a671a2a5e6fd892d6a06baed2b010acfbd` |
| 15 | 50 | `a28d66c7d49d61a7f190d14ef7b758aada5980294e7d8a313111b25d16ec9dd1` | `eb422cde0f6355864b98aa7592ddd3cf4c3c20d84e35948f9c562b4680cc74cd` |
| 16 | 50 | `93e10430cf332b49e2ddd05a6bcd0b2120db83f7c113679674f8930aa0e1f6a8` | `1dd1bf6c52d48aa3723dbf80bd9859c73bc0ffc8d40e4d2050784e42dd6e2361` |
| 17 | 50 | `4606899727da9fd0910c0212883c8f0fb989985bd9a6e7e9e0662063a15f18e0` | `aea8db8dcc68e6db66295ff35e069716a5ee4b850c73c3aad03d996fac2ab9bb` |
| 18 | 50 | `4efaa279d2dbe945c5a698d1a617249a9abb8df8c78c3d80f2481d282b673566` | `c23d54687dfd6ba79bd4fdd5235bdff40b6fb4ff8e22206bd600f2c275319221` |
| 19 | 50 | `c92465af85bc25f4be5b16db206c913771666988c14a29e85512d14e28ef8e5d` | `c2956cf5fe007141dc0b0a6d736bd145b0660435635baa181f1f98513db5ec11` |
| 20 | 50 | `491765a433d6c62ca81b4362cd48bf0f6ca9b6d42d850cf5b1148f12b948a135` | `6e93376c89221fedec05b2182176001fed670e3107b003993b4915841b3dc436` |
| 21 | 50 | `ebc8d98c60a229eac24e7b1032726d5239acc6188e162804bd672e213444526c` | `393ff0cf07f390c34e25a84e6bb075ac9f628af110336ec43c630ca508350a2a` |
| 22 | 50 | `8ca013311d3bae26b199b952e2c873b9de3d0fd86b69f7723c14b653775d9575` | `8205a00a5599a1b30a9af6511e4f5bf09ce79dc28c3b082290fbb14829c4e238` |
| 23 | 50 | `532fdd609d956cbde6da7cefaa15c24d6f68d547982b4affe7ce459f195e0912` | `d418d0657017c4fefbe879af127545772b884e7fb3472a553b76a046df6e7608` |
| 24 | 16 | `d47f8edc650d9aca5fff55e254187b47327e4bd7a1b19fe47ccb0f8b32c58411` | `792fc47aeaf43ce1d6d85b3356c32ed2b22e3b4123e4ca8356a2460c2f92ce66` |

## Production preservation and validation

Before/after manifests each cover **17,085 files**, with **zero added, zero removed and zero changed protected files**. Coverage includes every retained iteration-09 production-manifest file still present, complete production roots, all local models, active DB/WAL-related files, all index files, active/refined source assets, full Black Library/MFM/Wahapedia cache and old snapshot/raw directories, the root investigation’s inputs, frozen official/source evidence and unrelated JSON policies. The only allowed tracked policy is compared separately. The four top-level source-freshness records and five automatic-update forensic files are explicitly enumerated in `nine-forensic-inputs.json` and all nine are exact.

Active database SHA-256 before/after: `afb9b99da103b61d25b0db82b824c5caf8aaeed1e7237b739ef0bbf15102b855`. The index remains **3,404 documents**, including the existing 1,128 Black Library documents; `index-documents-before.json` records every mapped ID, text and metadata hash. Byte-identical `index.pkl`, `index.faiss`, processed-file metadata and other index files establish preservation of all documents and vectors. No writable database connection, active cache overwrite, ingestion, build/update/wiki generation, package installation or service action was performed.

| Protected evidence | SHA-256 |
| --- | --- |
| Before manifest | `3c809cba706a57a159b3b541dd64bfd2da9833c242e3524b7ce40aa58ef29981` |
| After manifest | `3c809cba706a57a159b3b541dd64bfd2da9833c242e3524b7ce40aa58ef29981` |
| Nine forensic input manifest | `62c22530b9f5a5a8d27dec64198a3f1b43791be10cbc981982fa32a1f32f0d36` |
| All 94 detailed decisions | `69c7c27ec072288df5041fe128fc3bff69edf5eb29acfeae70f5ae238f30a262` |

Validation used only `D:/Project/py/RAG/db_sources/release-check-20260930/python-security-worktree-environments/full-stack-windows-transformers5104/Scripts/python.exe`. All temporary paths, raw evidence, logs and XML are under the owned directory on D:. No new skips, exclusions or dependency installation.

| Actual invocation scope | Passed | Failures | Errors | Skips | XML/log |
| --- | ---: | ---: | ---: | ---: | --- |
| Black Library scope, snapshot, merge, identity, compile and legacy details modules | 91 | 0 | 0 | 0 | `tests.xml`, `tests.log` |
| Corpus source policy module | 11 | 0 | 0 | 0 | `corpus-tests.xml`, `corpus-tests.log` |

Reproduction from the repository root (same stable interpreter above):

```text
-m pytest tests/test_blacklibrary_scope.py tests/test_blacklibrary_snapshot.py tests/test_blacklibrary_snapshot_merge.py tests/test_blacklibrary_identity.py tests/test_db_compile_blacklibrary.py tests/test_fetch_blacklibrary_details.py -q -p no:cacheprovider --basetemp=D:/Project/py/RAG/db_sources/blacklibrary-listing-review-owned/20261004/pytest-tmp --junitxml=D:/Project/py/RAG/db_sources/blacklibrary-listing-review-owned/20261004/tests.xml
-m pytest tests/test_corpus_policy.py -q -p no:cacheprovider --basetemp=D:/Project/py/RAG/db_sources/blacklibrary-listing-review-owned/20261004/pytest-corpus-tmp --junitxml=D:/Project/py/RAG/db_sources/blacklibrary-listing-review-owned/20261004/corpus-tests.xml
```

Both XML files confirm the reported accounting. The changed Python test parses successfully, policy JSON/schema/counts and the actual diff were inspected, and `git diff --check` passes. No build is applicable to a JSON policy/classification-test/report change. No formatter dependency was installed.

The initial preservation helper expanded the `db_sources` root too broadly into unrelated environment/evidence directories. That diagnostic hash pass was interrupted before any baseline output or network call; its log is retained in `before-overbroad-interrupted.log`. The helper was narrowed to enumerated production inputs and explicit source roots, then the successful before/after manifests were saved. Production was never written. A LangChain deprecation warning during the read-only index unpickle is retained in `before.log`; no dependency or provider configuration was changed. There were no pytest failures. The four genuine upstream validation failures remain in their manifest/raw evidence.

## Remaining limits and handoff

This is a dated **community snapshot**, not official current rules, full-site completeness or full-body parity. The four wrong-identity upstream bodies remain unavailable for safe projection. Empty own listings have no valid English detail request; the six stale counterpart bindings are explicitly unproven. Retained September counterpart bodies are evidence lineage, not renewed full-rule verification. Finite supported English fallback remains an honest release limitation.

Implementation and evidence are ready for automatic GNHF commit, followed by clean status/HEAD confirmation. Root owns final push/merge/deploy and separate identity, history-price and stage-only worktrees. No shared orchestrator notes, roadmap, knowledge repository, concurrent worktree or running service was modified. No long-running process started by this iteration remains running. `handoff.md` in ignored evidence records the verified local results and the one remaining automatic commit/clean-checkout step.
