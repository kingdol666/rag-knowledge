@echo off
echo ============================================
echo  QDCVR Benchmark Backend Setup
echo  Using project venv: ..\..\backend\.venv
echo ============================================
echo.

set "VENV=..\..\backend\.venv\Scripts"

echo [1/3] Installing baseline dependencies...
"%VENV%\pip.exe" install rank-bm25 faiss-cpu sentence-transformers chromadb httpx fastapi uvicorn "numpy<2" -q
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip install failed. Try running manually:
    echo   %VENV%\pip.exe install rank-bm25 faiss-cpu sentence-transformers chromadb httpx fastapi uvicorn "numpy<2"
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

echo.
echo [2/3] Downloading BGE-M3 embedding model...
"%VENV%\python.exe" -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3'); print('BGE-M3: ready')"
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: BGE-M3 download may have failed. Will retry on first use.
)
echo [OK] Model cached.

echo.
echo [3/3] Starting benchmark backend on port 8800...
echo.
echo Open http://localhost:8800/api/health to verify
echo Baseline methods:
echo   [REAL-CODE] BM25, Dense(FAISS+BGE-M3), Hybrid, Dense+CrossEncoder
echo   [REAL-ALGO] CRAG, Self-RAG  
echo   [PROJECT]   QDCVR-Flat, QDCVR-Domain
echo.
"%VENV%\python.exe" main.py
pause
