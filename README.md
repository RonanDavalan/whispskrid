<p align="center">
  <a href="https://github.com/RonanDavalan/whispskrid/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/version-v1.0.0-brightgreen.svg" alt="Version v1.0.0"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="#"><img src="https://img.shields.io/badge/OS-Debian_13-D70A53.svg" alt="Tested on Debian 13"></a>
</p>

# WhispSkrid

A command-line, push-to-talk dictation tool for Linux: hold a key, speak,
release — the text transcribed locally by Whisper (`faster-whisper`) is
injected into whichever window currently has keyboard focus. All recognition
runs offline; no audio or transcribed text ever leaves the machine.

Capture is strictly push-to-talk: there is no wake phrase, no listening
state, no automatic cut on silence. See `docs/whispskrid.1.md` (manual page
source, also in `fr`/`de`/`es`) for the full command reference, and
`docs/configuration.md` for every `config.yaml` key.

## Status

First stable release (`v1.0.0`): dictation, injection, the control socket,
`pynput` push-to-talk, `--diagnose`, and a four-language CLI interface
(`en`/`fr`/`de`/`es`) are implemented and covered by the test suite.

## Install the Debian package

```bash
sudo apt install ./whispskrid_1.0.0_all.deb
```

Download the package from
[whispskrid.davalan.fr](https://whispskrid.davalan.fr) or from the
[Releases page](https://github.com/RonanDavalan/whispskrid/releases). See
the site for what the package installs and how to verify the download.

## Run from source

```bash
git clone https://github.com/RonanDavalan/whispskrid.git
cd whispskrid
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/whispskrid --diagnose
```

`--diagnose` reports what is still missing on your system (injection
backend, audio input, a downloaded model) before you run a real dictation.

## Running the tests

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

## License

This project is licensed under the **MIT License**. See the
[LICENSE](LICENSE) file for details.
