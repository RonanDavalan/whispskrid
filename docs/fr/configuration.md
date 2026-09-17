Guide de configuration du projet.

Ce document explique toutes les options disponibles dans `config.yaml`. Configurer correctement ce fichier vous permet d'adapter WhispSkrid à votre matériel, à votre langue et à votre environnement de bureau.

Comment le fichier de configuration est-il localisé ?

Le fichier est localisé selon la première règle correspondante ci-dessous ; une fois qu'une règle est trouvée, les règles restantes ne sont pas consultées.

1. Le chemin spécifié dans la variable d'environnement **WHISPSKRID_CONFIG**, si elle est définie.
   Utilisé tel quel ; jamais créé automatiquement.
2. `config/config.yaml`, relatif au répertoire du projet, lors de l'exécution
   à partir d'un dépôt Git (mode développement — activé lorsque `.git` existe
   à côté de la racine du projet **et** que le fichier existe à cet emplacement).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (par défaut
   `~/.config/whispskrid/config.yaml`). Créé automatiquement lors de la première exécution
   en copiant le modèle de configuration, avec un message indiquant le nom du fichier créé.
4. Le modèle de configuration : `/usr/share/whispskrid/config.yaml` (installation du paquet Debian), sinon le `config/config.yaml`
   intégré au projet (couvre l'exécution à partir d'une archive source sans un répertoire `.git`).

Le fichier résolu peut être **partiel** : toute clé qui lui manque prend la valeur du modèle par défaut, et les clés sont fusionnées une par une (les sections imbriquées sont fusionnées de manière récursive : vous n'avez besoin de répéter que les éléments que vous souhaitez modifier, et non l'ensemble du bloc).

## Structure générale de `config.yaml`

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

Sections de configuration détaillées.

### `default_language`

Force la langue de l'interface et la langue de la reconnaissance vocale. Une valeur vide
(par défaut) signifie : interface dans la langue du système, reconnaissance vocale avec la détection automatique de la langue de Whisper. Peut être redéfini par session avec `-l`/`--lang`.

```yaml
default_language: ""
```

### `backend`

Sélectionne le moteur de reconnaissance vocale. `faster-whisper` est la seule valeur acceptée dans la version 1.0.0 ; la clé est réservée pour un deuxième backend futur (`whisper.cpp`).

- **`name`** (chaîne de caractères) : `"faster-whisper"`, la seule valeur acceptée.
- **`beam_size`** (entier, valeur par défaut `5`) : largeur du faisceau passée à `WhisperModel.transcribe()`. Des valeurs plus élevées peuvent améliorer la précision, mais au prix d'une latence accrue.

```yaml
backend:
  name: "faster-whisper"
  beam_size: 5
```

### `models`

Quel modèle Whisper charger, et comment.

- **`default`** (chaîne de caractères, valeur par défaut `"base"`): un nom de modèle court (`tiny`,
  `base`, `small`, `medium`, `large-v3`, et leurs variantes `.en`), résolu
  à l'intérieur de `models.dir`, ou un chemin absolu vers un répertoire de modèle. Peut être
  modifié pour chaque session avec `--model`.
- **`dir`** (chaîne de caractères, valeur par défaut : chaîne vide) : le répertoire des modèles gérés. Une chaîne vide signifie : résolution automatique, dans l'ordre :
  `$WHISPSKRID_MODELS_DIR` (si défini) → `~/.local/share/whispskrid/whisper-models/`
  (si celui-ci contient déjà un modèle) → `/usr/share/whispskrid/whisper-models/`
  (installation du paquet) → `whisper-models/` à la racine d'un dépôt Git ;
  le premier de ces répertoires qui existe et contient au moins un modèle est choisi. Si aucun n'existe, le répertoire de l'utilisateur est créé et utilisé comme destination pour `--download-model`.
- **`device`** (chaîne de caractères, valeur par défaut `"auto"`): `"cpu"`, `"cuda"`, ou `"auto"`
  (laisser `faster-whisper` décider).
- **`compute_type`** (chaîne de caractères, valeur par défaut `"auto"`): `"int8"`,
  `"int8_float16"`, `"float16"`, ou `"auto"` (`int8` sur CPU, `float16` sur
  CUDA).

```yaml
models:
  default: "base"
  dir: ""
  device: "auto"
  compute_type: "auto"
```

### `capture`

- **`max_seconds`** (entier, valeur par défaut `300`): durée de coupure de sécurité. Si
  la touche "talkie-walkie" est maintenue enfoncée pendant plus de cette durée,
  l'enregistrement s'arrête automatiquement, ce qui est transcrit et injecté,
  et un avertissement est enregistré. Ceci est une mesure de sécurité contre
  une touche bloquée ou un tampon audio illimité, et non un minuteur de confort
  pour une utilisation normale.

```yaml
capture:
  max_seconds: 300
```

### `audio`

Paramètres du flux d'entrée du microphone, ouverts une seule fois au démarrage de la session et maintenus ouverts entre les dictées.

- **`sample_rate`** (entier, valeur par défaut `16000`): doit correspondre au taux attendu par Whisper.
- **`channels`** (entier, valeur par défaut `1`): mono.
- **`frames_per_buffer`** (entier, valeur par défaut `4096`): granularité de lecture de PortAudio, également l'unité d'arrondi de `capture.max_seconds` et de la durée d'un enregistrement.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
```

### `vad`

Réservé pour un arrêt automatique futur basé sur le silence. **Non implémenté dans
la version 1.0.0**: `vad.enabled: true` affiche un avertissement indiquant que la fonctionnalité n'est pas encore implémentée, et l'outil continue de fonctionner comme un système "push-to-talk" strict (la seule action qui démarre et arrête l'enregistrement est celle que vous effectuez en maintenant la touche enfoncée).

```yaml
vad:
  enabled: false
  silence_ms: 800
```

### `post_processing`

Whisper segmente et met en majuscule les phrases automatiquement ; le post-traitement de WhispSkrid est intentionnellement minimal.

- **`trim`** (booléen, valeur par défaut `true`): supprimer les espaces au début et à la fin
  du texte transcrit.
- **`capitalize_sentence_start`** (booléen, valeur par défaut `true`): forcer la
  majuscule sur la première lettre du texte injecté — Whisper omet parfois
  cela sur un fragment court.

```yaml
post_processing:
  trim: true
  capitalize_sentence_start: true
```

### `hotkeys`

- **`pynput_enabled`** (booléen, valeur par défaut `true`): démarre l'écouteur global `pynput`. `pynput` surveille le serveur X, donc il est démarré chaque fois qu'il est accessible (paramètre `DISPLAY`), pour n'importe quel type de session. Sous Wayland, il ne voit que les événements de touches pour les fenêtres exécutées via XWayland, et jamais une fenêtre Wayland native en focus. Définissez-le sur `false` pour ne jamais le démarrer et contrôler l'outil uniquement via les sous-commandes de socket liées aux raccourcis de votre environnement de bureau.
- **`push_to_talk`** (liste, valeur par défaut `["shift_r"]`): la touche "push-to-talk".
  Maintenue enfoncée → capture ; relâchée → transcription et injection (dans `mode: hold`, voir ci-dessous). `pynput` distingue la pression de la relâche nativement, donc la logique de maintien est exacte sur ce chemin. Les sous-commandes du socket de contrôle (`--dictate`, `--dictate-stop`, `--toggle`) existent pour les environnements de bureau dont le système de raccourcis ne peut pas transmettre "touche maintenue", où ils agissent comme un interrupteur de démarrage/arrêt.
- **`min_hold_ms`** (entier, millisecondes, valeur par défaut `250`): dans `mode: hold` uniquement, si une touche est relâchée avant ce délai, la capture est annulée au lieu d'être transcrite et injectée ; cela permet d'éviter une brève pression involontaire de la touche assignée (par exemple, un raccourci de l'environnement de bureau utilisant la même touche) qui ouvrirait une capture sur du bruit de fond ou du silence, ce que Whisper pourrait interpréter comme du texte. N'a aucun effet en dehors de `mode: hold`.
- **`mode`** (`hold`, `toggle` ou `armed`, valeur par défaut `hold`): ce qu'une pression sur la touche assignée fait. `hold` est le comportement décrit ci-dessus, protégé par `min_hold_ms`. `toggle` démarre la capture lors de la première pression et s'arrête, transcrit et injecte lors de la pression suivante de la même touche ; le relâchement de la touche ne fait rien dans ce mode. `armed` active l'écoute continue pour une phrase parlée lors de la première pression (voir `wakeword` ci-dessous) ; une deuxième pression la désactive. Purement additif : `push_to_talk` et sa logique de maintien restent inchangés lorsque `mode` est absent ou défini sur `hold`.

```yaml
hotkeys:
  pynput_enabled: true
  push_to_talk: ["shift_r"]
  min_hold_ms: 250
  mode: "hold"
```

### `wakeword`

Seulement utilisé lorsque `hotkeys.mode` est `armed`. Un système d'écoute continue activé par la pression d'un bouton :
une courte phrase orale déclenche un segment d'enregistrement, une autre le termine et l'enregistre, jusqu'à ce qu'une deuxième pression sur le bouton désactive le système.

- **`threshold`** (flottant de 0 à 1, valeur par défaut `0.5`): niveau de confiance minimum requis pour qu'une
  phrase soit considérée comme correspondante.
- **`models_dir`** (chaîne de caractères, valeur par défaut : vide) : répertoire contenant les modèles de phrases
  ( `<lang>_open.onnx` / `<lang>_close.onnx`, une paire par langue).
  Une valeur vide correspond aux emplacements d'installation standard.

```yaml
wakeword:
  threshold: 0.5
  models_dir: ""
```

### `control_socket`

Booléen, valeur par défaut `true`. Lorsque cette option est activée, la session en cours écoute sur une
socket Unix à `$XDG_RUNTIME_DIR/whispskrid.sock` (mode `0600`) afin que
les sous-commandes de contrôle puissent la piloter. Définissez sur `false` pour désactiver complètement la socket.

```yaml
control_socket: true
```

### `clipboard`

Le texte est injecté en le plaçant dans le presse-papiers et en simulant un collage.

- **`restore`** (booléen, valeur par défaut `true`): restaure le contenu précédent du presse-papiers de l'utilisateur après le collage. Un contenu du presse-papiers non textuel (une image, par exemple) n'est jamais enregistré ni écrasé.
- **`restore_delay_ms`** (entier, valeur par défaut `400`): durée maximale, en millisecondes, pendant laquelle la fenêtre cible est surveillée, permettant à l'application de lire la sélection avant que le presse-papiers ne soit restauré. L'attente s'arrête prématurément si le presse-papiers a déjà été modifié (un autre programme en a pris le contrôle) ; la restauration est alors abandonnée plutôt que contestée.
- **`defer_restore`** (booléen, valeur par défaut `false`): lorsque `true` est activé, le presse-papiers n'est jamais restauré en ligne ; le contenu original, celui qui existait avant la première dictée de la session, est restauré une seule fois, à la fin de la session (ou via `atexit` en cas de plantage). Cela élimine complètement les problèmes de concurrence liés au presse-papiers observés sous Wayland avec les applications GTK, au prix de voir le contenu du presse-papiers contenir le dernier segment dicté entre deux dictées d'une session active.
- **`confirm_timeout_ms`** (entier, valeur par défaut `500`): durée maximale d'attente pour confirmer que le presse-papiers contient bien le texte dicté avant d'envoyer la touche de collage.

```yaml
clipboard:
  restore: true
  restore_delay_ms: 400
  defer_restore: false
  confirm_timeout_ms: 500
```

### `injection`

Le système de gestion des frappes clavier est choisi une seule fois, au démarrage, par une vérification directe —
il n'est jamais retesté avant chaque opération de collage. La séquence est : **`ydotool`** (si le
fichier binaire existe et que son démon répond) → **`xdotool`** (si le fichier binaire
existe) → mode dégradé (le texte reste dans le presse-papiers, aucune frappe n'est envoyée).
Consultez les notes de compatibilité Wayland du projet pour comprendre pourquoi **`wtype`**
n'est pas intentionnellement inclus dans cette séquence.

- **`paste_combo`** (chaîne de caractères, valeur par défaut `ctrl+v`) et
  **`terminal_paste_combo`** (valeur par défaut `ctrl+shift+v`) : la combinaison de touches
  utilisée pour coller. La détection de la classe de fenêtre (pour choisir
  automatiquement la combinaison pour le terminal) n'est disponible que
  sur le chemin `xdotool` — `ydotool` injecte au niveau `/dev/uinput` et n'a pas
  de notion de fenêtre cible, donc `paste_combo` est toujours utilisé là, sauf
  si vous le modifiez.
- **`terminal_window_classes`** (liste) : classes de fenêtres traitées comme des terminaux
  (uniquement sur le chemin `xdotool`).
- **`ydotool_keycodes`** (mapping) : codes de touches physiques Linux, utilisés
  uniquement sur le chemin `ydotool`, qui envoie des codes de touches
  bruts au lieu de symboles de touches. Modifiez ces valeurs si vous
  utilisez une disposition autre que QWERTY.

```yaml
injection:
  paste_combo: "ctrl+v"
  terminal_paste_combo: "ctrl+shift+v"
  terminal_window_classes: ["konsole", "gnome-terminal-server", "xterm", "st", "alacritty", "kitty", "foot"]
  ydotool_keycodes: {}
```

### `sound_file`

Chemin absolu vers un fichier de son de notification court (par exemple, `.oga`, `.wav`),
joué via `paplay` pour confirmer le démarrage de l'enregistrement. Une valeur vide ou un paramètre `paplay` manquant désactive silencieusement le son.

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

Thème de couleur de la console. Les valeurs doivent être des noms de couleurs `colorama` valides (par exemple, `GREEN`, `RED`, `BLUE`, `RESET` ).

- **`ready_message`**: couleur du bandeau "prêt".
- **`help_text`**, **`help_title`**: couleurs du message d'aide.
- **`info`**, **`success`**, **`warning`**, **`error`**: couleurs du message d'état.

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
