# Project Location & Clone

> Referenced by knowledgebase-init Phase 2 when auto-detection is needed.

## Signature (all methods verify this)

A valid `<RAG_ROOT>` must contain all three: `config.yml` + (`ragctl` or `ragctl.bat`) + `backend/`.
## Method 0 — OMP Global MCP Config (primary for OMP installs)

If the user installed via `scripts/install_omp.cjs`, the project path is embedded in `~/.omp/agent/mcp.json`:

```bash
# Linux/macOS — extract kb-mcp --directory arg from OMP global config
OMP_MCP="$HOME/.omp/agent/mcp.json"
[ -f "$OMP_MCP" ] && python3 -c "
import json,sys
c=json.load(open('$OMP_MCP'))
args=c.get('mcpServers',{}).get('kb-mcp',{}).get('args',[])
i=args.index('--directory') if '--directory' in args else -1
print(args[i+1] if i>=0 else '',end='')
" 2>/dev/null | while read d; do [ -d "$d" ] && echo "$(dirname "$d")"; done
```

```powershell
# Windows
$ompMcp = "$env:USERPROFILE\.omp\agent\mcp.json"
if (Test-Path $ompMcp) {
  $cfg = Get-Content $ompMcp -Raw | ConvertFrom-Json
  $kbmcp = $cfg.mcpServers.'kb-mcp'
  if ($kbmcp) {
    $idx = [Array]::IndexOf($kbmcp.args, '--directory')
    if ($idx -ge 0) { $kbDir = $kbmcp.args[$idx + 1]; if (Test-Path $kbDir) { Split-Path $kbDir -Parent } }
  }
}
```

 ## Method 1 — Plugin Cache Scan (primary for plugin installs)

Claude Code clones plugins to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`.

```bash
# Linux/macOS
find "$HOME/.claude/plugins/cache" -maxdepth 4 -name "config.yml" -path "*rag-knowledge*" 2>/dev/null |
  while read f; do d=$(dirname "$f"); { [ -f "$d/ragctl" ] || [ -f "$d/ragctl.bat" ]; } && [ -d "$d/backend" ] && echo "$d"; done |
  sort -V | tail -1
```

```powershell
# Windows
Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache" -Recurse -Filter "config.yml" -Depth 4 -EA SilentlyContinue |
  Where-Object { $d=$_.DirectoryName; $_.FullName -match "rag-knowledge" -and ((Test-Path "$d\ragctl") -or (Test-Path "$d\ragctl.bat")) -and (Test-Path "$d\backend") } |
  Sort-Object FullName -Descending | Select-Object -First 1 | ForEach-Object { $_.DirectoryName }
```

## Method 2 — Git Root

```bash
git rev-parse --show-toplevel 2>/dev/null
```

## Method 3 — Walk Up from CWD (5 levels)

```bash
# Linux/macOS
d=$(pwd); for i in 1 2 3 4 5; do
  [ -f "$d/config.yml" ] && { [ -f "$d/ragctl" ] || [ -f "$d/ragctl.bat" ]; } && [ -d "$d/backend" ] && echo "$d" && break
  d=$(dirname "$d")
done
```

```powershell
# Windows
$d = Get-Location; foreach ($i in 1..5) {
  if ((Test-Path "$d\config.yml") -and ((Test-Path "$d\ragctl") -or (Test-Path "$d\ragctl.bat")) -and (Test-Path "$d\backend")) { Write-Output $d; break }
  $d = Split-Path $d -Parent
}
```

## Method 4 — Ask User (with clone option)

If methods 1-3 fail:

```
❓ 项目代码放在哪里？
  • 路径已存在且是本项目 → 直接使用
  • 路径不存在 → 自动 git clone
  • 路径存在但非本项目 → clone 到子目录
> 
```

**4b — path doesn't exist → auto clone:**
```bash
git clone https://github.com/kingdol666/rag-knowledge.git "<P>"
```

**China mirror fallbacks (if GitHub slow/blocked):**
```bash
git clone https://ghproxy.com/https://github.com/kingdol666/rag-knowledge.git "<P>"     # ghproxy
HTTPS_PROXY=http://127.0.0.1:7890 git clone https://github.com/kingdol666/rag-knowledge.git "<P>"  # user proxy
```

**4c — path exists but wrong signature → ask:** clone to `<P>/rag-knowledge` subdirectory, or re-enter path, or cancel.

## Confirmation Dialog

Always confirm with user after locating:

```
✅ 已定位 RAG Knowledge Platform
  📁 路径: <RAG_ROOT>  🏷️ 版本: <VERSION>  🔗 来源: <method>
  是否继续？[Y/n]:
```

## Optional Code Update (existing RAG_ROOT only, not fresh clone)

```
是否拉取最新代码？(git pull --ff-only) [Y/n，默认 Y]:
```

On dirty working tree → skip pull, warn user. **Never** `git reset --hard`.
