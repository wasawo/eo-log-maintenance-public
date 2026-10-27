# private証拠file ACLの限定形状

状態: 同一account方針は承認済み。渡された観測を分類する補助処理のみ。実ACL検査/変更や保存認可ではない。
根拠: [account方針](../../archive/decisions/recovery-execution-account-policy-proposal.md)、[private保管契約](../recovery-private-evidence-contract.md)。

## 部分実装の境界

Common/PrivateEvidenceAclProfile.pyは、1つのfileの正規化済みdescriptor観測と実行user SIDの申告を受け取る。
実OS、file、account、tokenを照会せず、SIDが実際の実行userかどうかも証明しない。
返すのはprofile_matches/固定reason/may_change_state=falseだけ。raw owner/trustee SIDを結果へ出さず、入力も変更しない。
profile_matches=trueは限定形状への一致であり、実効アクセスの確認・root資格・実保存許可ではない。

## 最初に受け入れる形状

- object_kindはfileだけ。directory/祖先/volumeは別の資格確認が必要。
- 所有者は申告execution user、SYSTEM、local Administratorsのいずれか。
- DACLはpresent・non-null・protectedを全て明示する。継承可のDACLはこの初期profileでは受け入れない。
- ACEはflags=0のplain allowだけ。trusteeは上記3種に限り、外部account/Everyone/Authenticated Users等を拒否する。
- maskはfile-specific/standard bitsだけ。generic mask・未知bit・deny/object/callback ACE・継承/伝播flagは保留する。genericの推測展開をしない。
- execution user自身への明示read_data/write_dataを要求し、Administrators等へのgrantをuserの権限に読み替えない。
- 初期user SID構文はdomain/local user型とAzureAD型のみ。実SIDの存在/所属/token種別の証明ではなく、未知familyは停止する。

この狭い形状から外れるACLを「公開されている」と断定しない。複雑なACLの実効アクセスを計算せず、unsupportedとして停止するためのprofile。
13合成テストはworld/foreign owner/grant、null/empty、継承、denyによる取り消しの誤認、generic/未知mask、group推測、出力非漏えいを検証する。
テストのSIDは固定ダミー。実name/SID/資格情報を収集せず、権限・task・configを変更しない。

## Windows一次資料と限界

[Null DACLs and Empty DACLs](https://learn.microsoft.com/en-us/windows/win32/secauthz/null-dacls-and-empty-dacls)に従い、null/absentと空DACLを同一視しない。
[How AccessCheck Works](https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object)はtokenのuser/group属性とACE順序がアクセス判定に関係することを説明する。
本helperはそのアルゴリズムを実装せず、denyを含む複雑なACLを許可方向に解釈しない。

未実装: descriptor取得・provider完全性、actual execution tokenとのbinding、impersonation/group/privilege、directory/祖先のdelete-child/置換、root/ACL変更から利用までの保護、必要権限付き新規作成、実効アクセス検証。
実taskのログオン方式・昇格などは同一accountだけでは決まらない。OSD-08の残る運用方針を別途確定する。
STORE-01やACL全体・P0/Tier Bをこの部分実装で完了にしない。

## Binary descriptor normalization slice

Common/PrivateFileSecurityDescriptor.ps1 adds ConvertFrom-EoPrivateFileSecurityDescriptor for supplied self-relative binary descriptors. It clones input bytes, requires an exact binary round trip, preserves ACE order/deny/flags and unsigned masks, and rejects owner absence, object/callback ACE, SACL and unsupported control flags instead of dropping them. The output is private internal SID-bearing data; only the existing Python assessment is suitable for sanitized diagnostics. Six cross-runtime tests cover sixteen synthetic descriptors. No Get-Acl/file/token query, ACL write, actual execution-user binding, effective-access/ancestry qualification or runtime permit is added. See [RawSecurityDescriptor](https://learn.microsoft.com/en-us/dotnet/api/system.security.accesscontrol.rawsecuritydescriptor) and [CommonAce](https://learn.microsoft.com/en-us/dotnet/api/system.security.accesscontrol.commonace) for the .NET representations.
