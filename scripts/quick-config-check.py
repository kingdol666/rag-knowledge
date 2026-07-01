"""Quick-shot config verification (no ports needed)."""
import os, sys, subprocess
ROOT = r"D:\codes\ClaudeGPT\rag_project\rag-knowledge"

tests = []

def t(name, code):
    r = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=10,
        cwd=ROOT
    )
    ok = r.returncode == 0
    print(f"  {'OK' if ok else 'FAIL'}: {name}" + (f"  ({r.stderr.strip()[:80]})" if not ok else ""))
    return ok

# 1) MCP config: dev
tests.append(t("MCP dev ports", """
import os, sys; sys.path.insert(0, r"ROOT/kb-mcp".replace('ROOT',r'ROOT'))
os.environ.update(APP_MODE='dev',BACKEND_PORT='8765',WEB_PORT='6789')
import config
assert '8765' in config.BACKEND_URL and '6789' in config.WEB_URL
""".replace('ROOT', ROOT)))

# 2) MCP config: prod
tests.append(t("MCP prod ports", """
import os, sys; sys.path.insert(0, r"ROOT/kb-mcp".replace('ROOT',r'ROOT'))
os.environ.update(APP_MODE='prod',BACKEND_PORT='8001',WEB_PORT='3000')
import config
assert '8001' in config.BACKEND_URL and '3000' in config.WEB_URL
""".replace('ROOT', ROOT)))

# 3) MCP custom ports
tests.append(t("MCP custom ports", """
import os, sys; sys.path.insert(0, r"ROOT/kb-mcp".replace('ROOT',r'ROOT'))
os.environ.update(APP_MODE='dev',BACKEND_PORT='9000',WEB_PORT='4000')
import config
assert '9000' in config.BACKEND_URL and '4000' in config.WEB_URL
""".replace('ROOT', ROOT)))

# 4) CORS
tests.append(t("CORS allow_all", """
import os; os.chdir(r"ROOT/backend".replace('ROOT',r'ROOT'))
os.environ['APP_MODE']='dev'
from app.config import config; config.reload()
assert config.cors_origins == ['*']
""".replace('ROOT', ROOT)))

# 5) NO_RELOAD
tests.append(t("NO_RELOAD=1 → prod", """
import os; os.chdir(r"ROOT/backend".replace('ROOT',r'ROOT'))
os.environ['APP_MODE']='dev'; os.environ['NO_RELOAD']='1'
from app.config import config; config.reload()
assert config.app_mode == 'prod'
""".replace('ROOT', ROOT)))

# 6) WEB_HOST
tests.append(t("WEB_HOST in URL", """
import os, sys; sys.path.insert(0, r"ROOT/kb-mcp".replace('ROOT',r'ROOT'))
os.environ.update(WEB_HOST='my-host',WEB_PORT='8888',APP_MODE='dev')
import config
assert 'my-host:8888' in config.WEB_URL
""".replace('ROOT', ROOT)))

# 7) MINERU
tests.append(t("MINERU_HOST+PORT", """
import os, sys; sys.path.insert(0, r"ROOT/kb-mcp".replace('ROOT',r'ROOT'))
os.environ.update(MINERU_HOST='10.0.0.1',MINERU_PORT='9999')
import config
assert '10.0.0.1:9999' in config.MINERU_URL
""".replace('ROOT', ROOT)))

# 8) MCP timeouts
tests.append(t("MCP timeouts", """
import os, sys; sys.path.insert(0, r"ROOT/kb-mcp".replace('ROOT',r'ROOT'))
os.environ.update(MCP_HTTP_TIMEOUT='60',MCP_PARSE_TIMEOUT='600')
import config
assert config.HTTP_TIMEOUT == 60 and config.PARSE_TIMEOUT == 600
""".replace('ROOT', ROOT)))

# 9) MinerU backend config
tests.append(t("MinerU config.yml", """
import os; os.chdir(r"ROOT/backend".replace('ROOT',r'ROOT'))
os.environ['APP_MODE']='dev'
from app.config import config; config.reload()
mc = config.mineru
assert mc.get('enabled') == True and mc.get('model_source') == 'modelscope'
""".replace('ROOT', ROOT)))

# 10) TREE_STORAGE_PATH via backend dotenv
tests.append(t("TREE_STORAGE_PATH", """
import os; from pathlib import Path; from dotenv import load_dotenv
os.chdir(r"ROOT/backend".replace('ROOT',r'ROOT'))
env_path = Path.cwd().parent / '.env'
load_dotenv(dotenv_path=str(env_path), override=True)
val = os.environ.get('TREE_STORAGE_PATH','')
assert 'tree-file-system' in val
""".replace('ROOT', ROOT)))

total = len(tests)
passed = sum(1 for t in tests if t)
print(f"\nResults: {passed}/{total} passed")
sys.exit(0 if passed == total else 1)
