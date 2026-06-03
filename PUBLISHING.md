# Publishing FlowGauge

FlowGauge publishes to [PyPI](https://pypi.org/) automatically via GitHub Actions
**Trusted Publishing** (OIDC) — there are **no API tokens or secrets** stored
anywhere. You push a version tag; the `Release` workflow builds and uploads.

Replace `OWNER` below with your GitHub username throughout.

## One-time setup

**1. Create the GitHub repo and push** (under your account):

```bash
git init && git add -A && git commit -m "FlowGauge v0.1.0"
git branch -M main
git remote add origin https://github.com/OWNER/flowgauge.git
git push -u origin main
```

**2. Add a Trusted Publisher on PyPI** (reserves the name for *only* this repo):

- Create a PyPI account at https://pypi.org and enable 2FA.
- Go to **Your account → Publishing → Add a new pending publisher** and enter:
  - **PyPI Project Name:** `flowgauge`
  - **Owner:** `OWNER`
  - **Repository name:** `flowgauge`
  - **Workflow name:** `release.yml`
  - **Environment name:** `pypi`
- A "pending" publisher reserves the name and authorizes this repo's workflow to
  create the project on first publish — no manual upload, no token.

**3. Create the matching GitHub environment:**

- Repo → **Settings → Environments → New environment** → name it `pypi`
  (matches `environment: pypi` in `.github/workflows/release.yml`).
- Optional: add required reviewers here to gate every release behind an approval.

## Cut a release

1. Bump `version` in `pyproject.toml` (e.g. `0.1.0` → `0.1.1`) and update `CHANGELOG.md`.
2. Commit, tag, and push — **the tag must match the version** (with a `v` prefix):

   ```bash
   git commit -am "Release v0.1.1"
   git tag v0.1.1
   git push origin main --tags
   ```

3. The **Release** workflow (Actions tab) builds the sdist + wheel and publishes
   to PyPI. The upload carries provenance linking back to the exact workflow run.
4. Verify: `uvx flowgauge@0.1.1` or visit `https://pypi.org/project/flowgauge/`.

## Notes

- Nothing to keep secret: Trusted Publishing means there are no credentials to
  commit or rotate.
- CI (`.github/workflows/ci.yml`) runs `ruff` + `pytest` on every push/PR; keep it
  green before tagging.
- To test the build locally without publishing: `python -m build` (or `uv build`),
  then `pip install dist/flowgauge-*.whl` in a clean venv.
