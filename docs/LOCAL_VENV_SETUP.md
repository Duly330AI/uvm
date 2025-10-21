# Local Python Environment Setup (.venv)

## Purpose

The local `.venv` is **only for VS Code IntelliSense and Pylance**. Actual development runs in Docker containers.

## Why is this needed?

- Pylance/VS Code needs local Python packages for type-hints and IntelliSense
- Docker container has all dependencies, but VS Code can't access them directly
- Without local dependencies: 2000+ "missing import" errors in Problems Panel

## Setup (Already Done)

```powershell
# Create venv
python -m venv .venv

# Activate venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\app\requirements.txt
pip install pytest==8.2.1 pytest-django==4.9.0 pytest-cov==6.0.0
```

## Installed Packages

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 5.1.13 | Web framework |
| djangorestframework | 3.15.2 | REST API |
| celery | 5.4.0 | Task queue |
| psycopg | 3.2.3 | PostgreSQL driver |
| redis | 5.0.8 | Cache/Celery broker |
| pytest | 8.2.1 | Testing |
| pytest-django | 4.9.0 | Django test support |
| pytest-cov | 6.0.0 | Coverage |

...and all other dependencies from `requirements.txt`

## Configuration Files

### `.vscode/settings.json`
- `python.defaultInterpreterPath`: Points to `.venv/Scripts/python.exe`
- `python.analysis.typeCheckingMode`: "basic"
- `python.analysis.useLibraryCodeForTypes`: true

### `pyrightconfig.json`
- `reportMissingImports`: "warning"
- `reportMissingModuleSource`: "warning"
- `reportAttributeAccessIssue`: "information"
- Ignores: migrations, __pycache__, .venv

## Important Notes

⚠️ **DO NOT run code in local .venv!** Always use Docker:
```bash
# ✅ Correct (in Docker)
docker compose exec web python manage.py runserver

# ❌ Wrong (local)
python manage.py runserver  # Missing database, Redis, etc.
```

⚠️ **DO NOT commit .venv/** - It's in `.gitignore`

✅ **DO commit** `pyrightconfig.json` - Team-wide Pylance config

## Updating Dependencies

When `requirements.txt` changes:
```powershell
.\.venv\Scripts\pip.exe install -r backend\app\requirements.txt --upgrade
```

## Troubleshooting

### Still seeing "missing import" errors?
1. **Restart VS Code** (Reload Window: Ctrl+Shift+P → "Reload Window")
2. Check Python interpreter: Bottom-left status bar should show `.venv`
3. Verify packages: `.\.venv\Scripts\pip.exe list`

### Pylance using wrong interpreter?
1. Ctrl+Shift+P → "Python: Select Interpreter"
2. Choose: `.\\.venv\\Scripts\\python.exe`

### Problems Panel still full?
1. Check `pyrightconfig.json` exists in workspace root
2. Verify `.vscode/settings.json` has correct paths
3. Delete `.vscode/` cache: Close VS Code, delete `.vscode/`, reopen

## Size

`.venv` folder: ~500 MB (all Python packages)

## Alternative: Dev Containers

For zero-config setup, use VS Code Dev Containers extension:
- Opens VS Code **inside** Docker container
- No local .venv needed
- All dependencies automatically available

(Not currently configured in this project)
