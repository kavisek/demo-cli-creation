.PHONY: sync run test lint format build install uninstall

# Install the project and dev tools into .venv
sync:
	uv sync

# Run the dev CLI from the project venv, e.g. make run ARGS="compute instances list"
run:
	uv run mycloud $(ARGS)

test:
	uv run pytest --cov=mycloud -q

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

build:
	uv build

# Install mycloud on your PATH as an isolated tool (re-run after changes)
install:
	uv tool install --force --reinstall .

uninstall:
	uv tool uninstall mycloud
