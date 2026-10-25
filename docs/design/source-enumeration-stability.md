# Source列挙の完了前再確認

2026-10-25。[source builder](../../Common/SourceInventoryEvidenceBuilder.py)のB2 coverage判定を強化する。[runtime gate](runtime-entrypoint-validation-gate.md)の完全列挙条件を支える観測であり、atomic snapshotや後続利用の認可ではない。

各directoryを列挙する時点でroot/祖先のidentity、child名集合と各entryのidentity/type/size/mtime/reparse属性/link数を保持する。全hash・分類後、各directoryを再列挙して同じ観測と比較する。root/祖先の変更、追加/削除/rename、既にhashしたfileの属性変化、directory差替え、再確認不能を検出したらenumeration_errorsを増やし、enumeration/validation coverageをincompleteにする。観測済みtarget/hash/errorは消さず、0件やno_workへ置き換えない。

child metadataが不明・reparseならそのdirectoryのsnapshotは採用せず、不完全扱いとする。reparseの先を走査しない。scandirはcontext managerでcloseし、最後の確認もsourceを書き換えない。初期planは不完全B2をrunning候補として保持できるが、[使用点再観測](source-inventory-revalidation.md)は不完全coverageを認可へ変えず、候補公開前に停止する。

比較は観測可能なnamespace/属性の変更に限る。最後の再確認後の変更、bytes変更と属性復元によるABA、同一bytesへの置換、実効ACL/root/FS/ownerの資格、各directoryが同時点に存在したことは証明しない。eligible fileは読取時にhashするが、最終passで全bytesを再hashするものではない。実使用点では独立したfreshな検査を要する。

[合成試験](../../tests/test_source_enumeration_stability.py)は専用tempで追加/削除/rename/同サイズ内容変更・directory追加/差替え、空列挙後の追加、最終rescan失敗、non-targetの列挙中変更、所有lock内の使用点検査から候補書込み前停止までを確認する。実ログ/Drive・削除/回復・runtime受け入れは含まない。既存reparse試験も、複数回のroot再確認を許しつつjunction先へ走査しないことを維持する。
