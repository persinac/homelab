
APP_NAME:=homelab
PACKAGE_NAME:=homelab

# Helpers for local files discovery
TOP_LEVEL_SCRIPTS:=./run.py
CODE_DIRS:=${TOP_LEVEL_SCRIPTS} ./${PACKAGE_NAME} ./tests
CODE_FILES:=${TOP_LEVEL_SCRIPTS} $(shell find ./${PACKAGE_NAME} -name '*.py')

# Dinamically defining the image tag according to env vars
# `CIRCLE_BRANCH` will have the branch name during CircleCI builds
ifeq (${CIRCLE_BRANCH},)
	TAG=${APP_NAME}-${subst /,_,$(shell git rev-parse --abbrev-ref HEAD)}
else ifeq (${CIRCLE_BRANCH},production)
	TAG=${APP_NAME}-master
else
	TAG=${APP_NAME}-${subst /,_,${CIRCLE_BRANCH}}
endif

.PHONY: check-all check-commit check-format check-push clean env env-prune format image image-push test

#---------------------------------

check-all: check-commit check-push

check-commit:
	flake8 ${CODE_DIRS}
	isort ${CODE_DIRS} --check
	mypy ${CODE_FILES} --ignore-missing-imports
	black ${CODE_DIRS} --check
	sqlfluff lint ${CODE_DIRS}

check-format: format check-all

check-push:
	vulture ${CODE_DIRS}
	pydocstyle ${CODE_DIRS}
	bandit -r ./${PACKAGE_NAME} -q
	git ls-files -z | xargs -0 detect-secrets-hook --exclude-files "helm/*" --baseline .secrets.baseline

clean:
	find . -name "*.pyc" -type f -delete
	rm -rf .pytest_cache

env-windows:
	virtualenv .venv --python=3.11 && . .venv/Scripts/activate && poetry install

env-prune-windows:
	rmdir /s /q .venv

env:
	virtualenv .venv --python=3.11
	. .venv/Scripts/activate; poetry install;

env-prune:
	rm -r .venv

format:
	black ${CODE_DIRS}
	isort ${CODE_DIRS}
	sqlfluff fix ${CODE_DIRS}

image:
	docker build -t rockerbox/rockerbox-metrics:${TAG} .

image-push:
	docker image push rockerbox/rockerbox-metrics:${TAG}

test:
	python -m coverage run -m pytest --junitxml=tests-results/junit.xml
	coverage report --omit='.tox/*,*/test_*,*/test*/*' 2>&1 | tee tests-results/coverage.txt