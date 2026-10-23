# 回復用owner証拠と既存v1 lockの扱い（判断案）

状態: v1保全・v2証拠契約を設計する互換方針は利用者承認済み（2026-10-23）。v2 schema/通常lock writer/旧record変更は未実装。
根拠: [明示回復の承認済み方向](recovery-disposition-proposal.md)、[診断設計](explicit-recovery-command-design.md)。

## 現状

現行v1 recordはschema_version/scope_id/owner_token/pid/hostを持つ。
正常所有者のtoken照合には使うが、将来の回復でPID再利用・同名host・再起動をまたぐ旧processの同一性/終了を証明するには不足する。
mutex放棄通知も診断で消費され得るため、永続的な終了証拠の代用にしない。
既存helperのowner_termination_confirmedという入力boolは、OS証拠を収集/検証する実装ではない。

## 承認された運用互換方針

- 既存v1 recordは診断・証拠保全のみとし、自動回復・自動v2変換・削除/退避/引継ぎの対象にしない。
- 将来の明示回復は、必要な証拠を生成時から記録した新形式v2のみを対象に設計する。
- v1が残った場合は通常同期の停止を維持し、別途レビューする非破壊の運用回復手順へ案内する。手作業でlockを削除すればよいという手順は作らない。
- 既存の正常なv1所有者の通常releaseまで禁止する変更ではない。既存writer/readerはこの案では変更しない。

利用者が選ぶのはこの互換方針。v2の正確なfields/schemaや本番操作を同時に承認するものではない。

## v2で具体化する証拠（未確定の技術契約）

1. OSから取得するprocess生成identityと、再起動/端末の同一性を誤認しない結び付け。host名やPIDだけで代用しない。
2. scopeと所有tokenへの結び付け。trusted root/設定・対象runとの対応を別途検証する。
3. 同一processの終了・不在/別processへのPID再利用・query不能を区別する検証。Access deniedや取得失敗は終了扱いせず保留する。
4. OS情報の出所・取得権限・不足/改変・時刻依存を検討し、必要な証拠を供給できない環境では生成/回復を拒否する。
5. v2は既存v1を読んで補完しない。取得時からの証拠を必要とし、unknown version/fieldや重複keyを拒否する。

この案は新規個人情報を公開しない。private証拠の保存領域・ACL・保持、disposition方式、安全な対象固定はなお未確定。

## 実装前の検証計画

- v1/未知version/不足fieldから回復を開始せず、入力recordと旧running bytesを保全する。
- 生存・正常終了・異常終了・PID再利用・再起動・情報取得失敗を固定した合成providerで区別する。
- 同一recordの情報差し替え、証拠の転用、診断後変更を拒否する。
- API/OS実体の試験は別途一次資料で契約を確認し、合成子processでのみ行う。
- いずれも未実行。v2 schemaや実運用復旧を既存CI成功で完成扱いしない。

## 利用者判断（2026-10-23）

「v1は診断・保全に限定し、v2の証拠契約を設計する（推奨）」を選択した。
この互換方針を同じ内容で再確認しない。v1の正常release、writer/readerはこの記録では変更しない。
具体化した[owner証拠契約](recovery-owner-evidence-v2-contract.md)を参照。
