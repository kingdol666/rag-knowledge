# Detailed Search & Graph API Tests
Write-Host "=== Detailed Search & Graph API Tests ===" -ForegroundColor Cyan

$baseUrl = "http://localhost:6789"
$pass = 0
$fail = 0

function Test-Name($name, $condition, $detail = "") {
    if ($condition) {
        Write-Host "[PASS] $name" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "[FAIL] $name $detail" -ForegroundColor Red
        $script:fail++
    }
}

# === Two-Stage Search Field Verification ===
Write-Host "`n--- Two-Stage Search Field Verification ---" -ForegroundColor Yellow
$body = @{ query = "polymer stretching"; stage1_top_k = 10; stage2_top_k = 3; balance_kbs = $true } | ConvertTo-Json
$r = Invoke-RestMethod -Uri "$baseUrl/api/search/two-stage" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30

Test-Name "Has success field" ($r.success -eq $true)
Test-Name "Has stage1" ($null -ne $r.stage1)
Test-Name "Has stage1.candidates" ($null -ne $r.stage1.candidates)
Test-Name "Has stage2" ($null -ne $r.stage2)
Test-Name "Has stage2.results" ($null -ne $r.stage2.results)
Test-Name "Has total_results" ($null -ne $r.total_results)
Test-Name "Results count > 0" ($r.total_results -gt 0) "($($r.total_results) results)"

if ($r.stage2.results.Count -gt 0) {
    $first = $r.stage2.results[0]
    Test-Name "Result has content" ($null -ne $first.content) "content length: $($first.content.Length)"
    Test-Name "Result has doc_path" ($null -ne $first.doc_path -and $first.doc_path -ne "") "value: $($first.doc_path)"
    Test-Name "Result has score" ($null -ne $first.score) "value: $($first.score)"
    Test-Name "Result has kb_id" ($null -ne $first.kb_id) "value: $($first.kb_id)"
    Test-Name "Result has stage1_score" ($null -ne $first.stage1_score) "value: $($first.stage1_score)"
    Test-Name "Result has source" ($null -ne $first.source) "value: $($first.source)"

    Write-Host "`n  Sample result:" -ForegroundColor Cyan
    Write-Host "    doc_path: $($first.doc_path)"
    Write-Host "    score: $($first.score)"
    Write-Host "    stage1_score: $($first.stage1_score)"
    Write-Host "    source: $($first.source)"
    Write-Host "    content preview: $($first.content.Substring(0, [Math]::Min(200, $first.content.Length)))..."
}

# === Vector Search Field Verification ===
Write-Host "`n--- Vector Search Field Verification ---" -ForegroundColor Yellow
$body = @{ query = "neural network deep learning"; top_k = 3; balance_kbs = $true } | ConvertTo-Json
$r = Invoke-RestMethod -Uri "$baseUrl/api/search/vector" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30

Test-Name "Vector search has success" ($r.success -eq $true)
Test-Name "Vector search has results" ($null -ne $r.results)
Test-Name "Vector search count > 0" ($r.count -gt 0) "($($r.count) results)"

if ($r.results.Count -gt 0) {
    $first = $r.results[0]
    Test-Name "Vector result has content" ($null -ne $first.content)
    Test-Name "Vector result has doc_path" ($null -ne $first.doc_path -and $first.doc_path -ne "")
    Test-Name "Vector result has score" ($null -ne $first.score)
    Test-Name "Vector result has kb_id" ($null -ne $first.kb_id)
    Write-Host "`n  Sample vector result:" -ForegroundColor Cyan
    Write-Host "    doc_path: $($first.doc_path)"
    Write-Host "    score: $($first.score)"
}

# === Graph Neighbors Test ===
Write-Host "`n--- Graph Neighbors Test ---" -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "$baseUrl/api/graph/stats" -TimeoutSec 10
    $stats = $r.stats
    Write-Host "  Graph stats: $($stats.node_count) nodes, $($stats.edge_count) edges"
    Test-Name "Graph stats has node_count" ($stats.node_count -gt 0)
    Test-Name "Graph stats has edge_count" ($stats.edge_count -gt 0)
    Test-Name "Graph stats has doc_count" ($stats.doc_count -gt 0)
} catch {
    Test-Name "Graph stats" $false $_.Exception.Message
}

# === Graph Search Test ===
Write-Host "`n--- Graph Search Test ---" -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "$baseUrl/api/graph/search?keyword=attention&type=documents&limit=5" -TimeoutSec 10
    Test-Name "Graph search returns results" ($r.success -eq $true) "success: $($r.success)"
    Test-Name "Graph search count > 0" ($r.count -gt 0) "count: $($r.count)"
    if ($r.documents -and $r.documents.Count -gt 0) {
        Write-Host "  First doc: $($r.documents[0].name)"
    }
} catch {
    Test-Name "Graph search" $false $_.Exception.Message
}

# === KB Search (keyword) Field Verification ===
Write-Host "`n--- Keyword Search Field Verification ---" -ForegroundColor Yellow
$r = Invoke-RestMethod -Uri "$baseUrl/api/kb/search?query=paper&top_k=5" -TimeoutSec 10
Test-Name "Keyword search has hits" ($r.hits.Count -gt 0) "count: $($r.count)"
if ($r.hits.Count -gt 0) {
    $first = $r.hits[0]
    Test-Name "Keyword hit has kbName" ($null -ne $first.kbName) "value: $($first.kbName)"
    Test-Name "Keyword hit has docName" ($null -ne $first.docName) "value: $($first.docName)"
    Test-Name "Keyword hit has path" ($null -ne $first.path) "value: $($first.path)"
    Test-Name "Keyword hit has score" ($null -ne $first.score) "value: $($first.score)"
}

Write-Host "`n=== Results: $pass passed, $fail failed ===" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
