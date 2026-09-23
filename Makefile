COMPOSE ?= docker compose
CURL ?= curl
SERVICES ?=
SERVICE ?=

.DEFAULT_GOAL := help

.PHONY: help config pull up down restart ps logs health docs-check check db-shell shell urls seed seed-verify gui

help: ## Muestra los objetivos disponibles.
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z0-9_-]+:.*##/ {printf "%-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

config: ## Valida la configuración de Docker Compose.
	$(COMPOSE) config --quiet

pull: ## Descarga las imágenes necesarias.
	$(COMPOSE) pull

up: ## Inicia el stack en segundo plano.
	$(COMPOSE) up -d --remove-orphans

down: ## Detiene el stack y preserva los volúmenes.
	$(COMPOSE) down --remove-orphans

restart: ## Reinicia el stack y preserva los volúmenes.
	$(MAKE) down
	$(MAKE) up

ps: ## Muestra el estado de los servicios.
	$(COMPOSE) ps --all

logs: ## Sigue los registros; use SERVICES=<servicio> para filtrar.
	$(COMPOSE) logs --follow --tail=100 $(SERVICES)

health: ## Comprueba bases y endpoints publicados.
	@set -eu; \
	printf '%s\n' 'Comprobando PostgreSQL...'; \
	$(COMPOSE) exec -T postgres-source pg_isready -U postgres; \
	printf '%s\n' 'Comprobando MinIO...'; \
	$(CURL) --max-time 15 -fsS -o /dev/null http://localhost:9000/minio/health/live; \
	printf '%s\n' 'Comprobando Dremio...'; \
	$(CURL) --max-time 15 -fsS -o /dev/null http://localhost:9047/; \
	printf '%s\n' 'Comprobando OpenSearch...'; \
	$(CURL) --max-time 15 -fsS -o /dev/null http://localhost:9200/_cluster/health; \
	printf '%s\n' 'Comprobando Langflow...'; \
	$(CURL) --max-time 15 -fsS -o /dev/null http://localhost:7860/health; \
	printf '%s\n' 'Comprobando OpenMetadata...'; \
	$(CURL) --max-time 15 -fsS -o /dev/null http://localhost:8585/; \
	printf '%s\n' 'Todos los checks HTTP respondieron correctamente.'

docs-check: ## Comprueba que existe el glosario canónico.
	@test -s CONTEXT.md || (echo 'Falta CONTEXT.md.' >&2; exit 1)
	@grep -q '^# ' CONTEXT.md || (echo 'El glosario no tiene título.' >&2; exit 1)

check: config docs-check health ## Valida documentación, configuración y disponibilidad del stack.

db-shell: ## Abre psql contra la base moodle_db.
	$(COMPOSE) exec postgres-source psql -U postgres -d moodle_db

seed: ## Carga datos sintéticos Moodle y ERP en las fuentes transaccionales.
	$(COMPOSE) run --rm seed-postgres
	$(COMPOSE) up -d --wait mssql-source
	$(COMPOSE) exec -T mssql-source /opt/mssql-tools18/bin/sqlcmd -C -b -S localhost -U sa -P 'MssqlPassword123!' -i /seeds/erpnext.sql

seed-verify: ## Muestra los recuentos principales de los datos sintéticos.
	$(COMPOSE) exec -T postgres-source psql -U postgres -d moodle_db -c "SELECT 'users' AS entity, count(*) FROM moodle.users UNION ALL SELECT 'courses', count(*) FROM moodle.courses UNION ALL SELECT 'submissions', count(*) FROM moodle.assignment_submissions;"
	$(COMPOSE) exec -T mssql-source /opt/mssql-tools18/bin/sqlcmd -C -b -S localhost -U sa -P 'MssqlPassword123!' -d erpnext_db -Q "SELECT 'customers' AS entity, count(*) AS total FROM erp.customer UNION ALL SELECT 'invoices', count(*) FROM erp.sales_invoice UNION ALL SELECT 'purchase_orders', count(*) FROM erp.purchase_order;"

gui: ## Inicia la interfaz DbGate para explorar las fuentes de solo lectura.
	$(COMPOSE) up -d --wait dbgate

shell: ## Abre una shell; requiere SERVICE=<servicio>.
	@test -n "$(SERVICE)" || (echo 'Uso: make shell SERVICE=<servicio>' >&2; exit 2)
	$(COMPOSE) exec $(SERVICE) /bin/sh

urls: ## Muestra las interfaces web locales.
	@printf '%s\n' \
	  'MinIO:        http://localhost:9001' \
	  'Dremio:       http://localhost:9047' \
	  'OpenSearch:   http://localhost:9200' \
	  'Langflow:     http://localhost:7860' \
	  'OpenMetadata: http://localhost:8585' \
	  'DbGate:       http://localhost:3000'
