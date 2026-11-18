# SnowRunnerFFBFix — usage

Version 0.2.0, package revision 5. Windows 64-bit, Steam SnowRunner
`1.907887.SNOW_DLC_19`. The plugin remains inactive if its compatibility checks
fail. Only the Logitech G923 has previous physical test results; this
installer change does not constitute a new in-game test.

Extract the ZIP outside the game folder and keep `Install.cmd` with `Sources`.
Close SnowRunner, open `Install.cmd`, select **English**, then **Install the fix**.
Launch the game normally from Steam afterwards. Existing files are never
overwritten. The mod loader is managed automatically: the installer adds the
bundled loader when none exists, or reuses a recognized one. The verified x64
copies of Ultimate ASI Loader 10.0.2 and 8.5.0 (from SMT v1.5) are recognized by
their exact hashes. An unknown DLL or loader configuration blocks installation
without changing existing files. Loading tests with 8.5.0 pass outside the game;
using the fix alongside the actual SMT mod in SnowRunner remains unverified.

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
Uninstallation starts directly, without a DLL question.

- A loader that existed before our installation is always preserved.
- A loader added by our installer is removed if it is recognized, unchanged,
  and no evidence of use by another mod is detected.
- A modified, shared or inaccessible loader, or one whose use is uncertain,
  is preserved without blocking removal of our plugin.

Detection includes hidden plugins, subdirectories, known configuration files,
chained DLLs and `.cxx` sources. Redirected directories, read failures or an
oversized directory tree cause the loader to be preserved. This scan cannot
prove the absence of every possible dependency from another mod.

If the plugin itself has been modified, the operation stops before deleting
anything. The log is preserved. The receipt records the actual reused loader
hash and ownership, and is removed on uninstall. A preserved loader is treated
as pre-existing on subsequent installation.

For scripts: `Sources/Scripts/manage.ps1 -Action Uninstall -GameDirectory <folder>`
applies the same automatic rules. The old `-RemoveLoader` parameter remains
accepted for existing scripts, without changing those rules.

Before upgrading, uninstall the old version with the game closed. Keep the
previous package to allow rolling back. Neither the game executable on disk nor
Windows system DLLs are modified.
