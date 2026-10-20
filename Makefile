.PHONY: install dev stop build test smoke health
install:
	bash infra/scripts/install-native.sh
dev:
	bash infra/scripts/dev-start.sh
stop:
	bash infra/scripts/dev-stop.sh
build:
	npm run build
test:
	npm test
	PYTHONPATH=apps/quant-worker apps/quant-worker/.venv/bin/python -m unittest discover -s apps/quant-worker/tests -v
smoke:
	bash infra/scripts/smoke-test.sh
health:
	bash infra/scripts/healthcheck.sh
