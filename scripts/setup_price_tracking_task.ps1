# PowerShell script to set up Windows Task Scheduler for daily price tracking
# Run this as Administrator

$taskName = "Valora_Price_Tracking"
$scriptPath = "$PSScriptRoot\track_price_changes.py"
$pythonPath = (Get-Command python).Source
$workingDir = Split-Path -Parent $PSScriptRoot

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Task '$taskName' already exists. Removing old task..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create action
$action = New-ScheduledTaskAction -Execute $pythonPath `
    -Argument "scripts\track_price_changes.py" `
    -WorkingDirectory $workingDir

# Create trigger (daily at 1 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At 1am

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

# Register the task
Register-ScheduledTask -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Daily price tracking for Valora AI properties" `
    -User $env:USERNAME

Write-Host "`n✅ Scheduled task created successfully!"
Write-Host "Task Name: $taskName"
Write-Host "Schedule: Daily at 1:00 AM"
Write-Host "Script: $scriptPath"
Write-Host "`nTo view/manage the task:"
Write-Host "  - Open Task Scheduler (taskschd.msc)"
Write-Host "  - Look for '$taskName' in Task Scheduler Library"
Write-Host "`nTo run manually:"
Write-Host "  Start-ScheduledTask -TaskName '$taskName'"
