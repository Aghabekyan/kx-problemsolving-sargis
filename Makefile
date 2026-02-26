lint:
	ruff check services/

format:
	ruff format services/

typecheck:
	mypy services/

test:
	pytest -v

check: lint typecheck test
