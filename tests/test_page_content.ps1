# Frontend Page Content Verification
Write-Host "=== Frontend Page Content Verification ===" -ForegroundColor Cyan

$baseUrl = "http://localhost:6789"
$pass = 0
$fail = 0

function Check-Content($name, $url, $patterns) {
    try {
        $html = (Invoke-WebRequest -Uri $url -TimeoutSec 30 -UseBasicParsing).Content

        $allFound = $true
        foreach ($p in $patterns) {
            if ($html -notmatch $p) {
                Write-Host "  Missing pattern: $p" -ForegroundColor Yellow
                $allFound = $false
            }
        }

        if ($allFound) {
            Write-Host "[PASS] $name" -ForegroundColor Green
            $script:pass++
        } else {
            Write-Host "[FAIL] $name - Missing expected content" -ForegroundColor Red
            $script:fail++
        }
    } catch {
        Write-Host "[FAIL] $name - $($_.Exception.Message)" -ForegroundColor Red
        $script:fail++
    }
}

# Test 1: Home page should have hero section and features
Check-Content "Home Page Content" "$baseUrl/" @(
    "RAG",
    "knowledge",
    "feature"
)

# Test 2: Search page should have search mode selector and search input
Check-Content "Search Page - Mode Selector" "$baseUrl/knowledge-search" @(
    "two-stage",
    "vector",
    "keyword"
)

# Test 3: Graph page should have SVG canvas and toolbar
Check-Content "Graph Page - Canvas & Toolbar" "$baseUrl/knowledge-graph" @(
    "svg",
    "graph",
    "knowledge"
)

# Test 4: File system page should have tree structure
Check-Content "File System Page" "$baseUrl/file-system" @(
    "file",
    "folder"
)

# Test 5: Knowledge base page should have KB management
Check-Content "Knowledge Base Page" "$baseUrl/knowledge-base" @(
    "knowledge",
    "base"
)

# Test 6: About page
Check-Content "About Page" "$baseUrl/about" @(
    "about"
)

Write-Host ""
Write-Host "=== Results: $pass passed, $fail failed ===" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
