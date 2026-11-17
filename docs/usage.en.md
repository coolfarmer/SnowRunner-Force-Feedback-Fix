# SnowRunnerFFBFix — usage

Version 0.2.0, package revision 2. Windows 64-bit, Steam SnowRunner
`1.907887.SNOW_DLC_19`. The plugin remains inactive if its compatibility checks
fail. Only the Logitech G923 has previous physical test results; this
uninstaller change does not constitute a new in-game test.

Extract the ZIP outside the game folder and keep `Install.cmd` with `Sources`.
Close SnowRunner, open `Install.cmd`, select **English**, then **Install the fix**.
Launch the game normally from Steam afterwards. Existing files are never
overwritten. A different DLL or unfamiliar loader configuration blocks installation.

**View status** shows the last recorded state; counters do not measure how the
wheel feels. **More options** lets you check the installation, select the game
folder, disable or re-enable the fix. Disabling takes effect on the next launch.

## Uninstalling

Close SnowRunner, open `Install.cmd` and choose **Uninstall**.
A separate question asks whether to keep `dinput8.dll`:

- **1 — Yes, keep (default)**: pressing Enter selects this answer.
  The plugin is removed and the loader stays available for other mods.
- **2 — No, request removal of dinput8.dll**: removal is allowed only if our
  installer added it, it is unchanged, and no other `.asi` plugin is detected
  in the game folder and its subfolders.
- **0 — Cancel uninstall**: no files are changed.

End of input before answering also cancels the operation. Pre-existing or
shared loaders are preserved even when removal is requested. If a file to
remove has been modified, uninstall stops before deleting anything. A modified
DLL does not prevent uninstalling the fix when **Yes, keep** is selected.
The diagnostic log is preserved.

Looking for `.asi` files cannot prove that nothing else depends on the loader.
Keeping `dinput8.dll` remains the recommended choice when unsure. Uninstalling
removes the fix's receipt; after keeping the DLL, a subsequent installation
treats it as pre-existing and protects it. The removal choice is offered during
uninstall, not as a DLL cleanup tool without an installation receipt.

For scripts: `Sources/manage.ps1 -Action Uninstall -GameDirectory <folder>` keeps
the loader without an interactive prompt. Add `-RemoveLoader` to request removal
with the same protections. The menu provides the interactive choice.

Before upgrading, uninstall the old version with the game closed. Keep the
previous package to allow rolling back. Neither the game executable on disk nor
Windows system DLLs are modified.
