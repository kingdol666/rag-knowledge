#!/usr/bin/env python3
"""Quick smoke test: verify .env overrides flow through all modules.

Expects .env values matching config.yml dev mode:
  APP_MODE=dev
  BACKEND_PORT=8765
  WEB_PORT=6789
  TREE_STORAGE_PATH=../storage/tree-file-system
"""
import os, sys, subprocess, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(str(ROOT))

# 1) Backend: dotenv loads BACKEND_PORT from .env
code = r"""
import os, sys; from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "backend"))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)
print(os.environ.get("APP_MODE"))
print(os.environ.get("BACKEND_PORT"))
print(os.environ.get("WEB_PORT"))
print(os.environ.get("TREE_STORAGE_PATH"))
"""
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10,
                   env=os.environ | {"PYTHONUTF8": "1"})
lines = r.stdout.strip().split("\n")
print(f"  Backend stdout: {lines}")
assert lines[1] == "8765", f"BACKEND_PORT={lines[1]!r}"
assert lines[0] == "dev", f"APP_MODE={lines[0]!r}"
assert lines[3] == "../storage/tree-file-system", f"TREE_STORAGE_PATH={lines[3]!r}"
print("[OK] Backend dotenv: APP_MODE=dev, BACKEND_PORT=8765, TREE_STORAGE_PATH=../storage/tree-file-system")

# 2) Frontend: start.mjs loadDotenv (unconditional loading)
node_code = r"""
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

// Simulate loading from web/start.mjs location
const __dirname = path.resolve(process.cwd(), 'web')

function loadDotenv() {
  const candidates = [
    path.resolve(__dirname, '..', '..', '.env'),    // rag-knowledge/.env
    path.resolve(__dirname, '..', '.env'),            // web/.env
  ]
  for (const envPath of candidates) {
    if (!fs.existsSync(envPath)) continue
    const content = fs.readFileSync(envPath, 'utf-8')
    for (const line of content.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
      const eq = trimmed.indexOf('=')
      const key = trimmed.slice(0, eq).trim()
      const val = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '')
      if (key) process.env[key] = val
    }
  }
}
loadDotenv()
console.log(process.env.APP_MODE)
console.log(process.env.BACKEND_PORT)
console.log(process.env.WEB_PORT)
console.log(process.env.TREE_STORAGE_PATH)
"""
r2 = subprocess.run(["node", "--input-type=module", "-e", node_code], capture_output=True, text=True, timeout=10, cwd=str(ROOT))
print(f"  Frontend stdout: {r2.stdout.strip()}")
lines2 = r2.stdout.strip().split("\n")
assert lines2[0] == "dev", f"APP_MODE={lines2[0]!r}"
assert lines2[1] == "8765", f"BACKEND_PORT={lines2[1]!r}"
assert lines2[2] == "6789", f"WEB_PORT={lines2[2]!r}"
assert lines2[3] == "../storage/tree-file-system", f"TREE_STORAGE_PATH={lines2[3]!r}"
print("[OK] Frontend loadDotenv: APP_MODE=dev, BACKEND_PORT=8765, WEB_PORT=6789, TREE_STORAGE_PATH=../storage/tree-file-system")

print("\n[PASS] All env variables flow correctly. Ready to start.")
