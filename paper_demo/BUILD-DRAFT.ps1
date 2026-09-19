[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$tex = Join-Path $PSScriptRoot 'tex'
Push-Location -LiteralPath $tex
try {
    & pdflatex -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'Initial LaTeX pass failed.' }
    & bibtex main
    if ($LASTEXITCODE -ne 0) { throw 'BibTeX failed.' }
    for ($i = 1; $i -le 3; $i++) {
        & pdflatex -interaction=nonstopmode -halt-on-error main.tex
        if ($LASTEXITCODE -ne 0) { throw "LaTeX pass $i failed." }
    }
    Write-Host "Built $(Join-Path $tex 'main.pdf')"
    Write-Host 'Recheck body-page count after replacing author metadata or adding acknowledgments.'
} finally {
    Pop-Location
}
