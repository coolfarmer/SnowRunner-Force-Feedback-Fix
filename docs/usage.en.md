# SnowRunnerFFBFix 0.2.0 — experimental native plugin

Version 0.2.0, package revision 1. Extract the complete ZIP anywhere. Keep `Install.cmd` and
the `Sources` folder together. Open **Install.cmd**, then select **English**.
You can change the language from the main menu; no game files are changed by
opening the menu or choosing a language.

## Install and use

To upgrade an existing installation, close the game and choose **Uninstall**
before installing 0.2.0. Either package can read the existing installation receipt.
No plugin is overwritten. Keep the previous archive to roll back using the same
uninstall/install procedure. Pre-existing or modified files remain protected.

1. Close SnowRunner.
2. Open `Install.cmd`, choose English, then **Install the fix**.
3. Compatibility checks run automatically. Once installation succeeds, launch
   SnowRunner normally from Steam. No separate game launcher is required.
4. Use **View status** to check the recorded plugin state. The interface separates
   historical logs from a currently running session. Counters describe memory
   initialization, not physical wheel forces.

**More options** provides a read-only compatibility check, temporary disabling,
re-enabling, and manual game-folder selection. Paste the game folder or `Sources\Bin`;
an empty path restores automatic Steam detection. Use **Uninstall** with the game
closed to remove the files owned by this installation. Existing/shared loaders,
modified files and the diagnostic log are preserved as reported on screen.

## Compatibility and scope

Windows x64; verified Steam executable `1.907887.SNOW_DLC_19`. The game hash is
listed in `package.json` and embedded in the plugin. All thirteen loaded-code
guards remain mandatory. An unrecognized game or changed target code leaves the fix inactive. Do not
change the manifest to bypass a check: it does not override compiled runtime guards.

The fix no longer requires the Logitech SDK or G HUB and does not filter wheel
models. The game still needs the drivers/SDKs appropriate to your device.
Static code analysis establishes a shared force source for DirectInput, Logitech
Legacy, TRUEFORCE and HORI. Thrustmaster mode creates the same DirectInput devices.
Other brands may benefit when using these paths; this does not add support for
wheels the game cannot recognize or fix every possible cause of oscillation.
Only the G923 has previous physical test results. Other models remain untested.

The local `dinput8.dll` is Ultimate ASI Loader 10.0.2. It loads
`SnowRunnerFFBFix.asi`, which uses MinHook 1.3.4 to initialize exactly four fields
(16 bytes) at a verified game constructor's entry. No wheel API, force clamp,
gain adjustment or periodic reset is added. The game executable on disk and
Windows system DLLs are not modified. Python and Frida are not required.

Installation refuses overwrites and unfamiliar existing loader configuration.
If Windows denies access, check folder permissions or run Install.cmd as
administrator when appropriate. The package does not elevate automatically.

## Status and errors

The displayed state and failure explanations use the selected language. Raw
plugin logs remain in their original diagnostic format; the menu translates their
meaning and does not print the raw English log. Unexpected Windows errors are
summarized in the selected language, with technical details saved to
`Sources/setup-diagnostic.log` when possible. Logs and license texts are technical
records, not translated installation prompts.

Disabling takes effect on the next launch; it does not stop forces already sent
to the wheel. Exit the game before disabling or uninstalling. The module is not
unloaded live. After an unknown update, the plugin must be validated against the
new version before it can apply the fix again.

## Test status

The previous 0.1.0 version was tested on a G923 on November 16, 2026: the user reported eleven
explicitly counted transitions, plus further uncounted transitions during a longer
session, without abnormal oscillations and with normal force feedback. Automatic
reactivation and a round trip after restarting were also checked. Disabling was
verified at the main menu, followed by uninstalling and launching without the
plugin. These results apply to the tested configuration, not every game version,
wheel or mod combination. Quantitative performance measurements remain outstanding.

Version 0.2.0 rebuilds the plugin without the SDK gate; the loader and the four-field
correction are unchanged. Automated tests cover activation with an absent or
different SDK, rejection of an unknown game or changed loaded code, and installation,
disable/enable and uninstall operations. No new in-game or physical test has been
performed with 0.2.0. Start physical trials at reduced force with an accessible way
to interrupt effects; compare several transitions and check normal force feedback,
steering, pedals and buttons. Source code and automated regression tests are available in the repository.
Upstream license notices are included alongside this guide.
