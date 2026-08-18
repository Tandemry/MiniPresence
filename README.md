# MiniPresence

MiniPresence is a small Windows app that shows a custom Discord Rich Presence while a chosen app
is open. It supports ordinary desktop programs as well as Edge and Chrome installed web apps, and
works with both the standard Discord desktop client and Discord Canary.

The packaged executable, app window, and notification-area icon use the MiniPresence artwork.
The compact 480-by-450 interface uses a cohesive dark theme with coral controls, searchable app
selection, clear connection states, and an inline Discord status preview.

No Discord password, user token, Application ID, or bot token is requested. MiniPresence uses its
shared Discord application identity and talks to the Discord desktop client through its local Rich
Presence connection.

## Download

Download the latest `MiniPresence-*-windows-x64.zip` from the repository's **Releases** page,
extract it, and run `MiniPresence.exe`. Windows SmartScreen may show a warning for an unsigned,
newly published executable; review the source or build it yourself if preferred.

## Set up Discord

Keep Discord or Discord Canary running and make sure activity sharing is enabled in Discord. That
is all: MiniPresence includes the project-owned Discord Application ID, so users do not create a
Discord developer application or link an account.

## Choose an app

1. Open the desktop program or installed web app you want to share.
2. Open MiniPresence and select **Choose app**.
3. Choose it by its normal name and select **Start**.

The chooser shows apps that are currently open. There are no process names, web app IDs, or other
technical details to enter. MiniPresence remembers the selection across launches; the next time it
opens, it immediately resumes watching for the saved app.

Known apps can also use their own public artwork in Discord. Volute Dashboard automatically uses
its supplied dashboard logo as the large Rich Presence image.

Enable **Start MiniPresence with Windows** to launch it quietly in the notification area after
sign-in. It automatically watches for the saved app and updates Discord whenever that app opens.
Use the notification-area icon to reopen or quit MiniPresence. The optional **Customize status**
screen changes the two lines shown on Discord; `{app_name}` inserts the selected app's name.

## Current scope

- Windows 10/11
- Currently open Windows desktop apps
- Microsoft Edge and Google Chrome installed web apps
- Discord desktop and Discord Canary
- One saved app at a time
- Optional background startup and notification-area control
- Automatic Discord reconnection and lightweight background monitoring

Desktop apps are identified by their program, so multiple windows from the same program count as
one app. Installed Edge and Chrome web apps are identified separately when possible. Multiple
profiles, page-by-page presence changes, and code signing are possible follow-up features.

## Build from source

Install Python 3.10 or later, clone the repository, then run:

```powershell
./scripts/build.ps1
```

The script tests the project and creates a standalone Windows executable plus a release ZIP under
`dist/`. Users of the packaged executable do not need Python installed.

## Publishing a release

Push a tag such as `v1.0.0`. The included GitHub Actions workflow builds the Windows executable and
attaches the ZIP to a new GitHub Release automatically.

```powershell
git tag v1.0.0
git push origin v1.0.0
```

## Development

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m minipresence
```

## License

[MIT](LICENSE)
