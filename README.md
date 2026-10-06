# Christ Church Video Cleanup

Prepare a full church-service recording into a sermon video: a five-second introduction followed by the selected Bible reading and sermon, with cleaned mono audio and optional camera stabilization. A local browser interface lets you review the date, passage, title and cut points before creating the finished video.

**Start with [version 1.1.0](https://github.com/thenailedone/ccs-video-cleanup/releases/tag/v1.1.0).** This private repository preserves the source and both available installers. The older 1.0.0 package is a legacy archive; use 1.1.0 for a new installation.

## Install on Ubuntu or Debian

Validated targets are **Ubuntu 24.04 LTS and Debian 13, amd64/x86-64**. Other distributions, release versions and ARM systems require separate validation. Ubuntu needs its `universe` repository enabled.

1. Sign in to GitHub with access to this repository. Open the [recommended release](https://github.com/thenailedone/ccs-video-cleanup/releases/tag/v1.1.0) and download the `.deb` and its `.deb.sha256` file into the same folder.
2. Open a terminal in that folder and run:

   ```bash
   sha256sum -c ccs-video-cleanup_1.1.0_amd64.deb.sha256
   sudo apt install ./ccs-video-cleanup_1.1.0_amd64.deb
   ccs-video-cleanup setup
   ```

3. Run setup as your normal desktop user. It downloads and checks the specialist tools and models; internet access is required. Allow several minutes and roughly 1–2 GB for those tools, plus system packages and video storage.
4. Open **Christ Church Video Cleanup** from your applications menu. The browser opens at `http://127.0.0.1:8765`.

The package uses APT for standard dependencies. Specialist AI packages, the YouTube downloader, Deno and the speech model are downloaded separately into your own user account. The church logo is excluded; an intro uses the church name as text unless you supply an authorized logo. See the [complete installation, migration and removal instructions](packaging/README.md).

## Prepare a sermon

1. Paste the completed service's YouTube URL and choose **Prepare sermon**.
2. Leave the computer running while it downloads and analyzes the recording. Closing the browser does not cancel processing.
3. If the app asks for details, play around the suggested cut points and supply the missing date, passage, title or timestamps. Unusual services can require manual correction; the interface is designed for that.
4. Choose **Save details and create video** when you are satisfied. Strong, unambiguous evidence can permit automatic rendering.
5. Watch the intro and check the beginning and end. Download **finished.mp4**, the full-quality output. Browser playback uses a separate preview.

There is no publishing or upload step. See the [operator guide](docs/USER_GUIDE.md) for review examples, file locations and CLI commands.

## What runs locally?

Speech recognition uses faster-whisper `small.en` on the CPU when usable English captions are unavailable. Slide reading uses RapidOCR. Passage matching and selection rules are conventional code; audio cleanup and stabilization use FFmpeg. **There are no cloud AI API calls, API keys or subscriptions.** Installation contacts dependency/model providers; YouTube processing contacts YouTube and may use locally read browser cookies. Cached local recordings and models support offline processing.

The app preserves the source and analysis evidence. It checks stereo phase before mixing so opposed channels do not cancel the voice. It asks for uncertain metadata instead of inventing an official title or treating an upload date as the service date. These checks improve reliability, but the operator still needs to check the result.

## Documentation

| You need to… | Read |
|---|---|
| Install, migrate, add a logo or uninstall | [Package instructions](packaging/README.md) |
| Prepare a service and correct uncertain information | [Operator guide](docs/USER_GUIDE.md) |
| Resolve setup, download, review or rendering problems | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Back up jobs, maintain tools or recover an installation | [Maintenance and recovery](docs/MAINTENANCE.md) |
| Understand the pipeline, caches and configuration | [Architecture](docs/ARCHITECTURE.md) |
| Change the app, test it or build a new package | [Development guide](docs/DEVELOPMENT.md) |
| Find earlier versions and understand archive provenance | [Version history](docs/VERSION_HISTORY.md) |
| Review dependency licences and branding restrictions | [Third-party components](packaging/THIRD_PARTY.md) and [rights](RIGHTS.md) |
| Maintain the original project-folder installation | [Original local installation](docs/LOCAL_INSTALL.md) |

## Versions and verification

| Version | Status | Packaging |
|---|---|---|
| [1.1.0](https://github.com/thenailedone/ccs-video-cleanup/releases/tag/v1.1.0) | Recommended | Small application-only `.deb`; APT libraries and user setup |
| [1.0.0](https://github.com/thenailedone/ccs-video-cleanup/releases/tag/v1.0.0) | Legacy private archive | Large bundled runtime; redistribution audit unfinished |

Version 1.1.0 passed all 19 Python tests, a synthetic media render, real OCR, offline speech-model loading, repeat setup and web/API checks in isolated Ubuntu 24.04 and Debian 13 userspaces. Those tests shared the host kernel; graphical desktop login/autostart was not exercised. The [validation record](docs/validation/v1.1.0.json) identifies the exact tested installer. [Artifact checksums and byte sizes](docs/versions.json) distinguish original installers from future rebuilds.

Source code and documentation are tracked in Git. Installer binaries are release attachments. Service recordings, transcripts, cookies, user environments and models are excluded from the source repository. This is a private application archive; no new open-source licence has been assigned. Read [RIGHTS.md](RIGHTS.md) before sharing or changing repository visibility.
