% WHISPSKRID(1) whispskrid | Benutzerbefehle
% Ronan Davalan
% 2026-09-11

# NAME

whispskrid – Offline-Diktierfunktion für die Kommandozeile, systemweit aktivierbar.

# ZUSAMMENFASSUNG

**whispskrid** [**-l** *LANG* | **--lang** *LANG*] [**--model** *NAME*]

**whispskrid** **\--diagnose**

**whispskrid** **\--download-model** [*NAME*]

**whispskrid** {**\--dictate** | **\--dictate-stop** | **\--toggle** | **\--cancel** | **\--status** | **\--stop**}

**whispskrid** **\--version**

# BESCHREIBUNG

**whispskrid** ist ein Kommandozeilen-Diktierwerkzeug für Linux, das von der
Offline-Spracherkennungsengine **faster-whisper** angetrieben wird. Die Aufnahme
erfolgt ausschließlich im "Push-to-Talk"-Modus: Audio wird nur aufgezeichnet,
während eine Taste gedrückt gehalten wird (oder, äquivalent dazu, zwischen einem
**\--dictate** und einem **\--dictate-stop** Befehl), und der erkannte Text wird direkt in
das aktuell aktive Fenster eingefügt – Terminal, Browser, Editor oder jede andere
Anwendung –, sodass es systemweit und nicht nur innerhalb eines einzelnen Programms
funktioniert.

Die gesamte Spracherkennung läuft lokal ab: weder Audio noch transkribierter Text werden jemals an einen externen Dienst gesendet.

Nur eine Sitzung läuft gleichzeitig pro Benutzer. Wenn sie ohne ein Steuerungsflag gestartet wird,
beginnt sie eine residente Sitzung: sie lädt das Modell, öffnet eine private Unix-Steuersocket unter `$XDG_RUNTIME_DIR/whispskrid.sock` (Modus `0600`), und startet einen
`pynput` Hotkey-Listener, falls aktiviert. Derselbe Befehl, der mit einem Steuerungsflag aufgerufen wird (siehe STEUERUNG EINER LAUFENDE SITZUNG), verbindet sich mit dieser Socket anstatt eine neue Sitzung zu starten.

Text wird injiziert, indem er in die Zwischenablage kopiert und dann eingefügt wird, sodass
zwei Arten von Tools benötigt werden: ein Tastenfolge-Simulator und ein Zwischenablage-Tool.
Unter Wayland sind dies **ydotool** (benötigt den `ydotoold` Daemon und Zugriff auf `/dev/uinput`) sowie **wl-clipboard**; unter X11 sind es **xdotool** sowie **xclip**. Ohne eines dieser Backends greift die Injektion auf einen eingeschränkten Modus zurück. Die Wahl zwischen beiden erfolgt einmalig beim Start durch direktes Prüfen, welches der beiden Programme und sein Dienst tatsächlich antwortet – nicht durch eine direkte Prüfung der Sitzungsart.
**whispskrid \--diagnose** zeigt, welche Tools, Audiogeräte und Zwischenablagezugriffe verfügbar sind, und beendet dann das Programm.

# INSTALLATION

Installieren Sie das Debian-Paket:

```
sudo dpkg -i whispskrid_<version>_all.deb
```

Der postinst-Schritt installiert **faster-whisper** per pip und meldet
dabei seinen eigenen Fortschritt; die `Recommends` des Pakets decken das
zur Sitzungsart passende Injection-Backend ab (**ydotool** +
**wl-clipboard** unter Wayland, **xdotool** + **xclip** unter X11) – keines
davon ist eine feste Abhängigkeit, eine unvollständige Umgebung wird also
trotzdem installiert, allerdings mit eingeschränktem Injection-Modus
(siehe **\--diagnose** unten).

Das Paket enthält kein Whisper-Modell. Laden Sie vor der ersten Nutzung
eines herunter — die Modelle stammen aus den offiziellen
CTranslate2-Konvertierungen auf Hugging Face
(*https://huggingface.co/Systran*) und werden automatisch in das
verwaltete Modellverzeichnis geladen (siehe DATEIEN unten):

```
whispskrid --download-model
```

Dieser Schritt ist nicht zwingend: Die residente Sitzung lädt das
Standardmodell beim ersten Start selbst herunter und kündigt dies vorher
an — der Download über Hugging Face zeigt keinen Fortschrittsbalken, ein
Transfer von mehreren hundert MB wäre sonst ohne jede sichtbare Aktivität.

Überprüfen Sie anschließend die Umgebung:

```
whispskrid --diagnose
```

Globale Hotkeys über `pynput` durch Beobachtung des X-Servers: Unter Wayland erreichen sie nur
Fenster, die über XWayland laufen, niemals ein direkt unter Wayland ausgeführtes Fenster.
Binden Sie die Unterbefehle für die Steuerung an die eigenen Tastenkombinationseinstellungen Ihres Desktops,
um eine Steuerung zu erhalten, die überall funktioniert.

# OPTIONEN

**-l** *LANG*, **--lang** *LANG*
:   Erzwingt die Schnittstellen- und Spracherkennungssprache für diese Sitzung
    (`en`, `fr`, `de` oder `es`), wobei die Einstellung in der
    Konfigurationsdatei (`default_language`) überschrieben wird.  Wählt außerdem die Sprache
    der eigenen Nachrichten der Kommandozeilenschnittstelle aus (einschließlich der
    Hilfetexte).

**\--model** *NAME*
:   Überschreibt `models.default` aus der Konfigurationsdatei für diese Sitzung –
    ein kurzer Modellname (`tiny`, `base`, `small`, `medium`, `large-v3`
    oder deren `.en`-Varianten — siehe **\--download-model** unten) oder
    ein Pfad im Dateisystem.

**\--diagnose**
:   Überprüfen Sie die Umgebung (Sitzungstyp, Injection-Backend, Tools, GPU/CUDA,
    Vorhandensein des Modells, Audioeingang, Zwischenablage, Steuersocket, Konfiguration)
    und beenden Sie das Programm. Der Exit-Status ist `0` wenn alle Prüfungen erfolgreich sind; einige
    Prüfungen (GPU-Beschleunigung, `ydotool`/`xdotool` Vorhandensein, jeweils einzeln) sind nur informativ und beeinflussen den Exit-Status nicht.

**\--download-model** [*NAME*]
:   Laden Sie ein Whisper-Modell herunter (`base`, wenn *NAME* weggelassen
    wird; eines von `tiny`, `base`, `small`, `medium`, `large-v3` oder
    deren `.en`-Varianten) von Hugging Face in das verwaltete
    Modellverzeichnis (standardmäßig
    `~/.local/share/whispskrid/whisper-models/` — siehe DATEIEN) und
    beenden Sie dann das Programm. Ein bereits vorhandenes Modell wird
    erkannt und der Vorgang übersprungen.

**\--version**
:   Die Versionsnummer ausgeben und beenden.

# STEUERUNG EINER LAUFENDE SESSION

Jede der folgenden Optionen verbindet sich mit dem Socket der laufenden Sitzung,
führt die Aktion aus, gibt die resultierende Antwort (`OK`, `OK <text>` oder
`ERR <reason>`) aus und beendet sich mit dem Status `0` bei `OK`, andernfalls mit `1`. Sie sollen
an Desktop-Tastenkombinationen gebunden werden.

**\--dictate**
:   Start der Aufnahme. Schlägt mit `ERR already-capturing` fehl, wenn bereits eine Aufnahme läuft.

**\--dictate-stop**
:   Stoppe die aktuelle Aufnahme, transkribiere sie und füge das Ergebnis ein. Gibt `ERR not-capturing` zurück, wenn keine Aufnahme läuft.

**\--toggle**
:   **\--dictate** oder **\--dictate-stop**, abhängig vom aktuellen Zustand der Sitzung – eine einzelne Verknüpfung für eine "Drücken zum Starten / Drücken zum Stoppen"-Taste, die auf Desktop-Ebene zugewiesen ist.

**\--cancel**
:   Die laufende Aufnahme ohne Transkription oder Injektion von
    Inhalten abbrechen.

**\--status**
:   Gibt den aktuellen Sitzungsstatus (`state=idle|capturing model=<name>
    language=<lang|auto>`) aus, ohne ihn zu ändern.

**\--stop**
:   Schließen Sie die aktive Benutzersitzung sauber.

## HOTKEYS

`pynput` Globale Hotkeys werden aktiviert, wenn `hotkeys.pynput_enabled` in der Konfigurationsdatei
auf "true" steht und ein Anzeigeserver erreichbar ist (`DISPLAY` gesetzt) –
unabhängig von der Sitzungsart, Wayland eingeschlossen, da `pynput` selbst
den X-Server beobachtet. Der Listener verbraucht das Tastaturereignis nicht: der Tastendruck
erreicht auch das aktive Fenster. Die Factory-Konfiguration bindet "Push-to-Talk" an:

**Rechte Strg-Taste**
:   Gedrückt halten zum Aufnehmen, loslassen zum Stoppen. Transkribiert und injiziert — die nativen
    "drücken/loslassen"-Funktionen von `pynput` implementieren "Push-to-Talk" direkt
    auf diesem Pfad (im Gegensatz zum "Control-Socket"-Pfad oben, der nur
    diskrete Befehle empfängt und daher **--toggle** anstelle dessen bereitstellen muss).

Die gebundenen Tasten sind unter `hotkeys.push_to_talk` in der
Konfigurationsdatei einstellbar. Jeder Name bezeichnet eine einzelne
physische Taste — niemals eine Tastenkombination — und nur eine einzige
physische Taste kann für Push-to-Talk gebunden werden: `ctrl_r` (rechte
Strg-Taste), `ctrl_l` (linke Strg-Taste), `alt_r` (rechte Alt-Taste),
`alt_l` (linke Alt-Taste), `shift_r` (rechte Umschalttaste), `shift_l`
(linke Umschalttaste), `cmd`.

`hotkeys.mode` (`hold`, Standardwert, oder `toggle`) legt fest, was ein
Druck auf die gebundene Taste bewirkt. `hold` entspricht dem oben
beschriebenen Verhalten: gedrückt halten = Aufnahme, loslassen = Stopp,
Transkription und Injektion. `toggle` startet die Aufnahme beim ersten
Tastendruck und stoppt, transkribiert und injiziert beim nächsten Druck
derselben Taste; das Loslassen bewirkt in diesem Modus nichts — nützlich,
um bei einem langen Diktat nicht dauerhaft eine Taste gedrückt halten zu
müssen.

Um die gebundene(n) Taste(n) oder den Modus zu ändern, bearbeiten Sie
`hotkeys.push_to_talk` / `hotkeys.mode` in der Konfigurationsdatei (siehe
KONFIGURATION unten für den genauen Pfad) und starten Sie die residente
Sitzung neu, damit die Änderung wirksam wird:

```
whispskrid --stop
whispskrid
```

Um **\--toggle** stattdessen an eine Desktop-Tastenkombination zu binden
— unter Wayland die einzige Möglichkeit für Fenster, die nicht über
XWayland laufen und die `pynput` deshalb nicht erreichen kann — bieten
die meisten Desktop-Umgebungen eine Einstellung für benutzerdefinierte
Tastenkombinationen. Unter GNOME: *Einstellungen → Tastatur →
Tastenkombinationen anzeigen und anpassen → Eigene Tastenkombinationen →
Tastenkombination hinzufügen*, mit `whispskrid --toggle` als Befehl und
der gewünschten Tastenkombination. KDE Plasma bietet das Äquivalent unter
*Systemeinstellungen → Kurzbefehle → Eigene Kurzbefehle*.

# KONFIGURATION

Das Laufzeitverhalten wird durch eine YAML-Konfigurationsdatei gesteuert: Standardeinstellungen für Sprache, Backend und Modellparameter, Dauerbegrenzung, Audioeingabegerät, Nachbearbeitung und Hotkeys.

Die Konfigurationsdatei wird anhand der ersten passenden Regel gefunden; sobald eine Regel übereinstimmt, werden die restlichen Regeln nicht mehr berücksichtigt.

1. Der Pfad, der in der Umgebungsvariablen **WHISPSKRID_CONFIG** angegeben ist, falls diese gesetzt ist.
   Wird unverändert verwendet; wird nie automatisch erstellt.
2. `config/config.yaml`, relativ zum Projektverzeichnis, wenn die Ausführung
   von einem Git-Checkout (Entwicklungsmodus) erfolgt.
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (Standard,
   `~/.config/whispskrid/config.yaml`). Wird beim ersten Ausführen automatisch erstellt,
   aus der Vorlage.
4. Die Vorlage: `/usr/share/whispskrid/config.yaml` (Debian-Paketinstallation), andernfalls die `config/config.yaml` im Projekt
   eingebettet (gilt für die Ausführung von einem Quell-Tarball ohne ein `.git` Verzeichnis).

Die resultierende Datei kann unvollständig sein: Alle Schlüssel, die darin fehlen, übernehmen den Standardwert aus der Werkseitvorlage, wobei die Werte schrittweise zusammengeführt werden.

Die aktive Sprache wird in folgender Reihenfolge ausgewählt: zuerst die **--lang** Option, falls diese angegeben ist;
ansonsten `default_language` aus der Konfigurationsdatei; andernfalls
automatische Erkennung durch das Erkennungsmodul.

Siehe **configuration.md** in der Projektdokumentation für die vollständige Referenz
aller Konfigurationsschlüssel.

# FEHLERBEHEBUNG

**Modell nicht gefunden.** Führen Sie **\--diagnose** aus und lesen Sie die
abschließende Zusammenfassungszeile, die selbst die erste blockierende
Prüfung benennt – raten Sie nicht anhand der rohen Ausgabe darüber:

```
whispskrid --diagnose
```

Wenn die Zusammenfassungszeile die Modellprüfung benennt, laden Sie ein
Modell herunter:

```
whispskrid --download-model
```

Führen Sie anschließend **\--diagnose** erneut aus; es beendet sich mit
Status `0`, sobald alle blockierenden Prüfungen erfolgreich sind (siehe
BEENDIGUNGSSTATUS).

# DATEIEN

`~/.config/whispskrid/config.yaml`
:   Konfigurationsdatei pro Benutzer.

`/usr/share/whispskrid/config.yaml`
:   Konfigurationsvorlage für die Fabrik (Installation des Debian-Pakets), schreibgeschützt.

`~/.local/share/whispskrid/whisper-models/`
:   Standardmäßiges Verzeichnis für heruntergeladene Whisper-Modelle.

`config/config.yaml`
:   Konfigurationsdatei, die verwendet wird, wenn die Ausführung von einem Git-Checkout erfolgt.

`whisper-models/`
:   Standard-Suchpfad für Whisper-Modelle, wenn das Programm von einem Git-Repository oder einer Quellcode-Datei gestartet wird.

`$XDG_RUNTIME_DIR/whispskrid.sock`
:   Steuerungssocket der laufenden Sitzung (Modus `0600`).

# BEENDIGUNGSSTATUS

**0**
:   Das Programm wurde sauber beendet, oder ein Steuerbefehl wurde empfangen `OK`.

Nicht Null
:   Startvorgang fehlgeschlagen (kein Injektions-Backend, Modell oder Audio-Gerät verfügbar),
    oder ein Steuerbefehl empfangen `ERR`.

# BEISPIELE

Starte eine Sitzung für Benutzer mit der Standardeinstellung für die Sprache, die in der Konfigurationsdatei angegeben ist:

```
whispskrid
```

Englisch für diese Sitzung erzwingen:

```
whispskrid --lang en
```

Verknüpfen Sie Desktop-Verknüpfungen für die Push-to-Talk-Funktion, ohne sich auf `pynput` verlassen zu müssen:

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
