# Maintenance and recovery

[Home](../README.md) · [Installation and migration](../packaging/README.md)

## Storage and backup

The package defaults to `${XDG_DATA_HOME:-$HOME/.local/share}/ccs-video-cleanup`. The original app stores jobs in its project directory. The GitHub repository is an archive of application versions, **not a backup of your services or job data**.

Back up the complete `jobs/` directory while no job is writing to it. This retains sources, evidence, manual corrections and outputs. For local-file jobs, also back up the original media path recorded in `source-path.json`; it may be outside the job folder. Back up your authorized `assets/` directory separately. Model caches and `venv/` are replaceable downloads; `setup.json` alone is not an installation or a backup.

Example package backup after processing finishes:

```bash
backup_data="${XDG_DATA_HOME:-$HOME/.local/share}/ccs-video-cleanup"
tar -czf "$HOME/ccs-jobs-backup-$(date +%F).tar.gz" -C "$backup_data" jobs
```

Keep the backup on another disk as appropriate. Check that it can be listed/restored. Do not commit it to Git. Jobs can take many gigabytes; archive or remove a whole completed job only after you have checked and backed up the required media. Do not remove caches inside an active job.

## Routine updates

Use APT's normal update mechanism for system packages. YouTube support changes more frequently than the app:

```bash
ccs-video-cleanup setup --update-downloader
```

The update refreshes yt-dlp/Deno and their inventory without replacing speech models. The AI versions are deliberately selected by the application setup. Review and test changes rather than upgrading every pip package indiscriminately or replacing APT-provided NumPy/Pillow/SciPy/PyAV/OpenCV with wheels.

A future app `.deb` can be installed with `sudo apt install ./PACKAGE.deb`. Finish active processing and stop the packaged service before switching versions; run setup afterward. Record the installer checksum and retain the previous known-good installer. The historical 1.0 archive is not the recommended rollback target: it uses a different bundled runtime. Prefer a tested application-only version.

## Recovery on a new machine

1. Install the recommended release and complete normal-user setup.
2. Finish/stop any processing on the destination.
3. Restore job folders to the destination's `jobs/` directory and import an authorized logo with `setup --logo` if desired.
4. Restore referenced local media and update paths if they moved. Do not assume old absolute paths work on a new computer.
5. Reopen the app and inspect a restored job and its finished output. Re-render only when required.

For migration from the project installation, follow the [service-switching instructions](../packaging/README.md). The old project's jobs and model cache are left intact. Only one default web server can own port 8765.

## Keep the GitHub archive useful

`main` holds current source and documentation. Tags preserve published source snapshots; Releases preserve original installers and checksum files. Do not overwrite an existing release installer with a rebuild under the same filename. Bump the version, test it, update `docs/versions.json` and attach new validation evidence. Keep a clone plus downloaded release assets for an independent offline archive: `git clone` alone does not download installer attachments.

Grant repository access only to intended collaborators. [GitHub's visibility documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility) explains the consequences of making a repository public. Resolve source/branding rights and the legacy bundle's outstanding obligations before considering such a change; see [RIGHTS.md](../RIGHTS.md).
