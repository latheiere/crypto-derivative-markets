# Publishing

The repository targets the public source project at
`https://github.com/latheiere/crypto-derivative-markets` and the PyPI distribution
`crypto-derivative-markets`. Creating the remote project, pushing history, configuring trusted
publishing, and publishing releases remain deliberate maintainer operations.

## One-time setup

1. Create the named public source repository and push the reviewed initial history.
2. Verify the source, issue-tracker, changelog, and documentation links already declared in
   `pyproject.toml`.
3. Protect the default branch and require the quality workflow.
4. Create a `pypi` repository environment and require maintainer approval for deployment.
5. Configure a PyPI trusted publisher for `.github/workflows/release.yml` and that environment.
6. Confirm that the distribution name `crypto-derivative-markets` is available or owned by the
   project before creating a release.
7. Verify that repository Actions resolve the pinned immutable commits before enabling release tags.

No long-lived PyPI credential is required or accepted by the release workflow.

## Release

1. Move documented changes from `Unreleased` to the new version in `CHANGELOG.md`.
2. Set `__version__` in `src/cdm/__init__.py` and verify that it matches the intended tag.
3. Run `make verify` in a clean environment. The release workflow repeats this complete gate before
   making its artifacts available to the publish job.
4. Commit the release metadata and create an annotated `vMAJOR.MINOR.PATCH` tag.
5. Push the commit and tag. The release workflow rebuilds from the tag, verifies the artifacts,
   publishes through trusted identity, and records build artifacts.

Schema-major changes require an explicit compatibility and migration section before release.
