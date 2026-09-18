<p align="center">
  <a href="https://github.com/RonanDavalan/whispskrid/releases/tag/v1.0.1"><img src="https://img.shields.io/badge/version-v1.0.1-brightgreen.svg" alt="Version v1.0.1"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="#install"><img src="https://img.shields.io/badge/packages-Debian_%C2%B7_Ubuntu_%C2%B7_Fedora_%C2%B7_openSUSE_%C2%B7_Arch-informational.svg" alt="Packages for Debian, Ubuntu, Fedora, openSUSE and Arch Linux"></a>
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

First stable release (`v1.0.1`): dictation, injection, the control socket,
`pynput` push-to-talk, `--diagnose`, and a four-language CLI interface
(`en`/`fr`/`de`/`es`) are implemented and covered by the test suite.

<a id="install"></a>

## Install

Download the package for your distribution from
[whispskrid.davalan.fr](https://whispskrid.davalan.fr) or from the
[Releases page](https://github.com/RonanDavalan/whispskrid/releases), then
install it with your package manager:

```bash
# Debian 12 and 13, Ubuntu 22.04 and 24.04 and their derivatives
sudo apt install ./whispskrid_1.0.1_all.deb

# Fedora 42
sudo dnf install ./whispskrid-1.0.1-1.fc42.noarch.rpm

# openSUSE Leap 15.6
sudo zypper install ./whispskrid-1.0.1-1.leap156.noarch.rpm

# Arch Linux
sudo pacman -U whispskrid-1.0.1-1-any.pkg.tar.zst
```

Then fetch a Whisper model and start dictating:

```bash
whispskrid --download-model base
whispskrid
```

Every package is installed, checked with `whispskrid --diagnose` and removed
cleanly in a container of each version listed above. The Debian package has
also been validated in real use on Debian 13, dictation included, on several
physical machines; the other packages have not yet been exercised in a real
graphical session. Other systems are not covered — that is simply the
perimeter that has been tested. See the site for what a package installs and
how to verify the download (`SHA256SUMS`).

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
