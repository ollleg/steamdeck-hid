# Publishing to PyPI

## Prerequisites

1. **Create a PyPI account** (if you don't have one):
   - Go to https://pypi.org/account/register/
   - Create an account

2. **Create an API token** (recommended):
   - Go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Give it a name (e.g., "steamdeck-hid-publish")
   - Scope: Select "Entire account" or limit to this project
   - Copy the token (it starts with `pypi-`). You won't see it again!

## Publishing Steps

### Option 1: Test on TestPyPI First (Recommended)

1. **Create a TestPyPI account** (separate from PyPI):
   - Go to https://test.pypi.org/account/register/
   - Create an account (can use same username/password as PyPI)

2. **Upload to TestPyPI**:
   ```bash
   python3 -m twine upload --repository testpypi dist/*
   ```
   - When prompted, use `__token__` as username
   - Use your TestPyPI API token as password (create one at https://test.pypi.org/manage/account/token/)

3. **Test the installation**:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ steamdeck-hid
   ```

### Option 2: Publish to Production PyPI

1. **Upload to PyPI**:
   ```bash
   python3 -m twine upload dist/*
   ```
   - When prompted, use `__token__` as username
   - Use your PyPI API token as password

2. **Verify the upload**:
   - Check https://pypi.org/project/steamdeck-hid/
   - Test installation: `pip install steamdeck-hid`

## Using API Tokens

When using API tokens with twine:
- **Username**: `__token__` (literally, with underscores)
- **Password**: Your API token (starts with `pypi-`)

You can also configure credentials in `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-token-here
```

## Updating the Package

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "0.2.4"  # Increment version number
   ```

2. **Build again**:
   ```bash
   python3 -m build
   ```

3. **Upload**:
   ```bash
   python3 -m twine upload dist/*
   ```

## Clean Up Build Artifacts

After publishing, you can remove the `dist/` directory:
```bash
rm -rf dist/ *.egg-info
```

## Troubleshooting

- **"File already exists"**: Version number already published. Increment version in `pyproject.toml`
- **"Invalid credentials"**: Check that you're using `__token__` as username and the correct API token
- **"Package name already taken"**: The name `steamdeck-hid` is already registered. You'll need to use a different name or contact the owner

