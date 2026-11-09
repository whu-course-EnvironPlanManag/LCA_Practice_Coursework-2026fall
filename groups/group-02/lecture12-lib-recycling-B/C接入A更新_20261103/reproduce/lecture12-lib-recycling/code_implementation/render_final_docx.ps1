$ErrorActionPreference = 'Stop'
$taskBase = Split-Path -Parent $PSScriptRoot
$workspaceBase = Split-Path -Parent $taskBase
$sourcePath = (Get-ChildItem -LiteralPath (Join-Path $workspaceBase 'outputs') -Recurse -Filter '*.docx' | Where-Object { $_.Directory.Name -like '*20261103' -and $_.Directory.Parent.Name -eq 'outputs' } | Select-Object -First 1).FullName
$qaFolder = Join-Path $taskBase 'report\final_integration_20261103\docx_qa'
New-Item -ItemType Directory -Path $qaFolder -Force | Out-Null
$pdfPath = Join-Path $qaFolder 'C_final_layout.pdf'
$wordApp = $null
$document = $null
try {
    $wordApp = New-Object -ComObject Word.Application
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $document = $wordApp.Documents.Open($sourcePath, $false, $true)
    $document.Repaginate()
    $pageCount = $document.ComputeStatistics(2)
    $document.ExportAsFixedFormat($pdfPath, 17)
    Write-Output "Pages: $pageCount"
    Write-Output $pdfPath
} finally {
    if ($null -ne $document) { $document.Close(0) }
    if ($null -ne $wordApp) { $wordApp.Quit() }
}
