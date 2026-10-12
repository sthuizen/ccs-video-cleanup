"""Linux login startup preference, stored in systemd's unit enablement."""
import subprocess
import json


def units(server):
    return (server, server.removesuffix('.service') + '-tray.service')


def enabled(server):
    return all(subprocess.run(
        ['systemctl', '--user', 'is-enabled', unit],
        capture_output=True, text=True, timeout=10,
    ).stdout.strip() == 'enabled' for unit in units(server))


def set_enabled(server, value, preference=None):
    # No --now: changing the login preference must not interrupt media work.
    subprocess.run(
        ['systemctl', '--user', 'enable' if value else 'disable', *units(server)],
        check=True, capture_output=True, text=True, timeout=15,
    )
    if preference is not None:
        preference.parent.mkdir(parents=True, exist_ok=True)
        temporary = preference.with_suffix('.tmp')
        temporary.write_text(json.dumps({'enabled': value}) + '\n')
        temporary.replace(preference)


def initialize(server, preference):
    """Clear legacy implicit startup once; thereafter preserve the user's choice."""
    if not preference.exists():
        set_enabled(server, False, preference)
