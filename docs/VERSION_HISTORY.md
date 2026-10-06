# Available versions and archive provenance

[Home](../README.md) · [Artifact manifest](versions.json)

This archive was established on 6 October 2026. There was no pre-existing Git history in the workspace. It preserves the two available versioned installers and their source snapshots; it does not invent a commit history for earlier unversioned edits.

## 1.1.0 — recommended application-only package

- Source-only amd64 `.deb`, with the public-domain Bible asset.
- Standard Python/media dependencies installed through APT.
- Specialist AI/downloader/Deno dependencies and speech model installed separately by the normal user.
- No third-party binaries, model files or church logo embedded in the package.
- First-run checks, protected system-library versions, dependency inventory/notices and a successful setup marker.
- Text branding fallback and authorized optional logo import.
- Validated in Ubuntu 24.04 and Debian 13 isolated userspaces; see [the exact artifact record](validation/v1.1.0.json).

The `v1.1.0` tag records source and the expanded archive documentation. The preserved `.deb` was built before that documentation expansion; source archives may contain additional documentation. Its original bytes and validation checksum have been retained.

## 1.0.0 — legacy bundled prototype

The original installer bundled a Python environment, media/downloader tools, recognition models and the church logo. It is retained only as a private historical reference. It is large and its redistribution audit is unfinished: native-library/FFmpeg source and notice obligations and branding permissions were not fully established. It is not the recommended install or a cleared public release.

The `v1.0.0` snapshot recovers `ccs/`, Bible assets and the packaging builder/instructions directly from the original `.deb`. Supporting wrappers, requirements, setup script and tests are retained from the surviving workspace because their earlier standalone history was unavailable. The tag is a recovered snapshot, not a claim that every supporting file existed in exactly that form at original build time. The packaged Python application is the authoritative historical source; the original installer is the authoritative binary artifact. Rebuilding this snapshot is not guaranteed to reproduce that installer bit for bit.

## Original project installation

The original locally installed workflow remains documented in [LOCAL_INSTALL.md](LOCAL_INSTALL.md), and its wrappers/setup script remain in current source. It is an installation mode, not an invented third release. Jobs, models, downloaded tools and the church logo remain private local data, not source attachments.

## Future work

Use a new version number for each release with changed installer content. Preserve source tags, installer files, checksum sidecars and validation evidence together. `main` can continue changing without altering historical release files. The source repository is deliberately not marked read-only/archived because further work is expected.
