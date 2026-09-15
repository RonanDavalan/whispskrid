% WHISPSKRID(1) whispskrid | Benutzerbefehle
% Ronan Davalan
% 2026-09-11

# NAME

whispskrid – Offline-Sprachsteuerung für die Kommandozeile, systemweit verfügbar.

# ZUSAMMENFASSUNG

**whispskrid** [**-l** *LANG* | **--lang** *LANG*] [**--model** *NAME*]

**whispskrid** **\--diagnose**

**whispskrid** **\--download-model** [*NAME*]

**whispskrid** {**\--dictate** | **\--dictate-stop** | **\--toggle** | **\--cancel** | **\--status** | **\--stop**}

**whispskrid** **\--version**

# BESCHREIBUNG

**whispskrid** ist ein Befehlszeilen-Diktierwerkzeug für Linux, das von der
offline-Spracherkennungsengine (**faster-whisper**) angetrieben wird. Die Aufnahme
erfolgt ausschließlich im "Push-to-Talk"-Modus: Audio wird nur aufgezeichnet, während
eine Taste gedrückt gehalten wird (oder, äquivalent dazu, zwischen einem **\--dictate**- und einem **\--dictate-stop**-Befehl), und
der erkannte Text wird direkt in das aktuell fokussierte Fenster eingefügt – Terminal, Browser, Editor oder jede andere Anwendung –,
sodass es systemweit funktioniert und nicht nur innerhalb eines einzelnen Programms.

Die gesamte Spracherkennung läuft lokal: Audio- oder transkribierter Text werden niemals an einen externen Dienst gesendet.

Es läuft jeweils nur eine Sitzung pro Benutzer gleichzeitig. Wird sie ohne Kontrollflag gestartet, beginnt sie eine residente Sitzung: Sie lädt das Modell, öffnet eine private Unix-Kontroll-Socket unter `$XDG_RUNTIME_DIR/whispskrid.sock` (Modus `0600`) und startet einen `pynput` Hotkey-Listener, falls aktiviert. Derselbe Befehl, der mit einem Kontrollflag aufgerufen wird (siehe "EINE LAUFENDE SITZUNG STEUERN"), verbindet sich mit dieser Socket anstatt eine neue Sitzung zu starten.

Text wird injiziert, indem er in die Zwischenablage kopiert und dann eingefügt wird, sodass
zwei Arten von Tools benötigt werden: ein Tastendrucksimulator und ein Tool für die Zwischenablage.
Unter Wayland sind dies **ydotool** (benötigt den `ydotoold` Daemon und Zugriff auf `/dev/uinput`) sowie **wl-clipboard»; unter X11 sind es **xdotool** und **xclip**. Ohne eines dieser Backends greift die Injektion auf einen eingeschränkten Modus zurück.
Die Wahl zwischen den beiden Optionen wird einmalig beim Startvorgang getroffen, indem geprüft wird, welche Binärdatei und welcher Daemon tatsächlich antworten – nicht indem der Sitzungstyp direkt überprüft wird. **whispskrid \--diagnose** gibt aus, welche Tools, Audiogeräte und Zwischenablagefunktionen verfügbar sind, und beendet dann das Programm.

# INSTALLATION

Installieren Sie das Debian-Paket:

```
sudo dpkg -i whispskrid_<version>_all.deb
```

Der `postinst`-Schritt installiert **faster-whisper** über pip und meldet seinen eigenen
Fortschritt; die Paket-Dateien `Recommends` enthalten das Backend für die Texteingabe, das für Ihren
Session-Typ verwendet wird (**ydotool** + **wl-clipboard** unter Wayland, **xdotool** +
**xclip** unter X11) – keines davon ist eine harte Abhängigkeit, sodass eine unvollständige
Umgebung weiterhin installiert wird, jedoch mit einem eingeschränkten Eingabemodus (siehe
**\--diagnose** unten).

Kein Whisper-Modell wird mit dem Paket geliefert. Laden Sie eines herunter, bevor Sie es zum ersten Mal verwenden –
die Modelle stammen aus den offiziellen CTranslate2-Konvertierungen auf Hugging Face
(*https://huggingface.co/Systran*), und werden automatisch in das verwaltete
Modellverzeichnis heruntergeladen (siehe DATEIEN unten):

```
whispskrid --download-model
```

Das Überspringen dieses Schritts ist nicht kritisch: Die lokale Sitzung lädt das Standardmodell beim ersten Start selbst herunter und gibt dies zuerst bekannt, da der eigene Download von Hugging Face keinen Fortschrittsbalken anzeigt (ein Datentransfer von mehreren hundert MB ohne sichtbare Aktivität).

Verifiziere die Umgebung:

```
whispskrid --diagnose
```

Globale Hotkeys über `pynput` durch Beobachtung des X-Servers: Unter Wayland erreichen sie nur
Fenster, die über XWayland laufen, niemals ein aktives, natives Wayland-Fenster.
Binden Sie die Unterbefehle für die Steuerung an die eigenen Tastenkombinationseinstellungen Ihres Desktops, um
eine Steuerung zu erhalten, die überall funktioniert.

# OPTIONEN

**-l** *LANG*, **\--lang** *LANG*
:   Erzwingt die Schnittstellen- und Spracherkennungsprache für diese Sitzung
    (`en`, `fr`, `de` oder `es`), wobei die Einstellung `default_language` aus der
    Konfigurationsdatei außer Kraft gesetzt wird.  Wählt außerdem die Sprache der
    eigenen Nachrichten der Befehlszeilenschnittstelle aus (einschließlich Hilfetext).

**\--model** *NAME*
:   Überschreibt `models.default` aus der Konfigurationsdatei für diese Sitzung –
    ein kurzer Name eines Modells (eines von `tiny`, `base`, `small`, `medium`,
    `large-v3`, oder deren `.en` Varianten – siehe **\--download-model** unten)
    oder ein Dateipfad.

**\--diagnose**
:   Überprüfen Sie die Umgebung (Sitzungstyp, Injektions-Backend, Tools, GPU/CUDA,
    Vorhandensein des Modells, Audioeingabe, Zwischenablage, Steuersocket, Konfiguration)
    und beenden Sie das Programm. Der Exit-Status ist `0` wenn alle
    prüfenden Bedingungen erfüllt sind; einige Prüfungen (GPU-Beschleunigung,
    Vorhandensein von `ydotool`/`xdotool` werden einzeln betrachtet) sind nur
    informativ und beeinflussen den Exit-Status niemals.

**\--download-model** [*NAME*]
:   Laden Sie ein Whisper-Modell (`base` wenn *NAME* weggelassen wird; eines von `tiny`,
    `base`, `small`, `medium`, `large-v3`, oder deren `.en` Varianten) von
    Hugging Face in das verwaltete Modelldirzeichnis
    (`~/.local/share/whispskrid/whisper-models/` standardmäßig – siehe FILES),
    und beenden Sie dann das Programm. Bereits heruntergeladene Modelle werden erkannt und übersprungen.

**\--version**
:   Geben Sie die Versionsnummer aus und beenden Sie das Programm.

# DIE STEUERUNG EINER LAUFENDEN SITZUNG

Jede der folgenden Optionen verbindet sich mit dem Socket der laufenden Sitzung, führt die Aktion aus, gibt die resultierende Antwort (`OK`, `OK <text>` oder `ERR <reason>` ) aus und beendet sich mit dem Status `0` bei `OK`, `1` andernfalls. Sie sollen an Desktop-Tastenkombinationen gebunden werden.

**\--dictate**
:   Erfassen starten. Schlägt mit `ERR already-capturing` fehl, wenn bereits eine Erfassung
    läuft.

**\--dictate-stop**
:   Die aktuelle Aufnahme stoppen, transkribieren und das Ergebnis einfügen. Fehlgeschlagen, wenn keine Aufnahme läuft (Fehler `ERR not-capturing`).

**\--toggle**
:   **\--dictate** oder **\--dictate-stop**, abhängig vom aktuellen Zustand der Sitzung – eine einzelne Verknüpfung für eine Taste, die gedrückt werden muss, um zu starten/stoppen, bzw. für eine "Push-to-Talk"-Funktion, die auf Desktop-Ebene zugewiesen ist.

**\--cancel**
:   Die laufende Aufnahme ohne Transkription oder Injektion von etwas beenden.

**\--status**
:   Gibt den aktuellen Sitzungsstatus (`state=idle|capturing model=<name>
    language=<lang|auto>`) aus, ohne ihn zu ändern.

**\--stop**
:   Die aktive Sitzung des Benutzers sauber beenden.

# TASTENBELEGUNGEN

`pynput` Globale Hotkeys werden aktiviert, wenn `hotkeys.pynput_enabled` in der Konfigurationsdatei auf "true" gesetzt ist und ein Display-Server erreichbar ist
(`DISPLAY` Einstellung) – für alle Sitzungstypen, einschließlich Wayland, da `pynput` selbst den X-Server überwacht. Der Listener verbraucht das Tastaturereignis nicht: der Tastendruck erreicht auch das aktive Fenster. Die Werkseinstellung bindet "Push-to-Talk" an:

**Rechte Strg-Taste**
:   Gedrückt halten zum Aufnehmen, loslassen zum Stoppen. Transkribieren und injizieren – die native
    "drücken/loslassen"-Semantik von `pynput` implementiert Push-to-Talk direkt
    auf diesem Pfad (im Gegensatz zum Control-Socket-Pfad oben, der nur
    diskrete Befehle empfängt und daher **--toggle** anstelle dessen bereitstellen muss).

Die gebundenen Taste(n) können unter `hotkeys.push_to_talk` in der
Konfigurationsdatei konfiguriert werden. Jeder Name unten bezeichnet eine
physische Taste – niemals eine Tastenkombination – und nur eine einzelne
physische Taste kann für die Push-to-Talk-Funktion verwendet werden: `ctrl_r`
(rechte Strg-Taste), `ctrl_l` (linke Strg-Taste), `alt_r` (rechte Alt-Taste),
`alt_l` (linke Alt-Taste), `shift_r` (rechte Umschalttaste), `shift_l` (linke
Umschalttaste), `cmd`.

`hotkeys.min_hold_ms` (Millisekunden, Standardwert: `250`) gilt nur für `mode: hold`:
Ein vor dieser Verzögerung veröffentlichtes Protokoll bricht die Aufnahme ab anstelle der
Transkription und Einfügung – ein Schutz vor einem kurzen, unbeabsichtigten Druck auf
die zugewiesene Taste (z. B. eine Desktop-Tastenkombination, die dieselbe Taste verwendet),
der andernfalls Hintergrundgeräusche oder fast vollständige Stille erfassen würde, was Whisper
in zufälligen Text umwandeln könnte.

`hotkeys.mode` (`hold`, der Standardwert, `toggle`, oder `armed`) steuert, was passiert,
wenn die zugeordnete Taste gedrückt wird. `hold` ist das oben beschriebene Verhalten,
das durch `hotkeys.min_hold_ms` geschützt ist. `toggle` startet die Aufnahme beim ersten
Drücken und stoppt, transkribiert und fügt den Text beim nächsten Drücken der
gleichen Taste ein; das Loslassen der Taste hat in diesem Modus keine Wirkung –
nützlich, um das Halten einer Taste während einer langen Diktierphase zu vermeiden.
`armed` aktiviert die kontinuierliche Aufnahme für eine gesprochene Phrase beim ersten
Drücken – eine kurze Phrase öffnet ein Aufnahme-Segment, eine weitere schließt
und fügt es ein, bis ein zweites Drücken die Aufnahme deaktiviert; siehe die
`wakeword` Taste in **configuration.md** (KONFIGURATION weiter unten).

Um die gebundenen Schlüssel oder den Modus zu ändern, bearbeiten Sie `hotkeys.push_to_talk` /
`hotkeys.mode` in der Konfigurationsdatei (siehe unten unter "CONFIGURATION" für
den genauen Pfad), und starten Sie dann die aktive Sitzung neu, damit die
Änderung wirksam wird:

```
whispskrid --stop
whispskrid
```

Um **\--toggle** an eine Desktop-Ebene-Verknüpfung zu binden – die einzige Option unter Wayland für Fenster, die nicht über XWayland laufen, was `pynput` nicht erreichen kann – bieten die meisten Desktop-Umgebungen eine Einstellung für benutzerdefinierte Verknüpfungen. Unter GNOME: *Einstellungen → Tastatur → Verknüpfungen anzeigen und anpassen → Benutzerdefinierte Verknüpfungen → Verknüpfung hinzufügen*, wobei `whispskrid --toggle` der Befehl ist und die von Ihnen gewählte Tastenkombination. KDE Plasma bietet die entsprechende Einstellung unter *Systemeinstellungen → Tastaturbelegungen → Benutzerdefinierte Tastaturbelegungen*.

# KONFIGURATION

Das Laufzeitverhalten wird durch eine YAML-Konfigurationsdatei gesteuert: Standardeinstellungen für Sprache, Backend und Modellparameter, Dauerbeschränkung für die Aufnahme, Audio-Gerät, Nachbearbeitung und Hotkeys.

Die Konfigurationsdatei wird anhand der ersten passenden Regel gefunden; sobald eine Regel zutrifft, werden die übrigen Regeln nicht mehr berücksichtigt.

1. Der Pfad, der in der Umgebungsvariablen **WHISPSKRID_CONFIG** angegeben ist, falls diese gesetzt wurde.
   Wird unverändert verwendet; wird niemals automatisch erstellt.
2. `config/config.yaml`, relativ zum Projektverzeichnis, wenn die Ausführung
   von einem Git-Checkout (Entwicklungsmodus) erfolgt.
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (Standard:
   `~/.config/whispskrid/config.yaml`). Wird beim ersten Ausführen automatisch erstellt,
   aus der Vorlage.
4. Die Vorlage: `/usr/share/whispskrid/config.yaml` (Debian-Paket
   Installation), andernfalls die `config/config.yaml` im Projekt
   eingebettet (deckt die Ausführung von einem Quell-Tarball ohne ein `.git` Verzeichnis ab).

Die resultierende Datei kann unvollständig sein: Alle Schlüssel, die darin fehlen, übernehmen den Standardwert aus der Vorlage, wobei die Werte schlüssel für schlüssel zusammengeführt werden.

Die aktive Sprache wird in folgender Reihenfolge ausgewählt: zunächst die **\--lang**-Option, falls angegeben;
ansonsten `default_language` aus der Konfigurationsdatei; andernfalls
wird die Sprache automatisch vom Erkennungsmodul erkannt.

Siehe **configuration.md** in der Projektdokumentation für die vollständige Referenz
aller Konfigurationsschlüssel.

# FEHLERSUCHE

**Modell nicht gefunden.** Führen Sie **--diagnose** aus und lesen Sie die abschließende Zusammenfassung,
die den ersten Blocking-Check selbst benennt – erraten Sie nicht anhand der
rohen Ausgabe oben:

```
whispskrid --diagnose
```

Wenn die Zusammenfassung einen Modellcheck nennt, laden Sie einen herunter:

```
whispskrid --download-model
```

Führen Sie dann **--diagnose** erneut aus; es beendet `0` jedes Mal, wenn eine Blockierungsprüfung erfolgreich ist
(siehe EXIT STATUS).

# DATEIEN

`~/.config/whispskrid/config.yaml`
:   Konfigurationsdatei für jeden Benutzer.

`/usr/share/whispskrid/config.yaml`
:   Konfigurationsvorlage für die Fabrik (Installation des Debian-Pakets), schreibgeschützt.

`~/.local/share/whispskrid/whisper-models/`
:   Standardmäßiges Verzeichnis für heruntergeladene Whisper-Modelle.

`config/config.yaml`
:   Konfigurationsdatei, die verwendet wird, wenn von einem Git-Checkout ausgeführt wird.

`whisper-models/`
:   Standard-Suchpfad für Whisper-Modelle, wenn das Programm von einer Git-Version oder einer Quellcode-Datei ausgeführt wird.

`$XDG_RUNTIME_DIR/whispskrid.sock`
:   Steuerungssocket der laufenden Sitzung (Modus `0600`).

# RÜCKGABEWERT

Das Programm wurde sauber beendet, oder ein Steuerbefehl wurde empfangen `OK`.

Nicht Null
:   Start fehlgeschlagen (kein Injektions-Backend, Modell oder Audiogerät verfügbar),
    oder ein Steuerbefehl empfangen `ERR`.

# BEISPIELE

Starte eine Sitzung für einen Benutzer mit der Standardeinstellung für die Sprache, die in der Konfigurationsdatei definiert ist:

```
whispskrid
```

Gerne.

```
whispskrid --lang en
```

Verknüpfen Sie Desktop-Verknüpfungen für Push-to-Talk, ohne sich auf `pynput` verlassen zu müssen:

```
whispskrid --dictate
whispskrid --dictate-stop
```

SIEHE AUCH

faster-whisper: *https://github.com/SYSTRAN/faster-whisper*

Whisper-Modellkatalog: *https://huggingface.co/Systran*

Projekt-Homepage: *https://whispskrid.davalan.fr/*

# FEHLER

Melden Sie Fehler im Fehlerverfolgungssystem des Projekts:
*https://github.com/RonanDavalan/whispskrid/issues*

# AUTOR

Ronan Davalan und die in CONTRIBUTORS.md aufgeführten Mitwirkenden.
