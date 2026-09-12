# Project Configuration Guide

This document explains every option available in `config.yaml`. Properly
configuring this file lets you tailor WhispSkrid to your hardware, your
language, and your desktop environment.

## How the configuration file is located

The file is located by the first matching rule below; once a rule matches,
the remaining rules are not consulted.

1. The path given in the **WHISPSKRID_CONFIG** environment variable, if set.
   Used as-is; never created automatically.
2. `config/config.yaml`, relative to the project directory, when running
   from a Git checkout (development mode — active when `.git` exists next
   to the project root **and** the file exists there).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (default
   `~/.config/whispskrid/config.yaml`). Created automatically on first run
   by copying the factory template, with a message naming the file created.
4. The factory template: `/usr/share/whispskrid/config.yaml` (Debian
   package install), otherwise the `config/config.yaml` embedded in the
   project (covers running from a source tarball without a `.git`
   directory).

The resolved file may be **partial**: any key it omits falls back to the
factory template's value, merged key by key (nested sections merge
recursively — you only need to repeat the leaves you want to change, never
the whole block).

## General structure of `config.yaml`

```yaml
default_language: "..."
backend: {...}
models: {...}
capture: {...}
audio: {...}
vad: {...}
post_processing: {...}
hotkeys: {...}
control_socket: true
clipboard: {...}
injection: {...}
sound_file: "..."
theme: {...}
```

## Configuration sections in detail

### `default_language`

Forces the interface language and the speech recognition language. Empty
(the factory default) means: interface in the system's language, speech
recognition in Whisper's automatic language detection. Overridable per
session with `-l`/`--lang`.

```yaml
default_language: ""
```

### `backend`

Selects the speech recognition engine. `faster-whisper` is the only value
accepted in v0.1.0; the key is reserved for a future second backend
(`whisper.cpp`).

- **`name`** (string): `"faster-whisper"`, the only accepted value.
- **`beam_size`** (integer, default `5`): beam width passed to
  `WhisperModel.transcribe()`. Higher values can improve accuracy at the
  cost of latency.

```yaml
backend:
  name: "faster-whisper"
  beam_size: 5
```

### `models`

Which Whisper model to load, and how.

- **`default`** (string, default `"base"`): a short model name (`tiny`,
  `base`, `small`, `medium`, `large-v3`, and their `.en` variants), resolved
  inside `models.dir`, or an absolute path to a model directory. Overridable
  per session with `--model`.
- **`dir`** (string, default empty): the managed models directory.  Empty
  means: resolve automatically, in order,
  `$WHISPSKRID_MODELS_DIR` (if set) → `~/.local/share/whispskrid/whisper-models/`
  (if it already holds a model) → `/usr/share/whispskrid/whisper-models/`
  (package install) → `whisper-models/` at the root of a Git checkout — the
  first of these that exists and holds at least one model wins. If none
  does, the user directory is created and used as the destination for
  `--download-model`.
- **`device`** (string, default `"auto"`): `"cpu"`, `"cuda"`, or `"auto"`
  (let `faster-whisper` decide).
- **`compute_type`** (string, default `"auto"`): `"int8"`,
  `"int8_float16"`, `"float16"`, or `"auto"` (`int8` on CPU, `float16` on
  CUDA).

```yaml
models:
  default: "base"
  dir: ""
  device: "auto"
  compute_type: "auto"
```

### `capture`

- **`max_seconds`** (integer, default `300`): safety cutoff. If the
  push-to-talk key is held past this many seconds, the capture stops on its
  own, transcribes and injects whatever was recorded, and logs a warning.
  This is a guard against a stuck key or an unbounded audio buffer — not a
  comfort timer for ordinary use.

```yaml
capture:
  max_seconds: 300
```

### `audio`

Parameters for the microphone input stream, opened once when the resident
session starts and kept open between dictations.

- **`sample_rate`** (integer, default `16000`): must match the rate Whisper
  expects.
- **`channels`** (integer, default `1`): mono.
- **`frames_per_buffer`** (integer, default `4096`): PortAudio read
  granularity — also the rounding unit of `capture.max_seconds` and of a
  recorded episode's length.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
```

### `vad`

Reserved for a future silence-based automatic stop. **Not implemented in
v0.1.0**: `vad.enabled: true` logs a "not yet implemented" warning and the
tool keeps behaving as strict push-to-talk (the key you hold is the only
thing that starts and stops a capture).

```yaml
vad:
  enabled: false
  silence_ms: 800
```

### `post_processing`

Whisper punctuates and capitalizes sentences on its own; WhispSkrid's
post-processing is deliberately minimal.

- **`trim`** (boolean, default `true`): strip leading/trailing whitespace
  from the transcribed text.
- **`capitalize_sentence_start`** (boolean, default `true`): force a
  capital on the first letter of the injected text — Whisper sometimes
  omits it on a short fragment.

```yaml
post_processing:
  trim: true
  capitalize_sentence_start: true
```

### `hotkeys`

- **`pynput_enabled`** (boolean, default `true`): start the `pynput` global
  listener. `pynput` watches the X server, so it is started whenever one is
  reachable (`DISPLAY` set), on any session type; under Wayland it only
  sees key events for windows running through XWayland, never a focused
  native-Wayland window. Set to `false` to never start it and drive the
  tool only through the control subcommands bound to your desktop's own
  shortcuts.
- **`push_to_talk`** (list, default `["ctrl_r"]`): the push-to-talk key.
  Held down → capture; released → transcribe and inject (in `mode: hold`,
  see below). `pynput` distinguishes press from release natively, so the
  hold semantics are exact on this path. The control-socket subcommands
  (`--dictate`, `--dictate-stop`, `--toggle`) exist for desktops whose
  shortcut system cannot convey "key held", where they act as a
  start/stop toggle instead.
- **`mode`** (`hold` or `toggle`, default `hold`): what a press of the
  bound key does. `hold` is the behavior described above. `toggle` starts
  capture on the first press and stops, transcribes and injects on the
  next press of the same key; the key release does nothing in this mode.
  Purely additive: `push_to_talk` and its hold semantics are unchanged
  when `mode` is absent or set to `hold`.

```yaml
hotkeys:
  pynput_enabled: true
  push_to_talk: ["ctrl_r"]
  mode: "hold"
```

### `control_socket`

Boolean, default `true`. When enabled, the running session listens on a
Unix socket at `$XDG_RUNTIME_DIR/whispskrid.sock` (mode `0600`) so the
control subcommands can drive it. Set to `false` to disable the socket
entirely.

```yaml
control_socket: true
```

### `clipboard`

Text is injected by placing it on the clipboard and simulating a paste.

- **`restore`** (boolean, default `true`): put the user's previous
  clipboard content back after pasting. A non-text clipboard (an image, for
  instance) is never saved or overwritten.
- **`restore_delay_ms`** (integer, default `400`): the maximum window,
  polled in short slices, left for the target application to read the
  selection before the clipboard is restored. The wait stops early if the
  clipboard has already changed (another owner took over) — the
  restoration is then abandoned rather than fought over.
- **`defer_restore`** (boolean, default `false`): when `true`, the
  clipboard is never restored inline; the original content — the one from
  before the first dictation of the session — is put back once, at the end
  of the session (or via `atexit` on a crash). Removes the clipboard race
  seen under Wayland with GTK applications entirely, at the cost of the
  clipboard carrying the last dictated segment between two dictations of an
  active session.
- **`confirm_timeout_ms`** (integer, default `500`): maximum time to wait
  for confirmation that the clipboard actually holds the dictated text
  before sending the paste keystroke.

```yaml
clipboard:
  restore: true
  restore_delay_ms: 400
  defer_restore: false
  confirm_timeout_ms: 500
```

### `injection`

The keystroke backend is chosen once, at startup, by direct probing —
never re-tested before every paste. The cascade is **`ydotool`** (if the
binary exists and its daemon answers) → **`xdotool`** (if the binary
exists) → degraded mode (text left on the clipboard, no keystroke sent).
See the project's Wayland compatibility notes for why `wtype` is
deliberately not part of this cascade.

- **`paste_combo`** (string, default `ctrl+v`) and
  **`terminal_paste_combo`** (default `ctrl+shift+v`): the key combination
  used to paste. Window-class detection (to pick the terminal combo
  automatically) is only available on the `xdotool` path — `ydotool`
  injects at the `/dev/uinput` level and has no notion of a targeted
  window, so `paste_combo` is always used there unless you override it.
- **`terminal_window_classes`** (list): window classes treated as
  terminals (`xdotool` path only).
- **`ydotool_keycodes`** (mapping): physical Linux keycodes, used only on
  the `ydotool` path, which sends raw keycodes rather than keysyms.
  Override these under a non-QWERTY layout.

```yaml
injection:
  paste_combo: "ctrl+v"
  terminal_paste_combo: "ctrl+shift+v"
  terminal_window_classes: ["konsole", "gnome-terminal-server", "xterm", "st", "alacritty", "kitty", "foot"]
  ydotool_keycodes: {}
```

### `sound_file`

Absolute path to a short notification sound file (e.g. `.oga`, `.wav`),
played through `paplay` to confirm the start of a capture. Empty or a
missing `paplay` silently disables the sound.

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

Console color theme. Values must be valid `colorama` color names (e.g.
`GREEN`, `RED`, `BLUE`, `RESET`).

- **`ready_message`**: color of the "ready" banner.
- **`help_text`**, **`help_title`**: help message colors.
- **`info`**, **`success`**, **`warning`**, **`error`**: status message
  colors.

```yaml
theme:
  ready_message: "GREEN"
  help_text: "RESET"
  help_title: "CYAN"
  info: "RESET"
  success: "GREEN"
  warning: "YELLOW"
  error: "RED"
```
