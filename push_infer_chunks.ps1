# Script tu dong push tung nhom nho file infer_output
# Moi lan push ~4-5 file anh (khoang 10MB)

$folder = "260519/24class_infer_output"
$files = Get-ChildItem $folder | Sort-Object Name

$chunkSize = 4  # so file moi commit
$chunks = [System.Collections.ArrayList]::new()
$chunk = @()

foreach ($f in $files) {
    $chunk += "$folder/$($f.Name)"
    if ($chunk.Count -ge $chunkSize) {
        [void]$chunks.Add($chunk)
        $chunk = @()
    }
}
if ($chunk.Count -gt 0) { [void]$chunks.Add($chunk) }

$total = $chunks.Count
for ($i = 0; $i -lt $total; $i++) {
    $c = $chunks[$i]
    Write-Host "`n=== Chunk $($i+1)/$total ===" -ForegroundColor Cyan
    
    git add @($c)
    git commit -m "260519 infer chunk $($i+1)/$total"
    
    $ok = $false
    for ($retry = 0; $retry -lt 3; $retry++) {
        git push origin master
        if ($LASTEXITCODE -eq 0) { $ok = $true; break }
        Write-Host "  [WARN] Push failed, retry $($retry+1)/3..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
    
    if (-not $ok) {
        Write-Host "  [ERROR] Chunk $($i+1) push failed 3 times. Resetting..." -ForegroundColor Red
        git reset HEAD~1
        break
    }
    Write-Host "  [OK] Chunk $($i+1) pushed!" -ForegroundColor Green
}

Write-Host "`nDone!" -ForegroundColor Green
