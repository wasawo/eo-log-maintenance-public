#requires -Version 7.6.7
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$JournalRoot,
    [Parameter(Mandatory)][guid]$RunId,
    [Parameter(Mandatory)][ValidateSet('PC-A', 'PC-B')][string]$MachineId,
    [Parameter(Mandatory)][ValidateSet('Sync', 'Archive')][string]$Operation,
    [string]$PythonExecutable = 'python',
    [ValidateRange(1, 300)][int]$TimeoutSeconds = 30,
    [switch]$AsJson
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../Common/LogFunctions.ps1')
if ($MachineId -eq 'PC-B' -and $Operation -eq 'Archive') { throw 'move_report_scope_invalid' }
$route = if ($Operation -eq 'Sync') { 'local_to_cloud' } else { 'cloud_to_archive' }
$start = [Diagnostics.ProcessStartInfo]::new()
$start.FileName = $PythonExecutable
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
foreach ($argument in @('-B', (Join-Path $PSScriptRoot '../Common/MoveRunReport.py'),
    '--journal-root', $JournalRoot, '--run-id', $RunId.ToString('D'), '--machine-id', $MachineId, '--route', $route)) {
    $start.ArgumentList.Add($argument)
}
$process = [Diagnostics.Process]::new()
$process.StartInfo = $start
try {
    try { [void]$process.Start() } catch { throw 'move_report_process_start_failed' }
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $process.Kill($true)
        $process.WaitForExit()
        throw 'move_report_process_timeout'
    }
    # Never forward raw Python stderr or a private journal path to the console.
    [void]$stderr.GetAwaiter().GetResult()
    $raw = $stdout.GetAwaiter().GetResult()
    if ($process.ExitCode -ne 0) {
        $safeReason = 'move_report_read_failed'
        try {
            $failure = $raw | ConvertFrom-Json -AsHashtable -ErrorAction Stop
            $allowedReasons = @('move_report_source_identity_conflict','move_journal_attempt_conflict',
                'move_journal_unexpected_entry','move_record_invalid','move_record_reference_digest_mismatch',
                'move_record_unavailable','move_journal_unavailable','move_report_scope_invalid',
                'move_record_reference_invalid','move_record_target_mismatch','move_record_reference_mismatch',
                'move_record_decision_invalid','move_record_file_invalid','move_record_changed',
                'move_journal_changed','move_record_id_mismatch')
            if ($failure -is [Collections.IDictionary] -and $failure.ok -is [bool] -and -not $failure.ok -and
                $failure.reason_code -cin $allowedReasons) { $safeReason = $failure.reason_code }
        }
        catch { }
        throw $safeReason
    }
    try { $response = $raw | ConvertFrom-Json -AsHashtable -ErrorAction Stop } catch { throw 'move_report_response_invalid' }
    try {
        if ($response -isnot [Collections.IDictionary] -or $response.Count -ne 2 -or
            @($response.Keys | Where-Object { $_ -cnotin @('ok','report') }).Count -ne 0 -or
            $response.ok -isnot [bool] -or -not $response.ok) { throw 'invalid' }
        $report = $response.report
        $keys = @('report_version','run_id','machine_id','route','run_records_present','prepared_source_count',
            'newly_completed_source_count','deleted_source_count','reconciled_source_count',
            'already_completed_source_count','unresolved_source_count','carried_unresolved_source_count','details')
        if ($report -isnot [Collections.IDictionary] -or $report.Count -ne $keys.Count -or
            @($report.Keys | Where-Object { $_ -cnotin $keys }).Count -ne 0 -or
            ($report.report_version -isnot [int] -and $report.report_version -isnot [long]) -or $report.report_version -ne 1 -or
            $report.run_id -cne $RunId.ToString('D') -or $report.machine_id -cne $MachineId -or
            $report.route -cne $route -or $report.run_records_present -isnot [bool] -or $report.details -isnot [Array]) { throw 'invalid' }
        foreach ($key in @($keys | Where-Object { $_.EndsWith('_count') })) {
            if (($report[$key] -isnot [int] -and $report[$key] -isnot [long]) -or $report[$key] -lt 0) { throw 'invalid' }
        }
        foreach ($item in $report.details) {
            $detailKeys = @('move_ref','log_type','state','completion_basis','reason_code','next_action','from_prior_run')
            if ($item -isnot [Collections.IDictionary] -or $item.Count -ne $detailKeys.Count -or
                @($item.Keys | Where-Object { $_ -cnotin $detailKeys }).Count -ne 0 -or
                $item.move_ref -cnotmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' -or
                $item.log_type -cnotin @('BattleLog','ErrorReport','unknown') -or
                $item.state -cnotin @('completed','incomplete','unknown') -or
                $item.completion_basis -cnotin @('none','delete_confirmed','reconciled') -or
                $item.next_action -cnotin @('none','inspect_records','reobserve','retry_move') -or $item.from_prior_run -isnot [bool] -or
                $item.reason_code -cnotin @('result_not_recorded','move_identity_conflict','current_results_ambiguous',
                    'prior_unresolved_records','delete_confirmed','delete_pending','delete_failed','not_sent',
                    'verification_unknown','source_changed','destination_mismatch','reconciled_completion','state_unconfirmed')) { throw 'invalid' }
        }
    }
    catch { throw 'move_report_response_invalid' }
    if ($AsJson) { $report | ConvertTo-Json -Depth 8; return }
    Write-Output '保存された移動記録の概要'
    Write-Output ("実行: {0} / {1} / {2}" -f $RunId, $MachineId, $Operation)
    if (-not $report.run_records_present) { Write-Output '指定実行の記録がありません。対象なしとは判定できません。' }
    Write-Output ("準備済み元: {0} / 今回初めて完了: {1}（削除確認 {2}・照合確認 {3}）" -f
        $report.prepared_source_count, $report.newly_completed_source_count, $report.deleted_source_count, $report.reconciled_source_count)
    Write-Output ("完了済みの再確認: {0} / 未解決: {1}（過去実行から {2}）" -f
        $report.already_completed_source_count, $report.unresolved_source_count, $report.carried_unresolved_source_count)
    foreach ($item in $report.details) {
        $state = switch ($item.state) { 'completed' { '完了記録あり' } 'incomplete' { '未完了' } default { '結果不明' } }
        $action = switch ($item.next_action) { 'none' { '記録上の追加対応なし' } 'inspect_records' { '記録の不整合を確認' } 'retry_move' { '移動処理の再実行が必要' } default { '現在状態の再観測が必要' } }
        Write-Output ("{0} / {1} / {2} / {3}" -f $item.move_ref, $item.log_type, $state, $action)
    }
}
finally { $process.Dispose() }
