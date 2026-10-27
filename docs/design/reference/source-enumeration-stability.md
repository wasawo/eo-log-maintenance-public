# Source列挙の完了前再確認

2026-10-25。[ソースビルダー](../../../Common/SourceInventoryEvidenceBuilder.py)のB2 coverage判定を強化する。[ランタイム ゲート](../runtime-entrypoint-validation-gate.md)の完全列挙条件を支える観測であり、atomic snapshotや後続利用の認可ではない。

各directoryを列挙する時点でroot/祖先のidentity、child名集合と各entryのidentity/type/size/mtime/reparse属性/link数を保持する。全hash・分類後、各directoryを再列挙して同じ観測と比較する。root/祖先の変更、追加/削除/rename、既にhashしたfileの属性変化、directory差替え、再確認不能を検出したらenumeration_errorsを増やし、enumeration/validation coverageをincompleteにする。観測済みtarget/hash/errorは消さず、0件やno_workへ置き換えない。

child metadataが不明・reparseならそのdirectoryのsnapshotは採用せず、不完全扱いとする。reparseの先を走査しない。scandirはcontext managerでcloseし、最後の確認もsourceを書き換えない。初期planは不完全B2をrunning候補として保持できるが、[使用点再観測](source-inventory-revalidation.md)は不完全coverageを認可へ変えず、候補公開前に停止する。

比較は観測可能なnamespace/属性の変更に限る。最後の再確認後の変更、bytes変更と属性復元によるABA、同一bytesへの置換、実効ACL/root/FS/ownerの資格、各directoryが同時点に存在したことは証明しない。eligible fileは読取時にhashするが、最終passで全bytesを再hashするものではない。実使用点では独立したfreshな検査を要する。

[合成試験](../../../tests/test_source_enumeration_stability.py)は専用tempで追加/削除/rename/同サイズ内容変更・directory追加/差替え、空列挙後の追加、最終rescan失敗、non-targetの列挙中変更、所有lock内の使用点検査から候補書込み前停止までを確認する。実ログ/Drive・削除/回復・runtime受け入れは含まない。既存reparse試験も、複数回のroot再確認を許しつつjunction先へ走査しないことを維持する。

## Hash読取の早期停止

開いたhandleのregular-file属性とdev/ino/size/mtimeを、最初のbyteを読む前に直前のpath観測と照合する。不一致なら読まずに停止する。読取は観測サイズの残り＋1 byte（各chunk最大1 MiB）までを要求し、総byte数が観測サイズを超えた時点で停止する。連続追記fileのEOFを追い続けず、短い読取も最後のサイズ/metadata照合で拒否する。空fileと1 MiB境界でもexact bytesのhashを維持する。

拒否は既存の`source_mutation_detected`として扱い、builderでは不完全coverageになる。handleはcontextを抜ける際にcloseする。OS読取自体のblockに対するtimeoutや最大file-sizeポリシーを追加するものではなく、hash後の変化や敵対的ABAを防ぐ資格はない。[hash試験](../../../tests/test_source_hash_identity.py)では別handleを読まないこと、EOFが返らない模擬streamでの超過時停止、short read、空/境界サイズを検査する。
