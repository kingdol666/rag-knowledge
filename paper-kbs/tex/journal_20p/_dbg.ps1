$tex = Get-ChildItem *.tex | ForEach-Object { Get-Content $_.FullName -Raw }
$all = $tex -join "`n"
$refs = [regex]::Matches($all, '\(?:ref|autoref)\{([^}]+)\}') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$labels = [regex]::Matches($all, '\label\{([^}]+)\}') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
Write-Output ("refs has fig:levels  : " + ($refs -contains 'fig:levels'))
Write-Output ("labels has fig:levels: " + ($labels -contains 'fig:levels'))
Write-Output ("n refs=" + $refs.Count + " n labels=" + $labels.Count)
$uncited = ($labels | Where-Object { $_ -like 'fig:*' -or $_ -like 'tab:*' }) | Where-Object { $refs -notcontains $_ }
Write-Output ("uncited: " + ($uncited -join ', '))
