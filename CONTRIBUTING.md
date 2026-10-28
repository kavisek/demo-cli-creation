# Contributing to mycloud

Thanks for your interest in contributing!

## Development setup

```sh
git clone https://github.com/kavisek/demo-cli-creation.git
cd demo-cli-creation
make sync        # uv sync
```

## Running tests and linters

```sh
make test        # pytest with coverage
make lint        # ruff check + ruff format --check
make format      # apply ruff fixes and formatting
```

## Making a change

1. Open an issue first for anything bigger than a small fix, so we can agree on the approach.
2. Fork the repo and create a branch: `git switch -c feat/my-change`.
3. Write commits in [Conventional Commits](https://www.conventionalcommits.org/) style (`feat:`, `fix:`, `docs:`, `chore:`).
4. Add or update tests, and make sure the checks above pass.
5. Open a pull request against `main` and fill in the template.

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.

## License

By contributing, you agree that your contributions are licensed under the project's [license](LICENSE).
