up:
	docker compose up -d --build

down:
	docker compose down -v

seed:
	docker compose exec api python scripts/bootstrap_all.py

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -q
