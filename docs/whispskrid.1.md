% WHISPSKRID(1) whispskrid | User Commands
% Ronan Davalan
% 2026-09-18

# NAME

whispskrid - offline, system-wide push-to-talk dictation for the command line

# SYNOPSIS

**whispskrid** [**-l** *LANG* | **\--lang** *LANG*] [**\--model** *NAME*]

**whispskrid** **\--diagnose**

**whispskrid** **\--download-model** [*NAME*]

**whispskrid** {**\--dictate** | **\--dictate-stop** | **\--toggle** | **\--cancel** | **\--status** | **\--stop**}

**whispskrid** **\--version**

# DESCRIPTION

**whispskrid** is a command-line dictation tool for Linux, powered by the
offline Whisper speech recognition engine (**faster-whisper**). Capture is
strictly push-to-talk: audio is recorded only while a key is held down (or,
equivalently, between a **\--dictate** and a **\--dictate-stop** command), and
the recognized text is injected directly into whichever window currently
holds keyboard focus — terminal, browser, editor, or any other application —
so it works system-wide rather than inside a single program.

All speech recognition runs locally: no audio or transcribed text is ever
sent to a remote service.

Only one session runs per user at a time. Launched with no control flag, it
starts a resident session: it loads the model, opens a private Unix control
socket at `$XDG_RUNTIME_DIR/whispskrid.sock` (mode `0600`), and starts a
`pynput` hotkey listener if enabled. The same command invoked with a control
flag (see CONTROLLING A RUNNING SESSION) connects to that socket instead of
starting a new session.

Text is injected by placing it on the clipboard and simulating a paste, so
two kinds of tool are needed: a keystroke simulator and a clipboard tool.
Under Wayland this is **ydotool** (needs the `ydotoold` daemon and access to
`/dev/uinput`) plus **wl-clipboard**; under X11 it is **xdotool** plus
**xclip**. Without either backend, injection falls back to a degraded mode.
The choice between the two is made once, at startup, by probing which
binary and daemon actually respond — not by checking the session type
directly. **whispskrid \--diagnose** reports which tools, audio device and
clipboard access are present, then exits.

# INSTALLATION

Install the package for your distribution:

Debian and derivatives:
```
sudo dpkg -i whispskrid_1.0.0_all.deb
```

Fedora:
```
sudo dnf install ./whispskrid-1.0.0-1.fc42.noarch.rpm
```

openSUSE Leap 15.6:
```
sudo zypper install ./whispskrid-1.0.0-1.leap156.noarch.rpm
```

Arch Linux:
```
sudo pacman -U whispskrid-1.0.0-1-any.pkg.tar.zst
```

The post-install step installs **faster-whisper** via pip into a private
virtual environment and reports its own progress; the package covers the
injection backend for your session type (**ydotool** + **wl-clipboard** under
Wayland, **xdotool** + **xclip** under X11) — none of them is a hard
dependency on every distribution, so an incomplete environment still
installs, at the cost of a degraded injection mode (see **\--diagnose**
below).

No Whisper model ships with the package. Download one before first use —
models come from the official CTranslate2 conversions on Hugging Face
(*https://huggingface.co/Systran*), fetched automatically into the managed
model directory (see FILES below):

```
whispskrid --download-model
```

Skipping this step is not fatal: the resident session downloads the default
model itself on first launch, announcing it first since Hugging Face's own
download shows no progress bar (a multi-hundred-MB transfer with no visible
activity otherwise).

Then verify the environment:

```
whispskrid --diagnose
```

Global hotkeys via `pynput` watch the X server: under Wayland they reach only
windows running through XWayland, never a focused native-Wayland window.
Bind the control subcommands to your desktop's own shortcut settings for
control that works everywhere.

# OPTIONS

**-l** *LANG*, **\--lang** *LANG*
:   Force the interface and speech recognition language for this session
    (`en`, `fr`, `de` or `es`), overriding `default_language` from the
    configuration file. Also selects the language of the CLI's own messages
    (help text included).

**\--model** *NAME*
:   Override `models.default` from the configuration file for this session —
    a model's short name (one of `tiny`, `base`, `small`, `medium`,
    `large-v3`, or their `.en` variants — see **\--download-model** below)
    or a filesystem path.

**\--diagnose**
:   Check the environment (session type, injection backend, tools, GPU/CUDA,
    model presence, audio input, clipboard, control socket, configuration)
    and exit. Exit status is `0` when every blocking check passes; some
    checks (GPU acceleration, `ydotool`/`xdotool` presence taken
    individually) are informative only and never block the exit status.

**\--download-model** [*NAME*]
:   Download a Whisper model (`base` when *NAME* is omitted; one of `tiny`,
    `base`, `small`, `medium`, `large-v3`, or their `.en` variants) from
    Hugging Face into the managed model directory
    (`~/.local/share/whispskrid/whisper-models/` by default — see FILES),
    then exit. Already-downloaded models are detected and skipped.

**\--version**
:   Print the version number and exit.

# CONTROLLING A RUNNING SESSION

Each of the following flags connects to the socket of the running session,
performs the action, prints the resulting reply (`OK`, `OK <text>` or
`ERR <reason>`), and exits with status `0` on `OK`, `1` otherwise. They are
meant to be bound to desktop keyboard shortcuts.

**\--dictate**
:   Start capture. Fails with `ERR already-capturing` if a capture is
    already in progress.

**\--dictate-stop**
:   Stop the current capture, transcribe it, and inject the result. Fails
    with `ERR not-capturing` if no capture is in progress.

**\--toggle**
:   **\--dictate** or **\--dictate-stop**, depending on the session's current
    state — a single shortcut for a press-to-start / press-to-stop
    push-to-talk key bound at the desktop level.

**\--cancel**
:   Discard the capture in progress without transcribing or injecting
    anything.

**\--status**
:   Print the current session state (`state=idle|capturing model=<name>
    language=<lang|auto>`) without changing it.

**\--stop**
:   Shut the running resident session down cleanly.

# HOTKEYS

`pynput` global hotkeys are started whenever `hotkeys.pynput_enabled` is
true in the configuration file and a display server is reachable
(`DISPLAY` set) — on any session type, Wayland included, since `pynput`
itself watches the X server. The listener does not consume the key
event: the keystroke also reaches the focused window. The factory
configuration binds push-to-talk to:

**Right Shift**
:   Hold to capture, release to stop, transcribe and inject — the native
    press/release semantics of `pynput` implement push-to-talk directly on
    this path (unlike the control-socket path above, which only sees
    discrete commands and must therefore expose **\--toggle** instead).

The bound key(s) are configurable under `hotkeys.push_to_talk` in the
configuration file. Each name below designates one physical key: `ctrl_r`
(right Control), `ctrl_l` (left Control), `alt_r` (right Alt), `alt_l`
(left Alt), `shift_r` (right Shift), `shift_l` (left Shift), `cmd`, `f1`
through `f12` (function keys). Listing more than one turns them into a
combination: all of them must be held together, in any order, to engage
push-to-talk (for instance `["alt_l", "shift_r"]`); in `mode: hold`,
releasing any one of them stops and injects. A modifier-key combination
can collide with a desktop-level shortcut (for instance, Alt+Shift is
commonly bound to a keyboard-layout switch on KDE Plasma and GNOME) —
a function key such as `f4` avoids that class of conflict.

`hotkeys.min_hold_ms` (milliseconds, default `250`) applies to `mode: hold`
only: a press released before this delay cancels the capture instead of
transcribing and injecting it — a guard against a brief, unintended tap of
the bound key (a desktop shortcut sharing the same key, for instance) that
would otherwise capture background noise or near-silence, which Whisper can
hallucinate into stray text.

`hotkeys.mode` (`hold`, the default, `toggle`, or `armed`) controls what
pressing the bound key does. `hold` is the behavior described above,
guarded by `hotkeys.min_hold_ms`. `toggle` starts capture on the first
press and stops, transcribes and injects on the next press of the same
key; releasing the key does nothing in this mode — useful to avoid holding
a key down for a long dictation. `armed` arms continuous listening for a
spoken phrase on the first press — a short phrase opens a capture segment,
another closes and injects it, until a second press disarms; see the
`wakeword` key in **configuration.md** (CONFIGURATION below).

To change the bound key(s) or the mode, edit `hotkeys.push_to_talk` /
`hotkeys.mode` in the configuration file (see CONFIGURATION below for its
exact path), then restart the resident session for the change to take
effect:

```
whispskrid --stop
whispskrid
```

To bind **\--toggle** to a desktop-level shortcut instead — the only
option under Wayland for windows that do not go through XWayland, which
`pynput` cannot reach — most desktop environments offer a custom shortcut
setting. On GNOME: *Settings → Keyboard → View and Customize Shortcuts →
Custom Shortcuts → Add Shortcut*, with `whispskrid --toggle` as the
command and the key combination of your choice. KDE Plasma offers the
equivalent under *System Settings → Shortcuts → Custom Shortcuts*.

# CONFIGURATION

Runtime behavior is controlled by a YAML configuration file: default
language, backend and model parameters, capture duration guard, audio
device, post-processing, hotkeys.

The configuration file is located by the first matching rule below; once a
rule matches, the remaining rules are not consulted.

1. The path given in the **WHISPSKRID_CONFIG** environment variable, if set.
   Used as-is; never created automatically.
2. `config/config.yaml`, relative to the project directory, when running
   from a Git checkout (development mode).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (default
   `~/.config/whispskrid/config.yaml`). Created automatically on first run,
   from the factory template.
4. The factory template: `/usr/share/whispskrid/config.yaml` (Debian package
   install), otherwise the `config/config.yaml` embedded in the project
   (covers running from a source tarball without a `.git` directory).

The resolved file may be partial: any key it omits falls back to the factory
template's value, merged key by key.

The active language is chosen, in order: the **\--lang** option, if given;
otherwise `default_language` from the configuration file; otherwise
automatic detection by the recognition backend.

See **configuration.md** in the project documentation for the full reference
of every configuration key.

# TROUBLESHOOTING

**Model not found.** Run **\--diagnose** and read its final summary line,
which names the first blocking check by itself — do not guess from the raw
output above it:

```
whispskrid --diagnose
```

If the summary line names the model check, download one:

```
whispskrid --download-model
```

Then re-run **\--diagnose**; it exits `0` once every blocking check passes
(see EXIT STATUS).

# FILES

`~/.config/whispskrid/config.yaml`
:   Per-user configuration file.

`/usr/share/whispskrid/config.yaml`
:   Factory configuration template (Debian package install), read-only.

`~/.local/share/whispskrid/whisper-models/`
:   Default managed directory for downloaded Whisper models.

`config/config.yaml`
:   Configuration file used when running from a Git checkout.

`whisper-models/`
:   Default location searched for Whisper models when running from a Git
    checkout or a source tarball.

`$XDG_RUNTIME_DIR/whispskrid.sock`
:   Control socket of the running session (mode `0600`).

# EXIT STATUS

**0**
:   The program exited cleanly, or a control command received `OK`.

Non-zero
:   Startup failed (no injection backend, model, or audio device available),
    or a control command received `ERR`.

# EXAMPLES

Start a resident session with the default language from the configuration
file:

```
whispskrid
```

Force English for this session:

```
whispskrid --lang en
```

Bind to desktop shortcuts for push-to-talk without relying on `pynput`:

```
whispskrid --dictate
whispskrid --dictate-stop
```

# SEE ALSO

faster-whisper: *https://github.com/SYSTRAN/faster-whisper*

Whisper model catalog: *https://huggingface.co/Systran*

Project homepage: *https://whispskrid.davalan.fr/*

# BUGS

Report bugs on the project's issue tracker:
*https://github.com/RonanDavalan/whispskrid/issues*

# AUTHOR

Ronan Davalan.
