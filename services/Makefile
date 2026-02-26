SERVICE_ARG := $(or $(service),$(word 2,$(MAKECMDGOALS)))

lint:
	ruff check services/

format:
	ruff format services/

typecheck:
	mypy services/

test:
	pytest -v

check: lint typecheck test

up:
	docker compose up --build

down:
	docker compose down

clean:
	docker compose down --rmi all --volumes --remove-orphans

kill:
	@if [ -z "$(SERVICE_ARG)" ]; then echo "Usage: make kill <service-name>"; exit 1; fi
	docker compose kill $(SERVICE_ARG)

start:
	@if [ -z "$(SERVICE_ARG)" ]; then echo "Usage: make start <service-name>"; exit 1; fi
	docker compose up -d $(SERVICE_ARG)

killg:
	docker compose kill gateway

kill-%:
	@if ! echo "$*" | grep -Eq '^[0-9]+$$'; then echo "Usage: make kill-<N> (e.g. kill-1)"; exit 1; fi
	docker compose kill storage-$*

ifneq (,$(filter start kill,$(firstword $(MAKECMDGOALS))))
%:
	@:
endif
