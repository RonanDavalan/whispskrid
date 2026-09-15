# Projektkonfigurationsanleitung

Dieses Dokument erklärt alle verfügbaren Optionen in `config.yaml`. Eine korrekte Konfiguration dieser Datei ermöglicht es Ihnen, WhispSkrid an Ihre Hardware, Ihre Sprache und Ihre Desktop-Umgebung anzupassen.

Wie die Konfigurationsdatei gefunden wird.

Die Datei wird anhand der ersten passenden Regel gefunden; sobald eine Regel zutrifft, werden die restlichen Regeln nicht mehr berücksichtigt.

1. Der Pfad, der in der Umgebungsvariable **WHISPSKRID_CONFIG** angegeben ist, falls diese gesetzt ist.
   Wird unverändert verwendet; wird nie automatisch erstellt.
2. `config/config.yaml`, relativ zum Projektverzeichnis, wenn das Programm
   aus einem Git-Checkout ausgeführt wird (Entwicklungsmodus – aktiv, wenn `.git`
   direkt neben dem Projektstammverzeichnis existiert **und** die Datei dort vorhanden ist).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (Standard:
   `~/.config/whispskrid/config.yaml`). Wird beim ersten Ausführen automatisch erstellt, indem die Factory-Vorlage
   kopiert wird, wobei eine Meldung angezeigt wird, die den Namen der erstellten Datei enthält.
4. Die Factory-Vorlage: `/usr/share/whispskrid/config.yaml` (Debian
   Paketinstallation), andernfalls die in das
   Projekt eingebettete `config/config.yaml` (ermöglicht die Ausführung aus einem Quelltarball ohne ein `.git`
   Verzeichnis).

Die resultierende Datei kann **unvollständig** sein: Alle Schlüssel, die darin fehlen, übernehmen den Wert der Standardvorlage, wobei die Schlüssel einzeln zusammengeführt werden (verschachtelte Abschnitte werden rekursiv zusammengeführt – Sie müssen nur die Elemente wiederholen, die Sie ändern möchten, niemals den gesamten Block).

## Allgemeine Struktur von `config.yaml`

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

## Konfigurationsabschnitte im Detail

### `default_language`

Erzwingt die Sprache der Benutzeroberfläche und die Sprache der Spracherkennung. Leer
(Standardeinstellung) bedeutet: Benutzeroberfläche in der Systemsprache,
Spracherkennung mit der automatischen Sprachenerkennung von Whisper. Kann pro
Sitzung mit `-l`/`--lang` überschrieben werden.

```yaml
default_language: ""
```

### `backend`

Wählt die Spracherkennungs-Engine aus. `faster-whisper` ist der einzige akzeptierte Wert in Version 0.1.0; der Schlüssel ist für einen zukünftigen zweiten Backend-Typ (`whisper.cpp`) reserviert.

- **`name`** (String): `"faster-whisper"`, der einzige akzeptierte Wert.
- **`beam_size`** (Integer, Standardwert: `5`): Die Beam-Breite, die an `WhisperModel.transcribe()` übergeben wird. Höhere Werte können die Genauigkeit verbessern, allerdings auf Kosten der Latenz.

```yaml
backend:
  name: "faster-whisper"
  beam_size: 5
```

### `models`

Welches Whisper-Modell soll geladen werden, und wie?

- **`default`** (String, Standardwert: `"base"`): Ein kurzer Modellname (`tiny`,
  `base`, `small`, `medium`, `large-v3`, und ihre `.en` Varianten), aufgelöst
  innerhalb von `models.dir`, oder ein absoluter Pfad zu einem Modellverzeichnis.
  Kann pro Sitzung mit `--model` überschrieben werden.
- **`dir`** (String, Standardwert: leer): Das Verzeichnis für verwaltete Modelle. Leer
  bedeutet: Automatische Auflösung, in der Reihenfolge:
  `$WHISPSKRID_MODELS_DIR` (falls gesetzt) → `~/.local/share/whispskrid/whisper-models/`
  (falls es bereits ein Modell enthält) → `/usr/share/whispskrid/whisper-models/`
  (Paketinstallation) → `whisper-models/` am Root eines Git-Checkouts – die
  erste dieser Optionen, die existiert und mindestens ein Modell enthält, gewinnt.
  Wenn keine existiert, wird das Benutzerverzeichnis erstellt und als Ziel für
  `--download-model` verwendet.
- **`device`** (String, Standardwert: `"auto"`): `"cpu"`, `"cuda"`, oder `"auto"`
  (lasse `faster-whisper` entscheiden).
- **`compute_type`** (String, Standardwert: `"auto"`): `"int8"`,
  `"int8_float16"`, `"float16"`, oder `"auto"` (`int8` auf CPU, `float16` auf
  CUDA).

```yaml
models:
  default: "base"
  dir: ""
  device: "auto"
  compute_type: "auto"
```

### `capture`

- **`max_seconds`** (Integer, Standardwert: `300`): Sicherheitsgrenze. Wenn die
  Taste für die Sprachaufnahmefunktion länger als diese Anzahl von Sekunden gedrückt
  wird, stoppt die Aufnahme automatisch, die Aufnahme wird transkribiert und
  eingebracht, und es wird eine Warnmeldung protokolliert. Dies dient als
  Schutz gegen eine blockierte Taste oder einen unbegrenzten Audio-Puffer – es
  ist kein Timer für den normalen Gebrauch.

```yaml
capture:
  max_seconds: 300
```

### `audio`

Parameter für den Mikrofon-Eingangsdatenstrom, der einmal geöffnet wird, wenn die Sitzung gestartet wird, und während der Diktierungen offen bleibt.

- **`sample_rate`** (Integer, Standardwert: `16000`): muss mit der von Whisper erwarteten Rate übereinstimmen.
- **`channels`** (Integer, Standardwert: `1`): Mono.
- **`frames_per_buffer`** (Integer, Standardwert: `4096`): PortAudio-Lese-Granularität – auch die Rundungseinheit von `capture.max_seconds` und der Länge einer aufgenommenen Episode.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
```

### `vad`

Für eine zukünftige, geräuschbasierte automatische Stoppfunktion reserviert. **Nicht in
v0.1.0 implementiert**: `vad.enabled: true` protokolliert eine Warnung "noch nicht implementiert" und
das Tool verhält sich weiterhin wie ein striktes Push-to-Talk-System (der gedrückte Knopf ist das einzige Element, das eine Aufnahme startet und stoppt).

```yaml
vad:
  enabled: false
  silence_ms: 800
```

### `post_processing`

Whisper setzt automatisch Satzzeichen und Großbuchstaben; die Nachbearbeitung von WhispSkrid ist bewusst minimal gehalten.

- **`trim`** (Boolean, Standardwert: `true`): Leerzeichen am Anfang und Ende
  aus dem transkribierten Text entfernen.
- **`capitalize_sentence_start`** (Boolean, Standardwert: `true`): Erzwingt einen
  Großbuchstaben am Anfang des eingefügten Textes – Whisper lässt ihn manchmal
  bei einem kurzen Textfragment weg.

```yaml
post_processing:
  trim: true
  capitalize_sentence_start: true
```

### `hotkeys`

- **`pynput_enabled`** (boolesch, Standardwert: `true`): Startet den globalen `pynput` Listener. `pynput` überwacht den X-Server, sodass er gestartet wird, sobald einer erreichbar ist (wenn `DISPLAY` gesetzt ist), für jeden Sitzungstyp. Unter Wayland werden nur Tastenereignisse für Fenster angezeigt, die über XWayland laufen, niemals ein fokussiertes natives Wayland-Fenster. Setzen Sie diesen Wert auf `false`, um ihn niemals zu starten und das Tool nur über die Kontroll-Subbefehle zu steuern, die an Ihre Desktop-Shortcuts gebunden sind.
- **`push_to_talk`** (Liste, Standardwert: `["ctrl_r"]`): Die Taste für "Push-to-Talk".
  Gedrückt → Aufnahme; losgelassen → Transkribieren und Einfügen (in `mode: hold`, siehe unten). `pynput` unterscheidet zwischen Druck und Loslassen nativ, sodass die "Gedrückt-Halten"-Semantik auf diesem Pfad genau ist. Die Kontroll-Socket-Subbefehle (`--dictate`, `--dictate-stop`, `--toggle`) existieren für Desktops, deren Shortcutsystem "Taste gedrückt halten" nicht darstellen kann, wo sie als Start/Stopp-Umschalter fungieren.
- **`min_hold_ms`** (Integer, Millisekunden, Standardwert: `250`): Nur in `mode: hold` gilt: Wenn eine Taste losgelassen wird, bevor diese Verzögerung abgelaufen ist, wird die Aufnahme abgebrochen, anstatt transkribiert und eingefügt zu werden – ein Schutz vor einem kurzen, unbeabsichtigten Druck der gebundenen Taste (z. B. ein Desktop-Shortcut, der dieselbe Taste verwendet), der andernfalls eine Aufnahme von Hintergrundgeräuschen oder fast völliger Stille auslösen würde, was Whisper als Text interpretieren könnte. Hat außerhalb von `mode: hold` keine Auswirkung.
- **`mode`** (`hold`, `toggle` oder `armed`, Standardwert: `hold`): Was passiert, wenn die gebundene Taste gedrückt wird. `hold` ist das oben beschriebene Verhalten, das durch `min_hold_ms` geschützt wird. `toggle` startet die Aufnahme beim ersten Druck und stoppt sie, transkribiert und fügt sie beim nächsten Druck derselben Taste ein; die Freigabe der Taste bewirkt in diesem Modus nichts. `armed` aktiviert die kontinuierliche Aufnahme einer gesprochenen Phrase beim ersten Druck (siehe `wakeword` unten); ein zweiter Druck deaktiviert sie. Rein additiv: `push_to_talk` und dessen "Gedrückt-Halten"-Semantik bleiben unverändert, wenn `mode` fehlt oder auf `hold` gesetzt ist.

```yaml
hotkeys:
  pynput_enabled: true
  push_to_talk: ["ctrl_r"]
  min_hold_ms: 250
  mode: "hold"
```

### `wakeword`

Nur verwendet, wenn `hotkeys.mode` `armed`. Eine kontinuierliche Aufnahme durch Drücken einer Taste:
Eine kurze gesprochene Phrase startet ein Aufnahmefragment, eine andere beendet es und speichert
es, bis ein zweiter Tastendruck die Aufnahme stoppt.

- **`threshold`** (Gleitkommazahl 0-1, Standardwert: `0.5`): minimale Konfidenz, bevor eine
  Phrase als übereinstimmend betrachtet wird.
- **`models_dir`** (String, Standardwert: leer): Verzeichnis, das die Phrasenmodelle
  enthält (`<lang>_open.onnx` / `<lang>_close.onnx`, ein Paar pro Sprache).
  Ein leerer Wert entspricht den Standardinstallationsorten.

```yaml
wakeword:
  threshold: 0.5
  models_dir: ""
```

### `control_socket`

Boolean, Standardwert `true`. Wenn aktiviert, lauscht die laufende Sitzung an einem Unix-Socket unter `$XDG_RUNTIME_DIR/whispskrid.sock` (Modus `0600`), sodass die
Unterbefehle zur Steuerung verwendet werden können. Setzen Sie den Wert auf `false`, um den Socket vollständig zu deaktivieren.

```yaml
control_socket: true
```

### `clipboard`

Der Text wird eingefügt, indem er in die Zwischenablage kopiert und dann eine Einfügung simuliert wird.

- **`restore`** (boolean, Standardwert: `true`): Setzt den vorherigen
  Inhalt der Zwischenablage des Benutzers wieder ein, nachdem ein Einfügen
  vorgenommen wurde. Ein nicht-textbasierter Zwischenablageinhalt (z. B. ein
  Bild) wird niemals gespeichert oder überschrieben.
- **`restore_delay_ms`** (Integer, Standardwert: `400`): Die maximale Zeitspanne,
  in der das Fenster, das von der Zielanwendung zur Lese des
  Auswahlbereichs verwendet wird, aktiv bleibt, bevor die Zwischenablage
  wiederhergestellt wird. Das Warten wird abgebrochen, wenn die
  Zwischenablage bereits geändert wurde (ein anderer Prozess hat die
  Kontrolle übernommen) – in diesem Fall wird die Wiederherstellung
  abgebrochen, anstatt versucht, sie durchzusetzen.
- **`defer_restore`** (Boolean, Standardwert: `false`): Wenn `true` gesetzt
  ist, wird die Zwischenablage niemals inline wiederhergestellt; der
  ursprüngliche Inhalt – der vom Beginn der Sitzung – wird einmal am Ende
  der Sitzung (oder über `atexit` bei einem Absturz) wiederhergestellt.
  Dies beseitigt das Problem von konkurrierenden Zugriffen auf die
  Zwischenablage, das unter Wayland bei GTK-Anwendungen auftritt, jedoch
  auf Kosten der Tatsache, dass die Zwischenablage den letzten
  diktieren Textabschnitt zwischen zwei Diktier-Vorgängen innerhalb einer
  aktiven Sitzung enthält.
- **`confirm_timeout_ms`** (Integer, Standardwert: `500`): Maximale Zeit, die
  auf eine Bestätigung gewartet wird, dass die Zwischenablage tatsächlich
  den diktierten Text enthält, bevor der Einfüge-Befehl gesendet wird.

```yaml
clipboard:
  restore: true
  restore_delay_ms: 400
  defer_restore: false
  confirm_timeout_ms: 500
```

### `injection`

Das Backend für die Tastensteuerung wird einmalig beim Start durch direkte Abfrage ausgewählt —
es wird nie vor jeder Einfügung erneut getestet. Die Reihenfolge ist: **`ydotool`** (wenn die
Binärdatei vorhanden ist und ihr Daemon antwortet) → **`xdotool`** (wenn die Binärdatei
vorhanden ist) → eingeschränkter Modus (Text bleibt in der Zwischenablage, keine Tastensteuerung wird gesendet).
Weitere Informationen, warum **`wtype`** absichtlich nicht Teil dieser Reihenfolge ist, finden Sie in den Kompatibilitätsnotizen des Projekts für Wayland.

- **`paste_combo`** (String, Standardwert: `ctrl+v`) und
  **`terminal_paste_combo`** (Standardwert: `ctrl+shift+v`): Die Tastenkombination,
  die zum Einfügen verwendet wird. Die Erkennung von Fenstertypen (um die
  Tastenkombination automatisch auszuwählen) ist nur im `xdotool` Pfad verfügbar.
  `ydotool` injiziert auf der `/dev/uinput` Ebene und kennt keine bestimmte
  Zielanwendung, daher wird `paste_combo` immer verwendet, es sei denn, Sie überschreiben es.
- **`terminal_window_classes`** (Liste): Fenstertypen, die als Terminals behandelt werden (nur im `xdotool` Pfad).
- **`ydotool_keycodes`** (Zuordnung): Physische Linux-Tastencodes, die nur im
  `ydotool` Pfad verwendet werden, der rohe Tastencodes anstelle von
  Keysyms sendet. Überschreiben Sie diese bei einem Nicht-QWERTY-Layout.

```yaml
injection:
  paste_combo: "ctrl+v"
  terminal_paste_combo: "ctrl+shift+v"
  terminal_window_classes: ["konsole", "gnome-terminal-server", "xterm", "st", "alacritty", "kitty", "foot"]
  ydotool_keycodes: {}
```

### `sound_file`

Absoluter Pfad zu einer kurzen Sounddatei für eine Benachrichtigung (z. B. `.oga`, `.wav`),
die über `paplay` abgespielt wird, um den Beginn einer Aufnahme zu bestätigen. Ein leerer oder fehlender `paplay` deaktiviert den Ton ohne Meldung.

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

Farbschema für die Konsole. Die Werte müssen gültige `colorama` Farbnamen sein (z.B. `GREEN`, `RED`, `BLUE`, `RESET`}).

- **`ready_message`**: Farbe des "Bereit"-Hinweisbanners.
- **`help_text`**, **`help_title`**: Farben der Hilfenachricht.
- **`info`**, **`success`**, **`warning`**, **`error`**: Farben der Statusmeldung.

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
