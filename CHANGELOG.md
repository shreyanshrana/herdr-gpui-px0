# Changelog

## 0.1.0

- Open px0 in a Herdr GPUI browser split beside the invoking terminal.
- Preserve the terminal's foreground directory, including subdirectories.
- Reuse the existing tab for the same pane and directory.
- Close plugin-owned px0 tabs in the current workspace without closing terminals.
- Stop the local px0 server when its browser tab closes.
- Keep runtime state outside the plugin installation; bind servers to localhost.
