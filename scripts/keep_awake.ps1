# Keep Windows from sleeping while a long evaluation runs. Changes no power settings: the request
# lasts only while this process lives. Usage: powershell -File scripts/keep_awake.ps1 -Minutes 600
param([int]$Minutes = 600)
$signature = '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
$api = Add-Type -MemberDefinition $signature -Name Power -Namespace LedgerLens -PassThru
$ES_CONTINUOUS = [uint32]"0x80000000"
$ES_SYSTEM_REQUIRED = [uint32]"0x00000001"
$api::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED) | Out-Null
Start-Sleep -Seconds ($Minutes * 60)
$api::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
