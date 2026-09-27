# Common targets for the catedra repo template. Every target is safe to run
# from a student laptop; nothing here touches a cloud account.

.PHONY: test test-app test-model test-pow test-contracts \
        build build-app build-model build-pow \
        compose-up compose-down compose-anvil-up compose-anvil-down \
        tf-fmt tf-validate helm-lint helm-template loadtest clean

PYTHON := 3.12

test: test-app test-model test-pow test-contracts

test-app:
	cd app && uv run --python $(PYTHON) --with-requirements requirements.txt --with pytest --with httpx pytest -q

test-model:
	cd model && uv run --python $(PYTHON) --with-requirements requirements.txt --with pytest --with httpx pytest -q

test-pow:
	cd pow && uv run --python $(PYTHON) --with-requirements requirements.txt --with pytest --with httpx pytest -q

test-contracts:
	cd contracts && forge test -vv

build: build-app build-model build-pow

build-app:
	docker build -t servicio-patron:local ./app

build-model:
	docker build -t model:local ./model

build-pow:
	docker build -t pow:local ./pow

compose-up:
	docker compose -f compose/docker-compose.yml up -d --build

compose-down:
	docker compose -f compose/docker-compose.yml down -v

compose-anvil-up:
	docker compose -f compose/docker-compose.anvil.yml up -d --build

compose-anvil-down:
	docker compose -f compose/docker-compose.anvil.yml down -v

tf-fmt:
	cd terraform && terraform fmt -recursive -check

tf-validate:
	cd terraform/envs/dev && terraform init -backend=false && terraform validate
	cd terraform/envs/prod && terraform init -backend=false && terraform validate

helm-lint:
	for c in servicio-patron anvil pow model; do helm lint helm/charts/$$c; done

helm-template:
	for c in servicio-patron anvil pow model; do helm template test helm/charts/$$c > /dev/null; done

loadtest:
	k6 run loadtest/k6-script.js

clean:
	find . -name "__pycache__" -o -name ".pytest_cache" -o -name ".ruff_cache" | xargs rm -rf
	rm -rf terraform/envs/dev/.terraform terraform/envs/prod/.terraform
