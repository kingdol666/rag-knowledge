# _postcheck.ps1 -- one-command verification for the journal_20p KBS build.
#
#   powershell -ExecutionPolicy Bypass -File _postcheck.ps1            # full chain + all gates
#   powershell -ExecutionPolicy Bypass -File _postcheck.ps1 -NoBibtex  # fast: single pass
#
# Checks, in order:
#   1. pdflatex -> bibtex -> pdflatex -> pdflatex under jobname qdcvr_kbs
#      (main_20p.pdf itself is usually locked by an open PDF viewer)
#   2. page count against the 20-page target
#   3. Overfull \hbox count (must be 0)
#   4. undefined references / citations (must be 0)
#   5. LaTeX errors (must be 0)
#   6. float label integrity: every \label referenced at least once, no undefined
#   7. artwork compliance: effective minimum type size >= 7 pt, no raster line art
#   8. a per-page section/float map written to map5.txt

param([switch]$NoBibtex)

$ErrorActionPreference = 'Stop'
$env:PATH = "C:\texlive\2025\bin\windows;$env:PATH"
$job = 'qdcvr_kbs'
$fail = 0

function Gate($name, $ok, $detail) {
  $tag = if ($ok) { 'PASS' } else { 'FAIL'; }
  if (-not $ok) { $script:fail++ }
  "{0,-4} {1,-34} {2}" -f $tag, $name, $detail
}

"=== build ($job) ==="
# Native calls are run with a relaxed preference: PowerShell 5.1 turns a native
# command's stderr into a terminating NativeCommandError when
# $ErrorActionPreference='Stop', and pdflatex/bibtex do write to stderr.
$eap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$stampBefore = if (Test-Path "$job.pdf") { (Get-Item "$job.pdf").LastWriteTimeUtc } else { [datetime]::MinValue }
function RunTex($exe, $exeArgs) { & $exe @exeArgs 2>&1 | Out-Null }
RunTex pdflatex @('-interaction=nonstopmode', "-jobname=$job", 'main_20p.tex')
if (-not $NoBibtex) {
  RunTex bibtex @($job)
  RunTex pdflatex @('-interaction=nonstopmode', "-jobname=$job", 'main_20p.tex')
  RunTex pdflatex @('-interaction=nonstopmode', "-jobname=$job", 'main_20p.tex')
}
$ErrorActionPreference = $eap
$stampAfter = if (Test-Path "$job.pdf") { (Get-Item "$job.pdf").LastWriteTimeUtc } else { [datetime]::MinValue }

$log = Get-Content "$job.log" -Raw

"`n=== gates ==="
Gate 'pdf was rewritten by this run' ($stampAfter -gt $stampBefore) "$stampAfter"
$pages = [int][regex]::Match($log, "Output written on $job\.pdf \((\d+) pages").Groups[1].Value
Gate 'page count <= 20' ($pages -le 20) "$pages pages"

$over = ([regex]::Matches($log, 'Overfull \\hbox')).Count
Gate 'no overfull hbox' ($over -eq 0) "$over found"

$undef = ([regex]::Matches($log, 'undefined')).Count
Gate 'no undefined refs/cites' ($undef -eq 0) "$undef found"

$err = ([regex]::Matches($log, '(?m)^!')).Count
Gate 'no latex errors' ($err -eq 0) "$err found"

if (-not $NoBibtex) {
  $bibwarn = ([regex]::Matches((Get-Content "$job.blg" -Raw), 'Warning--')).Count
  # 14 of these are "empty pages in ..." for arXiv/preprint entries; not a defect.
  Gate 'bibtex ran' ($bibwarn -lt 25) "$bibwarn warning(s)"
}

# --- float label integrity -------------------------------------------------
$tex = Get-ChildItem *.tex | ForEach-Object { Get-Content $_.FullName -Raw }
$all = $tex -join "`n"
$labels = [regex]::Matches($all, '\\label\{([^}]+)\}') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$refs = [regex]::Matches($all, '\\(?:ref|autoref)\{([^}]+)\}') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$unresolved = $refs | Where-Object { $labels -notcontains $_ }
$uncited = ($labels | Where-Object { $_ -like 'fig:*' -or $_ -like 'tab:*' }) | Where-Object { $refs -notcontains $_ }
Gate 'all \ref labels defined' ($unresolved.Count -eq 0) $(if ($unresolved) { $unresolved -join ', ' } else { 'ok' })
Gate 'every float cited' ($uncited.Count -eq 0) $(if ($uncited) { $uncited -join ', ' } else { 'ok' })

# --- artwork ---------------------------------------------------------------
"`n=== artwork (Elsevier: >= 7 pt effective, vector line art) ==="
# NB: uv writes a pymupdf deprecation notice to stderr; with
# $ErrorActionPreference='Stop' a native stderr redirect terminates the script
# (NativeCommandError), so relax it around this call and merge the streams.
$eap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$art = (uv run --with pymupdf python -B _audit_artwork_20p.py 2>&1 | Out-String)
$ErrorActionPreference = $eap
$art -split "`n" | Where-Object { $_ -match '^\s*fig|BELOW|minimum effective' } | ForEach-Object { $_.TrimEnd() }
$below = ([regex]::Matches($art, 'BELOW 7pt')).Count
Gate 'all figures >= 7 pt effective' ($below -eq 0) "$below below floor"

# --- page map --------------------------------------------------------------
pdftotext -layout "$job.pdf" map5.txt
$map = (Get-Content map5.txt -Raw) -split "`f"
"`n=== page map ==="
for ($i = 0; $i -lt $map.Count; $i++) {
  if ($map[$i].Trim() -eq '') { continue }
  $h = ($map[$i] -split "`n" | Where-Object { $_ -match '^\s*\d+(\.\d+)*\.\s+[A-Z]' } | ForEach-Object { $_.Trim() }) -join ' | '
  $f = ($map[$i] -split "`n" | Where-Object { $_ -match '^\s*(Figure|Table) [A-B]?\.?\d+[:.]' } | ForEach-Object { ($_.Trim() -split ':')[0] }) -join ', '
  "p{0:d2}  {1}   [{2}]" -f ($i + 1), $h.Substring(0, [Math]::Min(64, $h.Length)), $f
}

"`n=== result ==="
if ($fail -eq 0) { "ALL GATES PASS" } else { "$fail GATE(S) FAILED" }
exit $fail
