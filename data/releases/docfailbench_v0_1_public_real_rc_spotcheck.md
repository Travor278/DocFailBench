# Public-Real RC Spot-Check

- Release: `DocFailBench-v0.1-public-real-rc`
- Review date: 2026-05-08
- Sampled assertions: 57
- Decisions: approved=54, approved_with_edit=2, removed=1

## Policy

- Main score keeps visible content and structure assertions.
- Page-furniture `text_absence` checks are published as secondary hygiene and excluded from the main leaderboard.
- Ambiguous or visually wrong reading-order anchors are edited or removed before freeze.

## Records

| Case | Assertion | Type | Decision | Profile | Note |
| --- | --- | --- | --- | --- | --- |
| `public_real_nist_sp800_53r5_p027` | `table_shape_4a52f945214a` | `table_shape` | approved | main | Visual page review confirms a regular 32-row by 4-column revision table. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_7f5aeace671f` | `table_grid_cell` | approved | main | Header cell DATE is visible in row 0, column 0. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_a0c29a88a352` | `table_grid_cell` | approved | main | Header cell TYPE is visible in row 0, column 1. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_23c1839386a1` | `table_grid_cell` | approved | main | Header cell REVISION is visible in row 0, column 2. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_d6299f23d151` | `table_grid_cell` | approved | main | Header cell PAGE is visible in row 0, column 3. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_b852eba9523d` | `table_grid_cell` | approved | main | First data-row date 12-10-2020 is visually present. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_4446cb697879` | `table_grid_cell` | approved | main | First data-row type Editorial is visually present. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_c24191dc3f8a` | `table_grid_cell` | approved | main | First data-row page value 427 is visually present. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_386963b063d6` | `table_grid_cell` | approved | main | Row 11 revision text for Table C-5 duplicate deletion is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_2e8557cd970c` | `table_grid_cell` | approved | main | Row 11 page value 438 is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_6750102d1311` | `table_grid_cell` | approved | main | Near-tail revision entry Table C-19 is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_82be1ff5d528` | `table_grid_cell` | approved | main | Near-tail page value 463 is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_44fb09c941d3` | `table_grid_cell` | approved | main | Tail revision entry SI-19(7) is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_grid_cell_0b607d521dd8` | `table_grid_cell` | approved | main | Tail page value 464 is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_cell_exists_d7d3816de474` | `table_cell_exists` | approved | main | Revision cell beginning Appendix B Acronyms: Add is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_cell_exists_4ed8d55f644b` | `table_cell_exists` | approved | main | UPS Uninterruptible Power Supply is visible within the first revision row. |
| `public_real_nist_sp800_53r5_p027` | `table_cell_exists_8c917d4fa3d9` | `table_cell_exists` | approved | main | Table C-5 duplicate-row deletion text is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_cell_exists_ac5fdbb233cd` | `table_cell_exists` | approved | main | Table C-18 (SC-19) row is visible. |
| `public_real_nist_sp800_53r5_p027` | `table_cell_exists_e3118535aa36` | `table_cell_exists` | approved | main | Table C-19 (SI-19(7)) row is visible. |
| `public_real_nist_sp800_53r5_p027` | `reading_order_7fb05dfe98ce` | `reading_order` | approved | main | Appendix B Acronyms appears above the Table C-19 rows. |
| `public_real_nist_ai_rmf_p017` | `caption_binding_08b0fd565d5b` | `caption_binding` | approved | main | Trustworthiness diagram and Figure 4 caption are adjacent. |
| `public_real_nist_ai_rmf_p017` | `reading_order_0728a2413a0c` | `reading_order` | approved | main | Section heading precedes the figure caption. |
| `public_real_nist_ai_rmf_p017` | `reading_order_59722044cf62` | `reading_order` | approved | main | Figure caption precedes the Trustworthiness characteristics paragraph. |
| `public_real_nist_ai_rmf_p017` | `reading_order_958b96e778e9` | `reading_order` | approved | main | The characteristic list places valid and reliable before privacy-enhanced. |
| `public_real_irs_1040_2024_p001` | `table_cell_exists_847a240ce65d` | `table_cell_exists` | approved | main | Presidential Election Campaign box is visible in the upper-right form block. |
| `public_real_irs_1040_2024_p001` | `table_cell_exists_a3cd4eefe792` | `table_cell_exists` | approved | main | Filing Status label is visible on the left side of the form. |
| `public_real_irs_1040_2024_p001` | `table_cell_exists_dffadf7dc9f2` | `table_cell_exists` | approved | main | Digital Assets section label is visible below Filing Status. |
| `public_real_irs_1040_2024_p001` | `table_cell_exists_6b597cd48f00` | `table_cell_exists` | approved | main | Standard Deduction label is visible below Digital Assets. |
| `public_real_irs_1040_2024_p001` | `table_cell_exists_f83738d8b990` | `table_cell_exists` | approved | main | W-2 total amount row is visible in the Income section. |
| `public_real_irs_1040_2024_p001` | `reading_order_8e674fe7f026` | `` | approved_with_edit | removed | Original Dependents-to-Income anchor was ambiguous because Income appears in side text; edited to Dependents before W-2 row. |
| `public_real_irs_1040sa_2024_p001` | `table_cell_exists_62392c31d800` | `table_cell_exists` | approved | main | Medical and dental expenses row is visible. |
| `public_real_irs_1040sa_2024_p001` | `table_cell_exists_3c08328e4754` | `table_cell_exists` | approved | main | State and local income taxes row is visible. |
| `public_real_irs_1040sa_2024_p001` | `table_cell_exists_77833f29bc31` | `table_cell_exists` | approved | main | Home mortgage interest and points row is visible. |
| `public_real_irs_1040sa_2024_p001` | `table_cell_exists_994d77595721` | `table_cell_exists` | approved | main | Gifts by cash or check row is visible. |
| `public_real_irs_1040sa_2024_p001` | `reading_order_c83ac0b9231c` | `reading_order` | approved | main | Interest You Paid section precedes Gifts to Charity. |
| `public_real_irs_1040sc_2024_p001` | `table_cell_exists_794d85e431f3` | `table_cell_exists` | approved | main | Schedule C title Profit or Loss From Business is visible. |
| `public_real_irs_1040sc_2024_p001` | `table_cell_exists_6232f0848451` | `table_cell_exists` | approved | main | Gross receipts or sales row is visible. |
| `public_real_irs_1040sc_2024_p001` | `table_cell_exists_b86903e37050` | `table_cell_exists` | approved | main | Taxes and licenses expense row is visible. |
| `public_real_irs_1040sc_2024_p001` | `table_cell_exists_714320a018ce` | `table_cell_exists` | approved | main | Net profit or loss row is visible. |
| `public_real_irs_1040sc_2024_p001` | `reading_order_bb0e3ab4fb61` | `reading_order` | approved | main | Other expenses from line 48 precedes Total expenses. |
| `public_real_irs_1040sc_2024_p002` | `table_cell_exists_1f9e0c1c5837` | `table_cell_exists` | approved | main | Cost of Goods Sold section is visible. |
| `public_real_irs_1040sc_2024_p002` | `table_cell_exists_f3b3edfbaea9` | `table_cell_exists` | approved | main | Information on Your Vehicle section is visible. |
| `public_real_irs_1040sc_2024_p002` | `table_cell_exists_c28b9b28769c` | `table_cell_exists` | approved | main | Other Expenses section is visible. |
| `public_real_irs_1040sc_2024_p002` | `reading_order_dc6ac7201f91` | `reading_order` | approved | main | Vehicle service-date question precedes evidence-support question. |
| `public_real_irs_1040sd_2024_p001` | `table_cell_exists_0ff9020cdcbe` | `table_cell_exists` | approved | main | Short-Term Capital Gains and Losses header is visible. |
| `public_real_irs_1040sd_2024_p001` | `table_cell_exists_94f89be175ee` | `table_cell_exists` | approved | main | Gain or (loss) column header is visible. |
| `public_real_irs_1040sd_2024_p001` | `table_cell_exists_9416183769cd` | `table_cell_exists` | approved | main | Net short-term capital gain or loss row is visible. |
| `public_real_irs_1040sd_2024_p001` | `reading_order_473cbab141be` | `reading_order` | approved | main | Short-term net row precedes Long-Term Capital Gains and Losses. |
| `public_real_irs_1040sd_2024_p002` | `table_cell_exists_39e8665ad998` | `table_cell_exists` | approved | main | Part III Summary heading is visible. |
| `public_real_irs_1040sd_2024_p002` | `table_cell_exists_584f04c789a5` | `table_cell_exists` | approved | main | Capital Gain Tax Worksheet line is visible. |
| `public_real_irs_1040sd_2024_p002` | `reading_order_c4ae3284620e` | `` | approved_with_edit | removed | Original order was reversed; edited to Qualified Dividends before Schedule D Tax Worksheet. |
| `public_real_govinfo_cfr_title1_p014` | `reading_order_c3696e8c330f` | `reading_order` | approved | main | PART 1 appears before Administrative Committee definition. |
| `public_real_govinfo_cfr_title1_p014` | `reading_order_463faedcf7af` | `reading_order` | approved | main | Agency means appears before Document includes in the left column. |
| `public_real_govinfo_cfr_title1_p014` | `reading_order_6d673d9bc7b0` | `reading_order` | approved | main | Document includes appears before Document having general applicability. |
| `public_real_govinfo_cfr_title1_p014` | `reading_order_676d0d90e7d9` | `` | removed | removed | Removed from main RC because the cross-column anchor was too broad and failed sanity checks. |
| `public_real_govinfo_cfr_title1_p035` | `reading_order_5fd51a00c55e` | `reading_order` | approved | main | 21.19 appears before 21.35 in the contents-like list. |
| `public_real_govinfo_cfr_title1_p035` | `reading_order_dca7e39a47bb` | `reading_order` | approved | main | PART 21 appears before otherwise noted. |
