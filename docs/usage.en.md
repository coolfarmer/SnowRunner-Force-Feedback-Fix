# SnowRunnerFFBFix — usage

Version 0.2.0, package revision 4. Windows 64-bit, Steam SnowRunner
`1.907887.SNOW_DLC_19`. The plugin remains inactive if its compatibility checks
fail. Only the Logitech G923 has previous physical test results; this
package reorganization does not constitute a new in-game test.

Extract the ZIP outside the game folder and keep `Install.cmd` with `Sources`.
Close SnowRunner, open `Install.cmd`, select **English**, then **Install the fix**.
Launch the game normally from Steam afterwards. Existing files are never
overwritten. A different DLL or unfamiliar loader configuration blocks installation.

Navigate the Spectre.Console menu with the arrow keys and Enter. The interface
includes .NET; no additional runtime installation is needed. Windows PowerShell
5.1 performs the installation operations. Keep the extracted package complete;
the interface is not copied into the game.
`Install.cmd --plain` offers numbered menus, also selected automatically when
input or output is redirected. The original PowerShell menu remains available
via `powershell.exe -NoProfile -ExecutionPolicy Bypass -File Sources/Scripts/menu.ps1`.

**View status** shows the last recorded state; counters do not measure how the
wheel feels. **More options** lets you check the installation, select the game
folder, disable or re-enable the fix. Disabling takes effect on the next launch.

## Uninstalling

Close SnowRunner, open `Install.cmd` and choose **Uninstall**.
A separate question asks whether to keep `dinput8.dll`:

The first choice is selected by default. The numbers below apply to plain text
mode; use the arrow keys and Enter in the interactive menu.

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

For scripts: `Sources/Scripts/manage.ps1 -Action Uninstall -GameDirectory <folder>` keeps
the loader without an interactive prompt. Add `-RemoveLoader` to request removal
with the same protections. The menu provides the interactive choice.

Before upgrading, uninstall the old version with the game closed. Keep the
previous package to allow rolling back. Neither the game executable on disk nor
Windows system DLLs are modified.
