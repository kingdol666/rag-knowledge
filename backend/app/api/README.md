# API Documentation

## API Structure

```
app/
├── api/
│   ├── __init__.py              # API module initialization
│   ├── pdfparserapi.py          # Main API routes (Traditional + VLM)
│   └── README.md                # This file
├── models.py                    # Original models
├── models_vlm.py                # VLM-specific models
├── main.py                      # FastAPI application entry
└── services/
    ├── pdfparser.py             # Traditional parser service
    └── pdfparservt.py           # VT parser service (Traditional + VLM)
```

## API Endpoints

### Base URL
```
http://localhost:8000/api/v1
```

### Health & Configuration

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "model": "vlm-transformers",
  "api_connected": true
}
```

#### 2. Get Configuration (Traditional)
```http
GET /config
```

**Response:**
```json
{
  "backend": "vlm-transformers",
  "parse_method": "auto",
  "language": "en",
  "formula_enable": true,
  "table_enable": true,
  "device": "cpu",
  "start_page": 0,
  "end_page": null,
  "model_source": "huggingface",
  "is_configured": true
}
```

#### 3. Get VLM Configuration
```http
GET /vlm/config
```

**Response:**
```json
{
  "backend": "transformers",
  "model_path": null,
  "server_url": null,
  "formula_enable": true,
  "table_enable": true,
  "batch_size": 0
}
```

### Traditional PDF Conversion (Original)

#### 4. Convert PDF (Base64)
```http
POST /convert
```

**Request:**
```json
{
  "pdf_base64": "JVBERi0xLjQKJ...",
  "output_dir": "./output"
}
```

**Response:**
```json
{
  "success": true,
  "pages": ["# Markdown content..."],
  "total_pages": 1
}
```

#### 5. Convert PDF File (Upload)
```http
POST /convert/file
```

**Request (multipart/form-data):**
```
file: <PDF file>
output_dir: ./output (optional)
```

**Response:**
```json
{
  "success": true,
  "pages": ["# Markdown content..."],
  "total_pages": 1,
  "filename": "document.pdf"
}
```

#### 6. Convert PDF by Path
```http
POST /convert/path
```

**Query Parameters:**
- `pdf_path`: Absolute path to PDF file (required)
- `output_dir`: Output directory (optional)

**Response:**
```json
{
  "success": true,
  "pages": ["# Markdown content..."],
  "total_pages": 1
}
```

### VT Parser (Traditional Mode)

#### 7. Parse PDF - VT Mode
```http
POST /parse/vt
```

**Request:**
```json
{
  "pdf_path": "/path/to/document.pdf",
  "output_dir": "./output_vt",
  "use_ocr": true
}
```

**Response:**
```json
{
  "success": true,
  "markdown": "# Document content...",
  "markdown_path": "/path/to/output_vt/document.md",
  "image_dir": "/path/to/output_vt/images",
  "parse_method": "txt"
}
```

#### 8. Parse PDF File - VT Mode (Upload)
```http
POST /parse/file/vt
```

**Request (multipart/form-data):**
```
file: <PDF file>
output_dir: ./output_vt (optional)
use_ocr: true (optional, default: true)
```

**Response:**
```json
{
  "success": true,
  "markdown": "# Document content...",
  "markdown_path": "/path/to/output_vt/document.md",
  "image_dir": "/path/to/output_vt/images",
  "parse_method": "txt"
}
```

### VLM Parser (Vision Language Model)

#### 9. Parse PDF - VLM Mode
```http
POST /parse/vlm
```

**Request:**
```json
{
  "pdf_path": "/path/to/document.pdf",
  "output_dir": "./output_vlm",
  "vlm_backend": "transformers",
  "formula_enable": true,
  "table_enable": true,
  "batch_size": 0
}
```

**Response:**
```json
{
  "success": true,
  "markdown": "# Document content...",
  "markdown_path": "/path/to/output_vlm/document.md",
  "image_dir": "/path/to/output_vlm/images",
  "parse_method": "vlm",
  "vlm_backend": "transformers"
}
```

#### 10. Parse PDF File - VLM Mode (Upload)
```http
POST /parse/file/vlm
```

**Request (multipart/form-data):**
```
file: <PDF file>
output_dir: ./output_vlm (optional)
vlm_backend: transformers (optional)
formula_enable: true (optional)
table_enable: true (optional)
```

**Response:**
```json
{
  "success": true,
  "markdown": "# Document content...",
  "markdown_path": "/path/to/output_vlm/document.md",
  "image_dir": "/path/to/output_vlm/images",
  "parse_method": "vlm",
  "vlm_backend": "transformers"
}
```

## VLM Backend Options

### 1. transformers (Default)
- **Type**: HuggingFace Transformers
- **Requirements**: CPU/GPU
- **Best for**: Development, testing, general use
- **Model**: Qwen2-VL (auto-downloaded)

### 2. vllm-engine
- **Type**: vLLM inference engine
- **Requirements**: GPU (CUDA)
- **Best for**: High-performance production work
- **Model**: Qwen2-VL (auto-downloaded)

### 3. mlx-engine
- **Type**: MLX framework
- **Requirements**: Apple Silicon (M1/M2/M3), macOS 13.5+
- **Best for**: Mac users with Apple Silicon
- **Model**: Qwen2-VL (auto-downloaded)

### 4. http-client
- **Type**: HTTP client for remote server
- **Requirements**: Remote VLM server (OpenAI-compatible API)
- **Best for**: Offloading to remote GPU server
- **Model**: Depends on server
- **Requires**: `vlm_server_url` parameter

### 5. auto-engine
- **Type**: Auto-select best available
- **Requirements**: Automatically detects available engines
- **Best for**: Automatic optimization
- **Model**: Qwen2-VL (auto-downloaded)

## Environment Variables

### Traditional Parser
```bash
export MINERU_BACKEND="vlm-transformers"
export MINERU_PARSE_METHOD="auto"
export MINERU_LANGUAGE="en"
export MINERU_FORMULA_ENABLE="true"
export MINERU_TABLE_ENABLE="true"
export MINERU_DEVICE="cpu"
```

### VLM Parser
```bash
export MINERU_VLM_BACKEND="transformers"
export MINERU_VLM_MODEL_PATH="/path/to/model"  # Optional
export MINERU_VLM_SERVER_URL="http://127.0.0.1:8000"  # For http-client
export MINERU_VLM_FORMULA_ENABLE="true"
export MINERU_VLM_TABLE_ENABLE="true"
export MINERU_VLM_BATCH_SIZE="0"  # 0 = auto
```

## Usage Examples

### Python (requests)

```python
import requests

# Parse PDF with VT mode
response = requests.post(
    "http://localhost:8000/api/v1/parse/vt",
    json={
        "pdf_path": "/path/to/document.pdf",
        "output_dir": "./output_vt",
        "use_ocr": True
    }
)
result = response.json()
print(result["markdown"])

# Parse PDF with VLM mode
response = requests.post(
    "http://localhost:8000/api/v1/parse/vlm",
    json={
        "pdf_path": "/path/to/document.pdf",
        "output_dir": "./output_vlm",
        "vlm_backend": "transformers",
        "formula_enable": True,
        "table_enable": True
    }
)
result = response.json()
print(result["markdown"])
```

### cURL

```bash
# Parse PDF with VT mode
curl -X POST "http://localhost:8000/api/v1/parse/vt" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "/path/to/document.pdf",
    "output_dir": "./output_vt",
    "use_ocr": true
  }'

# Parse PDF with VLM mode
curl -X POST "http://localhost:8000/api/v1/parse/vlm" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_path": "/path/to/document.pdf",
    "output_dir": "./output_vlm",
    "vlm_backend": "transformers",
    "formula_enable": true,
    "table_enable": true
  }'
```

### File Upload (Python)

```python
import requests

# Upload and parse with VT mode
with open("document.pdf", "rb") as f:
    files = {"file": ("document.pdf", f, "application/pdf")}
    data = {
        "output_dir": "./output_vt",
        "use_ocr": "true"
    }
    response = requests.post(
        "http://localhost:8000/api/v1/parse/file/vt",
        files=files,
        data=data
    )
result = response.json()
print(result["markdown"])

# Upload and parse with VLM mode
with open("document.pdf", "rb") as f:
    files = {"file": ("document.pdf", f, "application/pdf")}
    data = {
        "output_dir": "./output_vlm",
        "vlm_backend": "transformers",
        "formula_enable": "true",
        "table_enable": "true"
    }
    response = requests.post(
        "http://localhost:8000/api/v1/parse/file/vlm",
        files=files,
        data=data
    )
result = response.json()
print(result["markdown"])
```

## Testing

Run the test suite:

```bash
# Make sure the server is running
python -m uvicorn app.main:app --reload

# Run tests (update TEST_PDF path in test_api_refactor.py first)
python test_api_refactor.py
```

## Interactive Documentation

Access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Migration Guide

### From Old Routes to New API

**Old:**
```python
from app.routes import router
```

**New:**
```python
from app.api import router
```

**Old endpoint:**
```
POST /api/v1/convert
```

**Still works (backward compatible)**

**New endpoints (VT & VLM):**
```
POST /api/v1/parse/vt
POST /api/v1/parse/vlm
POST /api/v1/parse/file/vt
POST /api/v1/parse/file/vlm
```

## Performance Comparison

| Mode | Speed | Accuracy | Resource Usage | Best For |
|------|-------|----------|----------------|----------|
| Traditional | Fast | Good | Low | Simple documents |
| VT Mode | Medium | Good | Low | Traditional OCR |
| **VLM Mode** | Medium | **Excellent** | Medium | Complex documents, formulas, tables |

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message describing the issue"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `404`: Not Found (file not found)
- `500`: Internal Server Error
- `503`: Service Unavailable (not configured)

## Best Practices

1. **Use VLM mode for complex documents** with formulas, tables, or scanned content
2. **Use VT mode for simple text PDFs** to save resources
3. **Use file upload endpoints** for client-side files
4. **Use path endpoints** for server-side files
5. **Check health endpoint** before processing
6. **Configure environment variables** appropriately for your use case

## Support

For issues or questions:
1. Check the health endpoint: `GET /health`
2. Check configuration: `GET /config` or `GET /vlm/config`
3. Review logs for error messages
4. Consult the interactive documentation at `/docs`
