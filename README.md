# px0 for Herdr GPUI

[![CI](https://github.com/shreyanshrana/herdr-gpui-px0/actions/workflows/ci.yml/badge.svg)](https://github.com/shreyanshrana/herdr-gpui-px0/actions/workflows/ci.yml)

A Herdr plugin that requires the Herdr GPUI desktop app. It is installed and
managed through Herdr's plugin system and uses GPUI's browser CLI; it is not a
native GPUI/Rust extension and does not work with a daemon-only setup.

Open [px0](https://px0.ai/) beside the current terminal. Repeated invocations
focus the existing px0 tab for that terminal and checkout. Closing the browser
tab stops its server; the Close action closes only this plugin's px0 tabs in
the current workspace, not terminals or VS Code.

## Requirements

- **macOS**; other platforms and remote hosts are not supported yet.
- **Herdr 0.9.1+** for plugin installation, actions, and terminal context.
- **Herdr GPUI desktop app with browser CLI support**, running with an active
  workspace. Invoke plugin actions from that workspace, not a daemon-only setup.
- **Python 3.8+**, available as `python3` on the plugin action's `PATH`.
- **px0 0.1.19+**, installed separately and available as `px0` on `PATH`, at
  `~/.local/bin/px0`, or through the `PX0_BIN` environment variable.

No build step or additional Python packages are required. This is a local-only
Python integration; neither Herdr nor px0 is bundled. If the GPUI executable
cannot be found automatically, set `HERDR_GPUI_BIN` to its executable path.

## Install as a Herdr plugin

Install [px0](https://px0.ai/) separately first, then install this integration:

```sh
herdr plugin install shreyanshrana/herdr-gpui-px0
herdr plugin action invoke herdr-gpui-px0.open
```

Invoke actions from a running Herdr GPUI workspace. No build step or binary
download is performed by this plugin. The plugin is independent of Herdr and
px0; neither application is bundled.

Already using a local link? Close its px0 tabs, run
`herdr plugin unlink herdr-gpui-px0`, then install from GitHub. Your config and
plugin state are preserved when the plugin ID stays the same.

Migrating from `herdr-px0`? Close its px0 tabs, remove the old plugin with
`herdr plugin unlink herdr-px0` for a local link, then install the new repo.
Replace `herdr-px0.open` and `herdr-px0.close` in your keybindings with
`herdr-gpui-px0.open` and `herdr-gpui-px0.close`. The new plugin ID uses separate
runtime state; old state is not migrated.

### Local development

```sh
make check
herdr plugin link /path/to/herdr-gpui-px0
herdr plugin action invoke herdr-gpui-px0.open
```

### Release archive

Download `herdr-gpui-px0_0.1.0.tar.gz` and `SHA256SUMS` from
[GitHub Releases](https://github.com/shreyanshrana/herdr-gpui-px0/releases), then:

```sh
shasum -a 256 -c SHA256SUMS
tar -xzf herdr-gpui-px0_0.1.0.tar.gz
herdr plugin link "$PWD/herdr-gpui-px0_0.1.0"
```

Keep the extracted directory in a permanent location. The archive contains
the Python plugin, manifest, documentation, and configuration example; you
still need Python and px0 installed. To update a GitHub-managed install:

```sh
herdr plugin update herdr-gpui-px0
```

Close existing px0 tabs before updating; reopen them to use the new version.

## Keyboard shortcuts

Merge [examples/herdr-config.toml](examples/herdr-config.toml) into
`~/.config/herdr/config.toml`. Replace existing bindings for these keys rather
than adding duplicates, or choose different keys if they are in use:

```toml
[[keys.command]]
key = 'cmd+\'
type = "plugin_action"
command = "herdr-gpui-px0.open"
description = "Open px0 beside terminal"

[[keys.command]]
key = "cmd+alt+w"
type = "plugin_action"
command = "herdr-gpui-px0.close"
description = "Close px0 in this workspace"
```

Reload with `/Applications/Herdr.app/Contents/MacOS/Herdr config reload`.
The actions also appear in Herdr's command palette.

## Behavior

The plugin reads the invoking pane through `HERDR_BIN_PATH` and opens its exact
foreground directory, without jumping to the Git root. Servers
bind only to `127.0.0.1` on a free port; auto-update and telemetry are disabled.
Each terminal/checkout owns a server so closing one pane's px0 tab does not
break another pane's review. The action stays running while its tab is open
and cleans up its child server before exiting.

Runtime metadata, locks, and server logs live under `HERDR_PLUGIN_STATE_DIR`.
No credentials or state are stored in the plugin source directory. Configure
nonstandard binary locations with `PX0_BIN` and `HERDR_GPUI_BIN` environment
variables. px0 can edit files and run coding agents with your user permissions;
use its review/edit actions only on trusted repositories.

## Test and troubleshoot

```sh
python3 -m unittest discover -s tests -v
herdr plugin log list --plugin herdr-gpui-px0
```

To unlink: close px0 tabs first, then run `herdr plugin unlink herdr-gpui-px0` and
remove or restore the two keybindings. Linking does not install px0 or change
keybindings automatically.

## Release packaging

```sh
make package
```

This packages the committed files at `HEAD` into `dist/` and writes SHA-256
checksums. A `v0.1.0` tag triggers the release workflow; the tag version must
match the manifest. Source installation does not require a release archive.

## License

MIT. See [LICENSE](LICENSE). Herdr and px0 retain their own licenses.
