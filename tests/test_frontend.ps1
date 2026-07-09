# Frontend Page Rendering Tests
Write-Host "=== Frontend Page Rendering Tests ===" -ForegroundColor Cyan

$baseUrl = "http://localhost:6789"
$pass = 0
$fail = 0

function Test-Page($name, $url) {
    try {
        $r = Invoke-WebRequest -Uri $url -TimeoutSec 30 -UseBasicParsing
        $html = $r.Content
        $hasError = $false

        # Check for common error patterns
        if ($html -match "Cannot read prop|is not defined|TypeError|ReferenceError|500 Internal Server Error") {
            $hasError = $true
        }

        # Check for Nuxt error page
        if ($html -match "nuxt-error-page|__nuxt_error") {
            $hasError = $true
        }

        if ($hasError) {
            Write-Host "[FAIL] $name - Error patterns found in HTML" -ForegroundColor Red
            $script:fail++
        } else {
            $hasContent = $html.Length -gt 1000
            if ($hasContent) {
                Write-Host "[PASS] $name (HTML size: $($html.Length) chars)" -ForegroundColor Green
                $script:pass++
            } else {
                Write-Host "[WARN] $name - HTML too short ($($html.Length) chars)" -ForegroundColor Yellow
                $script:fail++
            }
        }
    } catch {
        Write-Host "[FAIL] $name - $($_.Exception.Message)" -ForegroundColor Red
        $script:fail++
    }
}

# Test all pages
Test-Page "Home Page" "$baseUrl/"
Test-Page "File System Page" "$baseUrl/file-system"
Test-Page "Knowledge Base Page" "$baseUrl/knowledge-base"
Test-Page "Knowledge Search Page" "$baseUrl/knowledge-search"
Test-Page "Knowledge Graph Page" "$baseUrl/knowledge-graph"
Test-Page "About Page" "$baseUrl/about"

# Test graph build endpoint
Write-Host ""
Write-Host "Testing Graph Build..." -ForegroundColor Cyan
try {
    $body = @{ force = $false } | ConvertTo-Json
    $r = Invoke-RestMethod -Uri "$baseUrl/api/graph/build-all" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 60
    Write-Host "[PASS] Graph Build-All" -ForegroundColor Green
    $pass++
    if ($r.result) {
        Write-Host "  Total KBs: $($r.result.total_top_kbs)"
        Write-Host "  Processed: $($r.result.kbs.Count) KBs"
    }
} catch {
    Write-Host "[FAIL] Graph Build-All - $($_.Exception.Message)" -ForegroundColor Red
    $fail++
}

Write-Host ""
Write-Host "=== Results: $pass passed, $fail failed ===" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
