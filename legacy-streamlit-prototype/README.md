# Legacy Streamlit Prototype

Superseded early prototype (Streamlit + SQLite). Kept for reference only —
it is **not** counted toward Phase 1 (or any phase) completion. The
current, actively developed application lives in [`backend/`](../backend)
(FastAPI + PostgreSQL) and [`frontend/`](../frontend) (React + Tailwind),
per [`docs/ROADMAP.md`](../docs/ROADMAP.md).

To run this prototype anyway:

```bash
cd legacy-streamlit-prototype
python -m venv venv
venv\Scripts\activate   # or `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
streamlit run app.py
```
