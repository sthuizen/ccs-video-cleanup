# Application rights, dependencies and private archive

This repository is private and is intended for the owner's use and authorized collaborators. No new open-source licence or blanket public redistribution permission has been assigned to the application. Access to the repository is not a grant of rights over church branding, recordings or all included third-party components. Obtain an explicit licence decision from the relevant rights holders before publishing the application source.

Version 1.1 reduces bundled dependencies: the installer contains application source, setup scripts and the public-domain World English Bible Protestant text. APT supplies standard system components; the user separately downloads specialist packages/models under upstream terms. See [the component and notice guide](packaging/THIRD_PARTY.md) and [Bible provenance](assets/SOURCE.md). Separating downloads does not waive upstream terms or constitute a complete transitive legal audit.

The 1.0 installer is preserved privately to satisfy the historical archive requirement. Its bundled-runtime redistribution review is unfinished. In particular, exact FFmpeg/native-library corresponding-source and licence-notice obligations, model notices and permission to redistribute the church logo were not established. Do not treat the archive as a cleared public binary release. The logo is absent from the tracked source and the 1.1 installer; an operator may import a logo they are authorized to use locally.

Do not change this repository to public or redistribute the legacy bundle until source/branding permissions and applicable dependency obligations have been resolved. No service recordings, transcripts, cookies or private user environments are included in Git. Recordings may carry separate speaker/music rights; the app never publishes them automatically.

## Windows 1.2.0 church edition

At the owner's explicit request, the Windows installer includes the supplied church logo for use by Christ Church Southampton. This permission is scoped to that church use; the logo remains excluded from Git and unrelated public redistribution is not authorized.

The Windows installer bundles application source, Bible text, embedded CPython and a pip bootstrap wheel. CPython's licence and the pip wheel's licence remain included. The NSIS installer notice is included in `packaging/windows/NSIS-NOTICES.txt`. Setup separately downloads hash-pinned binary Python wheels, an immutable FFmpeg build, Deno and the local speech model. Package notices remain in their installed wheel metadata; FFmpeg documentation and model notices are retained under user data. Microsoft's Visual C++ installer is downloaded from Microsoft and publisher-signature checked rather than bundled. See the [Windows component and build guide](packaging/windows/README.md).

Separating downloads does not waive their licences. The application still has no blanket public-distribution licence or complete transitive legal clearance. Windows evaluation ISOs, test account credentials and virtual disks are private test infrastructure and are never release attachments.
