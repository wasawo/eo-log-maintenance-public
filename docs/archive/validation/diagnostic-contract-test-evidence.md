# 診断契約 C-45–C-54: 実装およびテストの証拠

> 履歴/検討資料。承認済みの選択・未決候補・当時の監査根拠を含み、この移動は撤回/失効を意味しない。現在の基準は[正式要件](../../requirements/log-move-requirements.md)と[現行決定台帳](../../decisions/decision-register-c18-c32.md)。当時の対象/証拠を現在のruntime受け入れへ拡張しない。

**ステータス:** の非規範的証拠の対応表、2026-10-21 の PR #140、#141、#144、および #146 について更新されました。規範的な決定は docs/archive/decisions/aggregation-inventory-integrity-options.md および docs/archive/decisions/decision-record-c54-sensitive-path-detection.md. に残ります

## 現在追跡されている実装

| 契約 | 追跡された実装/テスト | テストで確立されるもの | 残りのギャップ |
| --- | --- | --- | --- |
| C-45 イベント ID | Common/LogFunctions.ps1: New-DiagnosticErrorId; tests/Test-DiagnosticErrorId.ps1; docs/archive/decisions/c45-event-identity-conflict-options.md | 呼び出し元が所有する実行ごとの単調カウンターは、単一のテスト シーケンス内で一意の連続 ID を生成します。メンテナが承認したオプション A では、証拠の最終化/公開時に、1 つの ID で競合する不変/コア属性がフェイルクローズされる必要があります。 | ランタイム イベントの作成、個別イベントごとに 1 つの割り当て、伝播/重複排除、競合検出、およびフェールクローズの強制は実装/テストされていません。ポリシー決定は、実行時の受け入れの証拠ではありません。 |
| C-46 ID エンコードと枯渇 | 同じアロケーターとテスト | 正確な ERR-000001 スタイルの固定幅フォーマット。 ERR-999999 は最終的な ID です。疲れは閉じられない。書式設定は文化に依存しません。 | ランタイム実行スコープのアロケーター所有者や同時実行/シリアル化コントラクトは実装されていません。 |
| C-47 レコード/パスの制約 | ConvertTo-FinalizedDiagnosticJson; ConvertTo-SafeDiagnosticRelativePath; tests/Test-DiagnosticRecordFinalizer.ps1; tests/Test-DiagnosticPathSanitization.ps1 | 7 フィールドのレコード形状。安全なオプションのパス。 1024 Unicode スカラー値のパス キャップ。超過/安全でないパスは JSON null になります。 | エンドツーエンドの証拠パイプラインはありません。ソースとルートの関係は相対パス契約として表され、ファイルシステムに対して解決されません。 |
| C-48 バージョンの互換性 | ConvertTo-FinalizedDiagnosticJson; Test-DiagnosticRecordFinalizer.ps1 | スキーマ バージョン 1 は整数である必要があります。欠落している/サポートされていない/非整数のバージョンと欠落している/不明なフィールドは拒否されます。 | API は、生の JSON ではなく、すでに構造化された辞書を受け入れます。重複する JSON プロパティ名は、ディクショナリが具体化される前に、将来の raw-JSON 取り込み境界で拒否される必要があります。 |
| C-49 管理語彙 | ConvertTo-FinalizedDiagnosticJson; Test-DiagnosticRecordFinalizer.ps1 | 正確なエラーコードの許可リストと有効なフェーズ/操作のペア。無効な値と大文字小文字の違いは拒否されます。 | 実行時の失敗とコードのマッピングは統合されていません。 |
| C-50 失敗-条件マッピング | Common/LogFunctions.ps1 の DiagnosticErrorCode を解決します。 tests/Test-DiagnosticErrorCodeClassifier.ps1; aggregation-inventory-integrity-options.md の標準契約 | 承認されたオプション スカラー条件トークンは、C-49 error_code ホワイトリストに決定的にマッピングされます。 14 マッピングと不正な入力拒否のケースは、Validate CI で実行されます。 | プロデューサー側の優先順位の選択、イベントの作成/伝播/重複排除、生の JSON 重複キーの拒否、ランタイム シンクの非公開、およびエンドツーエンドの証拠は未実装/実行されないままになります。ヘルパーのカバレッジは実行時に受け入れられません。 |
| C-51 フェーズ/動作マッピング | Common/LogFunctions.ps1 の Resolve-DiagnosticPhaseOperation; tests/Test-DiagnosticPhaseOperationResolver.ps1; Test-DiagnosticRecordFinalizer.ps1; aggregation-inventory-integrity-options.mdの規範的契約 | 承認されたオプション C の操作トークンは、その固有のフェーズに決定論的にマッピングされます。正確な動作が維持されます。すべての 13 行、無効な入力、大文字と小文字の違い、コレクション形式の値、非文字列、および再現性が Validate CI でテストされます。 | プロデューサーのセマンティックの正確性、ランタイム イベントの作成/伝播、元のイベントの ID の保存、およびエンドツーエンドの証拠は未実装のまま/実行されません。リゾルバーのカバレッジは実行時に受け入れられません。 |
| C-52 メッセージを修正しました | ConvertTo-FinalizedDiagnosticJson; Test-DiagnosticRecordFinalizer.ps1 | 許可リストに登録された各コードは、正確に承認されたメッセージとペアになっています。不一致/ヌル/コントロールを含むメッセージは拒否されます。生産量は文化を問わず安定しています。 | このファイナライザーに実行時エラー イベントがフィードされることはありません。例外由来メッセージのプロセス境界での非公開が確立されていない。 |
| C-53 パス構文とフィールドのヌル化 | ConvertTo-SafeDiagnosticRelativePath; ConvertTo-FinalizedDiagnosticJson;どちらの診断テストも | 相対パス構文、正規の区切り文字、機密ポリシーの順序付け、Unicode の有効性、1024 スカラーの最大値、安全でないオプション パスでの明示的な JSON null、およびイベント ID/分類の保持。 | 実際のランタイム診断パイプラインや生の JSON 取り込み境界はありません。 |
| C-54 センシティブなパスの検出 | ConvertTo-SafeDiagnosticRelativePath; tests/Test-C54PatternContract.ps1; tests/Test-DiagnosticPathSanitization.ps1 | 承認された固定機密名/トークンおよび P1 ～ P6 パターンは、合成フィクスチャでカバーされます。 | 運用ログ/認証情報やエンドツーエンドのロギング シンクは実行されません。実行時の非公開は未検証のままです。 |

## CI 証拠

- PR #140 は 454041f4337d5f22550a288dfd74afecde76635a にマージされました。正確なヘッド検証の実行 39509321771 とパッケージ検証の実行 39509321735 が 6a7222db4387019c6dc598c2b9bf38b6efca3c4c で成功しました。マージ後のメイン検証実行 39509466949 とパッケージ検証実行 39509467065 が 454041f4337d5f22550a288dfd74afecde76635a で成功しました。
- PR #141 は 58aeb10e3661b7cd893e1a6bfed0469e29e4089f にマージされました。正確なヘッド検証の実行 39509756240 とパッケージ検証の実行 39509756267 が fe5428248fe5fbef51acd396a1e4bca33438ae53 で成功しました。マージ後のメイン検証実行 39509903050 とパッケージ検証実行 39509903012 は両方とも SHA 58aeb10e3661b7cd893e1a6bfed0469e29e4089f のマージに成功しました。

## 許容境界

この対応表は、ヘルパーおよび合成テストのカバレッジのみを記録します。 C-50 には純粋なトークンからコードへのヘルパーが追加されましたが、これには、信頼できるプロデューサーの統合、優先順位の強制、ランタイム診断の生成、イベント伝播、生の JSON 重複キーの拒否、ランタイム ログシンクの非公開、または P0 の受け入れは要求されません。 P0-008、P0-010、および P0-012 は開いたままになります。 docs/schema/helper/package CI は実行時証拠に昇格させてはなりません。


## OSD-02 タイムスタンプ/鮮度ポリシー — 受け入れクロスウォーク (PR スコープ)

- 承認されたポリシー: UTC ISO 8601 (大文字の `Z`)。不正な形式/オフセット/タイムゾーンのないタイムスタンプと開始前終了を拒否します。
- 初期構成可能なデフォルト: 5 分の将来の最大スキュー。 24 時間の鮮度のしきい値。
- 鮮度スコープ: 現在の実行中にのみ生成または更新されたタイムスタンプ。歴史上の明示的な経過時間だけで歴史が無効になるわけではありません。
- クロック: OS 同期が構成されていると仮定します。現在の UTC を確実に取得できない場合、時間に依存する操作のフェール クローズ。外部監視サービスは必須ではありません。
- 必要なテストはまだ証明されていません: 固定クロック境界のケース、不正な形式/順序のケース、無効な構成、クロック 利用不能 の処理、過去の経過時間の動作。
- ステータス: 承認された仕様のみ。ランタイム実装や実行可能テストの結果は主張されません。
