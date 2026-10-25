# 初期inventoryの読取観測接続

2026-10-25。[C-32/OSD-01](../requirements/p0-open-specification-decisions.md#approved-decision-record--osd-01)を支える`inspect_initial_inventory`：[SourceInventoryRevalidation.py](../../Common/SourceInventoryRevalidation.py)。運用sync/archiveのmanifestとは別の内部immutable型を使い、永続record/schema/rootを採用しない。

独立したPC-A source信頼確認・exact B2・明示relative path tuple・log/run/root/scope/reference date/現在時計を既存source batch再観測へ渡す。呼出しごとに実sourceを全列挙/hashし、一致時だけ与えられたDrive前後列挙・download計画/完了hash集合を既存の厳密batch比較へ渡す。実Driveのquery/時系列/出所をこのhelperで認証するものではない。

初期inventory用の結果は元B2 bytes、選択path、pathごとの比較元とContentComparisonを保持する。順序と件数を検査して結び付け、同一内容候補・不在/競合/不明によるheldを区別する。共通Drive/計画/download不備ではstatus=held、比較file集合は空にして、選択pathとB2を保持する。部分比較を捏造せず、空の完全inventoryへ変えない。

共通入力が整合してもstatus=requires_runtime_evidenceで、選択した範囲の観測に限る。空の明示選択はno_workやinventory全件完了ではなく、元B2の既知validation errorsも消さない。毎回のsource再観測が失敗した場合は固定reasonの例外で停止し、過去の観測から補完/自動復元しない。

結果のmay_restore/may_report_sync_success/may_archive/may_publish_operational_manifestは常にfalse。型もInitialManifestPlan/TerminalManifestPlanと分離し、保存・state遷移・運用reportを生成しない。同じ保存済み結果の再利用をreceiptや出所/実行資格にしない。原名とPC suffix候補の別名化も行わず、既存OSD-01のexact name/size/hashを維持する。

[合成接続試験](../../tests/test_initial_inventory_observation.py)は両log、指定順とID binding、候補/不在の混在、共通不備時のB2/選択保全、PC-B/未信頼source拒否・source変更、空選択、既知error保全、内部件数不一致の停止を確認する。全FS I/Oは自作tempの合成sourceで、candidate/運用manifestへの書込み・実Drive接続はない。

実source/backup記録とfolder/query/metadata/完了の真正性・現在性、実SDK/C-02/credential、原子的snapshot/ABA・使用点root/FS/owner/clock資格、初期inventory専用の永続schema/保存領域と診断、復元/同期/両PC/archive gateとruntime受け入れは未実装・未実証のまま。
