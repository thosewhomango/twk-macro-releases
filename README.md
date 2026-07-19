# TWK Macro Releases

Public distribution repository for independently versioned TWK Macro Hub components.

This repository contains update catalogs, validation rules, release notes, and compiled GitHub Release assets. Macro source code and user data do not belong here.

## Components

Each component has its own semantic version, package, manifest, release tag, backup, and rollback path.

Examples:

- `hub-v0.61.0`
- `updater-v1.0.0`
- `utdx-v0.60.12`
- `als-v0.18.2`

One macro release must not modify files owned by another component.

## Repository layout

```text
updates/
  stable/catalog.json
  beta/catalog.json
schema/
  catalog.schema.json
scripts/
  validate_catalog.py
.github/workflows/
  validate-catalog.yml
```

Compiled component ZIP files and their manifests are published as GitHub Release assets rather than committed to `main`.

## Catalog URLs

Initial raw catalog URLs:

- Stable: `https://raw.githubusercontent.com/thosewhomango/twk-macro-releases/main/updates/stable/catalog.json`
- Beta: `https://raw.githubusercontent.com/thosewhomango/twk-macro-releases/main/updates/beta/catalog.json`

GitHub Pages can replace these URLs later without changing the package format.

## Publishing order

1. Build one component from an explicit program-owned allowlist.
2. Generate and sign its internal component manifest.
3. Create the component ZIP and calculate its SHA-256.
4. Create a draft component-specific GitHub Release.
5. Upload the ZIP and manifest assets.
6. Verify uploaded asset names, sizes, and hashes.
7. Publish the GitHub Release.
8. Update and sign the appropriate channel catalog last.

Publishing the catalog last prevents clients from discovering an incomplete release. Never replace an asset on an existing tag; publish a new component version instead.

## Validation

Run locally:

```powershell
python scripts/validate_catalog.py
```

GitHub Actions runs the same validation whenever catalog, schema, or validator files change.

The initial catalogs have no components and use a `null` signature. A non-empty catalog is rejected unless it has a signature value. Signature generation and client-side verification must be implemented before the first production update is advertised.

## Safety rules

- Do not commit private-server links, webhook URLs, settings, recordings, logs, screenshots, caches, source files, or development backups.
- Do not upload a ZIP made directly from a working macro directory.
- Use HTTPS package URLs and SHA-256 for every package.
- Treat release tags and assets as immutable.
- Update the catalog only after the corresponding Release is complete and verified.
