% WHISPSKRID(1) whispskrid | Commandes utilisateur
% Ronan Davalan
% 2026-09-11

# NOM

whispskrid - dictée vocale hors ligne, système complet, pour la ligne de commande.

# SYNOPSIS

**whispskrid** [**-l** *LANG* | **\--lang** *LANG*] [**\--model** *NAME*]

**whispskrid** **\--diagnose**

**whispskrid** **\--download-model** [*NAME*]

**whispskrid** {**\--dictate** | **\--dictate-stop** | **\--toggle** | **\--cancel** | **\--status** | **\--stop**}

whispskrid **\--version**

# DESCRIPTION

**whispskrid** est un outil de dictée en ligne de commande pour Linux, alimenté par le moteur de reconnaissance vocale hors ligne **faster-whisper**. L'enregistrement se fait strictement en mode "push-to-talk" : l'audio n'est enregistré que lorsque vous maintenez une touche enfoncée (ou, de manière équivalente, entre une commande **\--dictate** et une commande **\--dictate-stop**), et le texte reconnu est injecté directement dans la fenêtre qui a actuellement le focus du clavier, qu'il s'agisse d'un terminal, d'un navigateur, d'un éditeur ou d'une autre application, ce qui lui permet de fonctionner à l'échelle du système plutôt que dans un seul programme.

Toute la reconnaissance vocale s'effectue localement : aucun audio ni aucun texte transcrit n'est jamais envoyé à un service distant.

Une seule session s'exécute par utilisateur à la fois. Lancée sans indicateur de contrôle, elle démarre une session persistante : elle charge le modèle, ouvre une prise de contrôle Unix privée à `$XDG_RUNTIME_DIR/whispskrid.sock` (mode `0600`), et démarre un écouteur de raccourcis clavier `pynput` si celui-ci est activé. La même commande invoquée avec un indicateur de contrôle (voir GESTION D'UNE SESSION EN COURS) se connecte à cette prise au lieu de démarrer une nouvelle session.

Le texte est injecté en le plaçant dans le presse-papiers et en simulant un collage, ce qui nécessite deux types d'outils : un simulateur de frappe et un outil de presse-papiers.
Sous Wayland, il s'agit de **ydotool** (qui nécessite le démon `ydotoold` et un accès à `/dev/uinput`) ainsi que **wl-clipboard** ; sous X11, il s'agit de **xdotool** ainsi que **xclip**. Sans l'un ou l'autre de ces environnements, l'injection passe en mode dégradé.
Le choix entre les deux est effectué une seule fois, au démarrage, en vérifiant quel binaire et quel démon répondent réellement, et non en vérifiant directement le type de session. **whispskrid \--diagnose** indique quels outils, quel périphérique audio et quel accès au presse-papiers sont disponibles, puis se termine.

# INSTALLATION

Installez le paquet Debian :

```
sudo dpkg -i whispskrid_<version>_all.deb
```

L'étape `postinst` installe **faster-whisper** via pip et signale sa propre progression ; les `Recommends` du paquet couvrent le backend d'injection pour votre type de session (**ydotool** + **wl-clipboard** sous Wayland, **xdotool** + **xclip** sous X11) — aucun d'eux n'est une dépendance obligatoire, donc un environnement incomplet peut toujours être installé, mais au prix d'un mode d'injection dégradé (voir **--diagnose** ci-dessous).

Aucun modèle Whisper n'est inclus dans le paquet. Téléchargez-en un avant la première utilisation —
les modèles proviennent des conversions officielles CTranslate2 disponibles sur Hugging Face
(*https://huggingface.co/Systran*), et sont téléchargés automatiquement dans le répertoire des modèles gérés
(voir FICHIERS ci-dessous) :

```
whispskrid --download-model
```

Omettre cette étape n'est pas critique : la session persistante télécharge le modèle par défaut lors du premier lancement, et affiche un message pour l'annoncer, car le téléchargement de Hugging Face lui-même ne montre pas de barre de progression (il s'agit d'un transfert de plusieurs centaines de Mo sans aucune activité visible).

Vérifiez ensuite l'environnement :

```
whispskrid --diagnose
```

Les raccourcis clavier globaux via `pynput` surveillent le serveur X : sous Wayland, ils n'atteignent que les fenêtres exécutées via XWayland, et jamais une fenêtre Wayland native qui a le focus. Associez les sous-commandes de contrôle aux propres paramètres de raccourcis de votre bureau pour un contrôle qui fonctionne partout.

# OPTIONS

**-l** *LANG*, **\--lang** *LANG*
:   Force la langue de l'interface et de la reconnaissance vocale pour cette session
    (`en`, `fr`, `de` ou `es`), en écrasant la valeur définie dans
    le fichier de configuration (\`default_language`).  Sélectionne également la langue des propres messages de l'interface en ligne de commande
    (y compris le texte d'aide).

**\--model** *NOM*
:   Remplace `models.default` du fichier de configuration pour cette session :
    il peut s'agir du nom court d'un modèle (l'un des suivants : `tiny`, `base`, `small`, `medium`,
    `large-v3`, ou leurs variantes `.en` — voir **\--download-model** ci-dessous)
    ou d'un chemin d'accès dans le système de fichiers.

**\--diagnose**
:   Vérifier l'environnement (type de session, backend d'injection, outils, GPU/CUDA,
    présence du modèle, entrée audio, presse-papiers, socket de contrôle, configuration)
    et quitter. Le code de sortie est `0` si toutes les vérifications bloquantes réussissent ; certaines
    vérifications (accélération GPU, présence de `ydotool` et de `xdotool`, prises
    individuellement) sont uniquement informatives et n'affectent jamais le code de sortie.

**\--download-model** [*NAME*]
:   Télécharger un modèle Whisper (`base` lorsque *NAME* est omis ; l'un des `tiny`,
    `base`, `small`, `medium`, `large-v3`, ou leurs variantes `.en`),
    depuis Hugging Face vers le répertoire des modèles gérés
    (`~/.local/share/whispskrid/whisper-models/` par défaut - voir FICHIERS),
    puis quitter. Les modèles déjà téléchargés sont détectés et ignorés.

**\--version**
:   Afficher le numéro de version et quitter.

# GESTION D'UNE SESSION EN COURS

Chacun des drapeaux suivants se connecte à la socket de la session en cours,
effectue l'action, affiche la réponse résultante (`OK`, `OK <text>` ou
`ERR <reason>`), et se termine avec le code de statut `0` si `OK`, sinon avec `1`. Ils
sont destinés à être associés à des raccourcis clavier du bureau.

**\--dictate**
:   Start capture. Fails with `ERR already-capturing` if a capture is
    already in progress.

**\--dictate-stop**
:   Arrête la capture en cours, transcrit le résultat et l'injecte.  Échoue avec `ERR not-capturing` s'il n'y a pas de capture en cours.

**\--toggle**
:   **\--dictate** ou **\--dictate-stop**, selon l'état actuel de la session : un raccourci unique pour une touche "pousser pour parler" qui permet de démarrer/arrêter la communication et qui est configurée au niveau du bureau.

**\--cancel**
:   Annuler l'enregistrement en cours sans transcrire ni injecter quoi que ce soit.

**\--status**
:   Affiche l'état de la session actuelle (`state=idle|capturing model=<name>
    language=<lang|auto>`) sans le modifier.

**\--stop**
:   Fermer proprement la session persistante en cours.

# RACCORTS CLAVIER

`pynput` Les touches de raccourci globales sont activées chaque fois que `hotkeys.pynput_enabled` est
vrai dans le fichier de configuration et qu'un serveur d'affichage est accessible
(paramètre `DISPLAY`) — pour tous les types de session, y compris Wayland, car `pynput`
lui-même surveille le serveur X. Le listener ne consomme pas l'événement de touche :
la frappe atteint également la fenêtre active. La configuration par défaut associe
la fonction "push-to-talk" à :

**Maj droit**
:   Maintenir pour enregistrer, relâcher pour arrêter, transcrire et injecter : la fonctionnalité native de pression/relâchement de `pynput` implémente la fonction "pousser pour parler" directement sur ce chemin (contrairement au chemin de la socket de contrôle mentionné ci-dessus, qui ne reçoit que des commandes discrètes et doit donc exposer **--toggle** à la place).

Les touches assignées sont configurables dans la section `hotkeys.push_to_talk` du
fichier de configuration. Chaque nom ci-dessous désigne une seule touche physique : `ctrl_r` (Ctrl droit), `ctrl_l` (Ctrl gauche), `alt_r` (Alt droit), `alt_l` (Alt gauche), `shift_r` (Maj droit), `shift_l` (Maj gauche), `cmd`, `f1` à `f12` (touches de fonction). En lister plusieurs en fait une combinaison : toutes doivent être tenues ensemble, dans n'importe quel ordre, pour engager la fonction "push-to-talk" (par exemple `["alt_l", "shift_r"]`) ; en `mode: hold`, relâcher l'une d'entre elles arrête et injecte. Une combinaison de touches modificatrices peut entrer en conflit avec un raccourci du bureau (par exemple, Alt+Maj est couramment lié au changement de disposition clavier sous KDE Plasma et GNOME) — une touche de fonction comme `f4` évite ce type de conflit.

`hotkeys.min_hold_ms` (millisecondes, par défaut `250`) s'applique à `mode: hold` uniquement : une touche pressée avant ce délai annule l'enregistrement au lieu de transcrire et d'injecter le son, ce qui permet d'éviter qu'une brève pression involontaire sur la touche assignée (par exemple, un raccourci clavier sur un ordinateur) n'enregistre du bruit de fond ou un silence, ce que Whisper pourrait interpréter à tort comme du texte.

`hotkeys.mode` (`hold`, par défaut, `toggle`, ou `armed`) contrôle ce qui se passe
lorsque la touche associée est pressée. `hold` est le comportement décrit ci-dessus,
protégé par `hotkeys.min_hold_ms`. `toggle` démarre l'enregistrement au premier appui et s'arrête,
transcrit et insère au prochain appui de la même touche ; relâcher la touche ne fait
rien dans ce mode, ce qui est utile pour éviter de maintenir une touche enfoncée
pendant une longue dictée. `armed` active l'écoute continue d'une phrase parlée au
premier appui ; une courte phrase ouvre un segment d'enregistrement, une autre le ferme
et l'insère, jusqu'à ce qu'un deuxième appui désactive cette fonction ; voir la
touche `wakeword` dans **configuration.md** (CONFIGURATION ci-dessous).

Pour modifier la ou les clés de limite ou le mode, éditez `hotkeys.push_to_talk` /
`hotkeys.mode` dans le fichier de configuration (voir CONFIGURATION ci-dessous pour son
chemin exact), puis redémarrez la session persistante pour que le changement prenne
effet :

```
whispskrid --stop
whispskrid
```

Pour lier **\--toggle** à un raccourci au niveau du bureau, plutôt qu'à un raccourci global, ce qui est la seule option sous Wayland pour les fenêtres qui ne passent pas par XWayland, ce que `pynput` ne peut pas atteindre, la plupart des environnements de bureau offrent un paramètre de raccourci personnalisé. Sur GNOME : *Paramètres → Clavier → Afficher et personnaliser les raccourcis → Raccourcis personnalisés → Ajouter un raccourci*, avec `whispskrid --toggle` comme commande et la combinaison de touches de votre choix. KDE Plasma offre l'équivalent sous *Paramètres système → Raccourcis → Raccourcis personnalisés*.

# CONFIGURATION

Le comportement de l'application pendant son exécution est contrôlé par un fichier de configuration YAML : ce fichier définit les paramètres par défaut de la langue, du backend, du modèle, la durée de l'enregistrement, le périphérique audio, le post-traitement et les raccourcis clavier.

Le fichier de configuration est trouvé en fonction de la première règle correspondante parmi celles listées ci-dessous ; une fois qu'une règle est trouvée, les règles restantes ne sont pas consultées.

1. Le chemin spécifié dans la variable d'environnement **WHISPSKRID_CONFIG**, si elle est définie.
   Utilisé tel quel ; jamais créé automatiquement.
2. `config/config.yaml`, par rapport au répertoire du projet, lors de l'exécution
   depuis une copie Git (mode développement).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (par défaut
   `~/.config/whispskrid/config.yaml`). Créé automatiquement lors de la première exécution,
   à partir du modèle par défaut.
4. Le modèle par défaut : `/usr/share/whispskrid/config.yaml` (installation du paquet Debian), sinon le `config/config.yaml` intégré au projet
   (permet de fonctionner à partir d'une archive source sans répertoire `.git`).

Le fichier résolu peut être partiel : toute clé qui lui manque reprend la valeur du modèle par défaut, et les clés sont fusionnées une par une.

La langue active est choisie, dans l'ordre suivant : l'**\--lang**, si elle est spécifiée ;
sinon, celle définie dans le fichier de configuration, c'est-à-dire `default_language` ; sinon,
détection automatique par le module de reconnaissance.

Consultez **configuration.md** dans la documentation du projet pour obtenir la référence complète
de chaque clé de configuration.

DÉPANNAGE

**Modèle non trouvé.** Exécutez **--diagnose** et lisez sa ligne de résumé finale,
qui indique le premier contrôle bloquant — ne devinez pas à partir de la sortie brute ci-dessus :

```
whispskrid --diagnose
```

Si la ligne de résumé indique le nom du test du modèle, téléchargez-en un :

```
whispskrid --download-model
```

Ensuite, relancez **--diagnose**; il quitte `0` une fois que chaque vérification de blocage est réussie (voir ÉTAT DE SORTIE).

# FICHIERS

`~/.config/whispskrid/config.yaml`
:   Fichier de configuration par utilisateur.

`/usr/share/whispskrid/config.yaml`
:   Modèle de configuration d'usine (installation via paquet Debian), en lecture seule.

`~/.local/share/whispskrid/whisper-models/`
:   Répertoire par défaut pour les modèles Whisper téléchargés.

`config/config.yaml`
:   Fichier de configuration utilisé lors de l'exécution à partir d'un dépôt Git.

`whisper-models/`
:   Emplacement par défaut recherché pour les modèles Whisper lorsqu'on exécute le programme à partir d'un dépôt Git
    ou d'une archive source.

`$XDG_RUNTIME_DIR/whispskrid.sock`
:   Socket de contrôle de la session en cours (mode `0600`).

# CODE DE SORTIE

:   Le programme s'est terminé correctement, ou une commande de contrôle a été reçue `OK`.

Non nul
:   Démarrage échoué (pas de backend d'injection, de modèle ou de périphérique audio disponible),
    ou une commande de contrôle reçue `ERR`.

# EXEMPLES

Démarrez une session persistante en utilisant la langue par défaut spécifiée dans le fichier de configuration.

```
whispskrid
```

Forcez l'anglais pour cette session.

```
whispskrid --lang en
```

Associer des raccourcis clavier pour la fonction "talk" sans dépendre de `pynput` :

```
whispskrid --dictate
whispskrid --dictate-stop
```

# VOIR ÉGALEMENT

faster-whisper: *https://github.com/SYSTRAN/faster-whisper*

Catalogue des modèles Whisper: *https://huggingface.co/Systran*

Page d'accueil du projet : *https://whispskrid.davalan.fr/*

# BUGS

Signalez les erreurs sur le système de suivi des problèmes du projet :
*https://github.com/RonanDavalan/whispskrid/issues*

# AUTEUR

Ronan Davalan, et les contributeurs listés dans CONTRIBUTORS.md.
