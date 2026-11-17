python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
python -m uvicorn transactions_app.main:app --host 0.0.0.0 --port 8002 --reload
