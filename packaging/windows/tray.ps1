param([string]$Url,[string]$Instance,[string]$Icon,[string]$DataDir)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$tray=New-Object System.Windows.Forms.NotifyIcon
$tray.Icon=New-Object System.Drawing.Icon($Icon)
$tray.Text='Christ Church Video Cleanup - Starting'
$menu=New-Object System.Windows.Forms.ContextMenuStrip
$task=$menu.Items.Add('Starting local services...');$task.Enabled=$false
$title=$menu.Items.Add('');$title.Enabled=$false
$detail=$menu.Items.Add('');$detail.Enabled=$false
$timing=$menu.Items.Add('');$timing.Enabled=$false
[void]$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator))
$startupPython=Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'runtime\python.exe'
$startupScript=Join-Path $PSScriptRoot 'startup.py'
$startup=$menu.Items.Add('Start automatically at login')
$startup.Checked=((& $startupPython $startupScript status) -eq 'enabled')
$startup.Add_Click({
    $startup.Enabled=$false
    try {
        $action=if($startup.Checked){'disable'}else{'enable'}
        $result=& $startupPython $startupScript $action 2>&1
        if($LASTEXITCODE -ne 0){throw ($result -join "`n")}
    } catch {
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'Could not change login startup','OK','Error')|Out-Null
    } finally {
        $startup.Checked=((& $startupPython $startupScript status) -eq 'enabled')
        $startup.Enabled=$true
    }
})
$open=$menu.Items.Add('Open Christ Church Video Cleanup')
$quit=$menu.Items.Add('Quit and stop services')
$open.Add_Click({Start-Process $Url})
$tray.Add_DoubleClick({Start-Process $Url})
$quit.Add_Click({
    $force=$false
    try {
        $state=Invoke-RestMethod "$Url/api/tray" -TimeoutSec 3
        if($state.busy){
            if(-not $state.desktop_active){throw 'A command-line job is running. Finish it before closing services.'}
            $answer=[System.Windows.Forms.MessageBox]::Show('Stopping interrupts the current job. Saved sources and analysis are kept. Stop services now?','A service is still processing','YesNo','Warning','Button2')
            if($answer -ne 'Yes'){return};$force=$true
        }
        $body=@{instance=$Instance;force=$force}|ConvertTo-Json
        Invoke-RestMethod "$Url/api/shutdown" -Method Post -ContentType 'application/json' -Headers @{'X-CCS-Request'='1'} -Body $body -TimeoutSec 5 | Out-Null
        $tray.Visible=$false;[System.Windows.Forms.Application]::Exit()
    } catch {
        [System.Windows.Forms.MessageBox]::Show('Services could not be stopped. Setup or processing may still be running. '+$_.Exception.Message,'Christ Church Video Cleanup','OK','Information')|Out-Null
    }
})
$tray.ContextMenuStrip=$menu;$tray.Visible=$true
$timer=New-Object System.Windows.Forms.Timer;$timer.Interval=4000
$timer.Add_Tick({
    try {
        $state=Invoke-RestMethod "$Url/api/tray" -TimeoutSec 2
        $feedback=$state.feedback
        $task.Text=$feedback.task;$title.Text=$feedback.title;$detail.Text=$feedback.detail;$timing.Text=$feedback.timing
        $title.Visible=[bool]$feedback.title;$detail.Visible=[bool]$feedback.detail;$timing.Visible=[bool]$feedback.timing
        $tip='Christ Church: '+$feedback.task
        if($tip.Length -gt 63){$tip=$tip.Substring(0,63)};$tray.Text=$tip
        @{pid=$PID;visible=$tray.Visible;task=$task.Text;title=$title.Text;detail=$detail.Text;timing=$timing.Text;startup_enabled=$startup.Checked}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $DataDir 'tray-state.json')
    } catch {
        $task.Text='Starting or reconnecting...';$tray.Text='Christ Church Video Cleanup - Starting'
    }
})
$timer.Start()
try {[System.Windows.Forms.Application]::Run()} finally {$timer.Stop();$tray.Visible=$false;$tray.Dispose()}
