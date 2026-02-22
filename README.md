# Citation Scout MVP

This project includes:
- `backend/`: FastAPI service for uploading `.docx` files and extracting legal citations.
- `frontend/`: React (Vite) UI for uploading documents and displaying extracted citations.

## Backend Setup

1. Open a terminal in `backend/`.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

API endpoint:
- `POST /upload` with `multipart/form-data` field `file` (`.docx` only)

Response fields:
- `filename`
- `citation_count`
- `citations`: list of `{ "type": "case|statute|regulation", "text": "...", "status": "valid|review|invalid" }`

## Frontend Setup

1. Open a terminal in `frontend/`.
2. Install dependencies:

```bash
npm install
```

3. Optional: set backend URL in `.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

4. Start the UI:

```bash
npm run dev
```

Default frontend URL:
- `http://localhost:5173`

## Citation Extraction Logic

The backend parses `.docx` paragraph text using `python-docx` and applies regex patterns for:
- Case citations (e.g., `Smith v. Jones, 123 F.3d 456 (2001)`)
- Federal statutes (e.g., `42 U.S.C. § 1983`)
- Federal regulations (e.g., `21 C.F.R. § 314.50`)

Validation status is mocked deterministically (`valid`, `review`, `invalid`) from citation text.
