# Working on this app

Read [the development guide](docs/DEVELOPMENT.md), [architecture](docs/ARCHITECTURE.md) and the workspace's [AGENTS.md](AGENTS.md) before changing the pipeline. Use an isolated data directory and synthetic media for tests. Preserve the stereo-phase safeguard, source/evidence caches, single-job lock and explicit handling of uncertain dates/titles/cut points.

Keep changes focused. Include the user-visible problem, resulting behavior, tests and any remaining limits in a pull request. Run `.venv/bin/python -m unittest discover -s tests -v` after substantive pipeline changes; run relevant Deno checks for interface logic. Never upload service jobs, cookies, credentials, downloaded toolchains or model caches. New dependencies need installation, licence and target-distro review.

This is a private working archive with no newly assigned open-source licence. Do not make it public or add an application licence without the owner's explicit decision. Use issues for reproducible problems and improvements; sanitize log excerpts before attaching them.
