# Contributing to SecureDevIQ

Thank you for your interest in contributing to SecureDevIQ! We welcome bug fixes, feature improvements, and new vulnerability challenge content.

## Getting Started

1. **Fork and clone** the repository
2. **Create a feature branch**: `git checkout -b feature/my-improvement`
3. **Make your changes** and test thoroughly
4. **Submit a pull request** with a clear description

## Development Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

Run tests:
```bash
pytest tests/ -v
```

Run linting:
```bash
ruff check app/ tests/
```

### Frontend

```bash
cd frontend
pip install -r requirements.txt
reflex run
```

### Using Docker Compose

```bash
docker compose up --build
```

## Code Style

- **Backend**: Follow PEP 8; use `ruff` for linting (`ruff check app/`)
- **Frontend**: Reflex / Python conventions
- **Comments**: Only when WHY is non-obvious; code should be self-documenting
- **No breaking changes** to the public API without discussion

## Adding New Vulnerability Categories

To add a new vulnerability type (e.g., "Timing Attacks"):

1. **Add to the `VulnCategory` enum** in `backend/app/models/__init__.py`
2. **Update `CHALLENGE_GENERATION_SYSTEM_PROMPT`** in `backend/app/prompts/generation.py`
3. **Update the frontend category list** in `frontend/securedeviq/pages/challenge.py`
4. **Create a migration** (optional if schema unchanged):
   ```bash
   cd backend
   alembic revision --autogenerate -m "add timing_attacks category"
   alembic upgrade head
   ```
5. **Write test challenges** to verify the category works end-to-end

## Security

- **Never commit secrets** (API keys, passwords, tokens) — use `.env` and `.env.example`
- **Validate user input** at system boundaries (frontend→backend)
- **Use parameterized queries** (SQLAlchemy ORM does this automatically)
- **Report security issues privately** via email to the maintainer before disclosing publicly

For more details, see [SECURITY.md](SECURITY.md).

## Testing

- **Unit tests** go in `backend/tests/`
- **Use in-memory SQLite** for tests (no Postgres needed locally)
- **Mock the Anthropic client** — tests should not call the real API
- **Aim for >80% code coverage** on new code

## Pull Request Guidelines

- **Title**: Brief, present tense (e.g., "Add support for Rust code challenges")
- **Description**: Explain the *why* and *what*, not just the how
- **Tests**: Include tests for new functionality
- **CI**: All tests and linting must pass before merge
- **Docs**: Update README/docstrings if behavior changes

## Questions?

- Check existing issues for similar questions
- Open a discussion or issue for help
- Reference relevant sections of the code in your question

Thank you for contributing! 🚀
