<img width="1746" height="434" alt="Miniprestexto1" src="https://github.com/user-attachments/assets/da668690-e8a1-4f55-ab74-f8b47ff5e4db" />

MiniPresence is an incredibly small Windows app that shows a custom Discord Rich Presence while a chosen app
is open. That's literally it.

It supports ordinary desktop programs as well as Edge and Chrome installed web apps, and
works with both the standard Discord desktop client and Discord Canary.

Presence is shown only while the selected app owns the active, visible window. Switching to
another app or minimizing the selected app clears the presence; returning to it restores the
presence automatically.

## Download

Download the latest `MiniPresence-*-windows-x64.zip` from the repository's **Releases** page,
extract it, and run `MiniPresence.exe`.

## Set up 

Keep Discord or Discord Canary running and make sure activity sharing is enabled in Discord. That
is all you need to do.

It is designed with simplicity in mind, so everything you encounter is mostly self-explanatory; its quite easy to figure it out.

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
