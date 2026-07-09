# API Integration Test Script
Write-Host "=== RAG Knowledge Platform API Tests ===" -ForegroundColor Cyan

$baseUrl = "http://localhost:6789"
$backendUrl = "http://localhost:8765"
$pass = 0
$fail = 0

function Test-Endpoint($name, $url, $method = "GET", $body = $null) {
    try {
        if ($method -eq "GET") {
            $r = Invoke-RestMethod -Uri $url -TimeoutSec 15
        } else {
            $json = $body | ConvertTo-Json -Depth 10
            $r = Invoke-RestMethod -Uri $url -Method $method -Body $json -ContentType "application/json" -TimeoutSec 30
        }
        Write-Host "[PASS] $name" -ForegroundColor Green
        $script:pass++
        return $r
    } catch {
        Write-Host "[FAIL] $name - $($_.Exception.Message)" -ForegroundColor Red
        $script:fail++
        return $null
    }
}

# 1. Backend health
$r = Test-Endpoint "Backend Health" "$backendUrl/api/v1/health"
if ($r) { Write-Host "  Status: $($r.status)" }

# 2. Frontend catalog (proxy)
$r = Test-Endpoint "KB Catalog (via proxy)" "$baseUrl/api/kb/catalog"
if ($r) { Write-Host "  KB count: $($r.knowledgeBases.Count)" }

# 3. Vector search
$r = Test-Endpoint "Vector Search" "$baseUrl/api/search/vector" "POST" @{
    query = "RAG retrieval augmented generation"
    top_k = 5
    kb_id = ""
    balance_kbs = $true
}
if ($r) { Write-Host "  Results: $($r.count)" }

# 4. Two-stage search
$r = Test-Endpoint "Two-Stage Search" "$baseUrl/api/search/two-stage" "POST" @{
    query = "attention mechanism transformer"
    stage1_top_k = 20
    stage2_top_k = 5
    kb_id = ""
    balance_kbs = $true
}
if ($r) {
    Write-Host "  Stage1 candidates: $($r.stage1.candidate_count)"
    Write-Host "  Stage2 results: $($r.stage2.results.Count)"
    Write-Host "  Total results: $($r.total_results)"
    if ($r.stage2.results.Count -gt 0) {
        $first = $r.stage2.results[0]
        Write-Host "  First result: doc_path=$($first.doc_path), score=$($first.score)"
    }
}

# 5. Graph health
$r = Test-Endpoint "Graph Health" "$baseUrl/api/graph/health"
if ($r) { Write-Host "  Health: $($r.health | ConvertTo-Json -Compress)" }

# 6. Graph stats
$r = Test-Endpoint "Graph Stats" "$baseUrl/api/graph/stats"
if ($r) { Write-Host "  Stats: $($r.stats | ConvertTo-Json -Compress)" }

# 7. KB search (keyword)
$r = Test-Endpoint "Keyword Search" "$baseUrl/api/kb/search?query=attention&top_k=5"
if ($r) { Write-Host "  Hits: $($r.count)" }

# 8. KB tags
$r = Test-Endpoint "KB Tags" "$baseUrl/api/kb/tags"
if ($r) { Write-Host "  Tags count: $($r.tags.Count)" }

Write-Host ""
Write-Host "=== Results: $pass passed, $fail failed ===" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
