# Reviewed empty Black Library listings

The user confirmed that packaging entries and empty source placeholders should be excluded from the crawl backlog. The earlier 98 was a raw failed-detail count, not 98 missing canonical units.

All 94 approved exclusions are tied to a source ID and the SHA-256 of the entire sanitized inventory record. Any changed inventory field, added English lookup key, or inline detail reopens normal processing. Full datasheets with the same Chinese name remain eligible. No canonical unit, English Legends datasheet, cache content or runtime database row was deleted.

- 49 empty listings have an exact-name, same-faction captured full counterpart.
- 36 are empty Legends listings.
- 9 are other empty listings, including bundles; these are not all asserted to be packaging duplicates.
- Four identity mismatches remain actionable: 教廷牧师 (992), 守望连长阿耳忒弥斯 (1001), 守望堡主 (1002), 万变魔君 (1094).

Inceptor example: ignored empty source 2743; preserved full source 69 (INCEPTOR SQUAD). Reviewed count: 94 ignored + 4 actionable = the previous 98. The two separately source-empty responses remain separately reported.

Validation: 40 focused snapshot/policy/merge tests passed. An offline reclassification of the complete captured inventory produced 1,071 full details, two source-empty, 94 ignored and four failed. A staged merge confirms every cached detail payload remains unchanged. Both module use and the standalone downloader --help work. No Docker rebuild is required for this offline crawler change; runtime assets are unchanged. Original snapshots are preserved, and the classified copy is at db_sources/blacklibrary/snapshots/20260926-reviewed-listings/.

The source policy is db_compile/blacklibrary_listing_policy.json. The adjacent JSON contains every excluded ID, reason, hash and matched full counterpart. This is a scoped backlog decision, not a claim of a complete Black Library mirror.
