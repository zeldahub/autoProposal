# Lon — BE (FastAPI)

## 실행

```powershell
cd D:\github\autoProposal\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
uvicorn app.main:app --reload --port 8080
```

- 헬스: http://localhost:8080/healthz
- 문서: http://localhost:8080/docs

## 구조

```
app/
├── main.py
├── core/      config / db_maria / db_mongo / security / errors
├── routers/   auth / projects / files / llm / generate / categories / admin
└── services/
    ├── llm/   base / openai / gemini / anthropic
    ├── pptx_builder.py
    └── xlsx_builder.py
```
