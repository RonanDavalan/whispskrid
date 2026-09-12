% WHISPSKRID(1) whispskrid | Commandes utilisateur
% Ronan Davalan
% 2026-09-11

# NOM

whispskrid - dictée vocale hors ligne, système complet, pour la ligne de commande.

# SYNOPSIS

**whispskrid** [**-l** *LANG* | **--lang** *LANG*] [**--model** *NAME*]

**whispskrid** **\--diagnose**

**whispskrid** **\--download-model** [*NAME*]

**whispskrid** {**\--dictate** | **\--dictate-stop** | **\--toggle** | **\--cancel** | **\--status** | **\--stop**}

**whispskrid** **\--version**

# DESCRIPTION

**whispskrid** est un outil de dictée en ligne de commande pour Linux, alimenté par le moteur de reconnaissance vocale **offline Whisper** (**faster-whisper**). L'enregistrement est strictement en mode "parler-pour-enregistrer" : l'audio n'est enregistré que pendant que vous maintenez une touche enfoncée (ou, de manière équivalente, entre une commande **\--dictate** et une commande **\--dictate-stop**), et le texte reconnu est directement injecté dans la fenêtre qui a actuellement le focus du clavier – terminal, navigateur, éditeur ou toute autre application – ce qui lui permet de fonctionner à l'échelle du système, plutôt que dans un seul programme.

Toute la reconnaissance vocale s'effectue localement : aucun audio ni aucun texte transcrit n'est jamais envoyé à un service distant.

Une seule session s'exécute par utilisateur à la fois. Lancée sans indicateur de contrôle, elle démarre une session persistante : elle charge le modèle, ouvre une socket de contrôle Unix privée à `$XDG_RUNTIME_DIR/whispskrid.sock` (mode `0600`), et démarre un écouteur de raccourcis clavier `pynput` si celui-ci est activé. La même commande, invoquée avec un indicateur de contrôle (voir GÉRER UNE SESSION EN COURS), se connecte à cette socket au lieu de démarrer une nouvelle session.

Le texte est injecté en le plaçant dans le presse-papiers et en simulant un collage, de sorte que deux types d'outils sont nécessaires : un simulateur de frappe et un outil de presse-papiers.
Sous Wayland, il s'agit de **ydotool** (nécessite le démon `ydotoold` et un accès à `/dev/uinput`) ainsi que de **wl-clipboard** ; sous X11, il s'agit de **xdotool** ainsi que de **xclip**. Sans l'un ou l'autre de ces environnements, l'injection revient à un mode dégradé. Le choix entre les deux se fait une seule fois, au démarrage, en sondant lequel des deux binaires et de son démon répond réellement — pas en vérifiant directement le type de session.
**whispskrid \--diagnose** indique quels outils, quel périphérique audio et quel accès au presse-papiers sont disponibles, puis se termine.

# INSTALLATION

Installez le paquet Debian :

```
sudo dpkg -i whispskrid_<version>_all.deb
```

L'étape postinst installe **faster-whisper** via pip et signale sa propre
progression ; les `Recommends` du paquet couvrent le backend d'injection
adapté à votre type de session (**ydotool** + **wl-clipboard** sous
Wayland, **xdotool** + **xclip** sous X11) — aucun n'est une dépendance
stricte, donc un environnement incomplet s'installe quand même, au prix
d'un mode d'injection dégradé (voir **\--diagnose** ci-dessous).

Aucun modèle Whisper n'est fourni avec le paquet. Téléchargez-en un avant
la première utilisation — les modèles proviennent des conversions
CTranslate2 officielles hébergées sur Hugging Face
(*https://huggingface.co/Systran*), récupérées automatiquement dans le
répertoire de modèles géré (voir FICHIERS ci-dessous) :

```
whispskrid --download-model
```

Sauter cette étape n'est pas bloquant : la session persistante télécharge
elle-même le modèle par défaut au premier lancement, en l'annonçant
d'abord — le téléchargement de Hugging Face n'affiche aucune barre de
progression, un transfert de plusieurs centaines de Mo resterait sinon
sans aucune activité visible.

Puis vérifiez l'environnement :

```
whispskrid --diagnose
```

Raccourcis globaux via `pynput` en surveillant le serveur X : sous Wayland, ils n'atteignent que les fenêtres exécutées via XWayland, et jamais une fenêtre Wayland native active.  Associez les sous-commandes de contrôle aux propres paramètres de raccourcis de votre environnement de bureau pour un contrôle qui fonctionne partout.

# OPTIONS

-l *LANG*, **\--lang** *LANG*
:   Force la langue de l'interface et de la reconnaissance vocale pour cette session
    (`en`, `fr`, `de` ou `es`), en remplaçant la valeur définie dans
    le fichier de configuration (\`default_language` ).  Sélectionne également la langue des propres messages de l'interface en ligne de commande
    (y compris le texte d'aide).

**\--model** *NOM*
:   Remplace `models.default` du fichier de configuration pour cette session :
    il s'agit du nom court d'un modèle (par exemple `base`) ou d'un chemin d'accès au système de fichiers.

**\--diagnose**
:   Vérifiez l'environnement (type de session, backend d'injection, outils, GPU/CUDA,
    présence du modèle, entrée audio, presse-papiers, socket de contrôle, configuration)
    et quittez. Le code de sortie est `0` si toutes les vérifications bloquantes réussissent ; certaines
    vérifications (accélération GPU, présence de `ydotool` et de `xdotool`, considérées
    individuellement) sont purement informatives et n'affectent jamais le code de sortie.

**\--download-model** [*NOM*]
:   Téléchargez un modèle Whisper (`base` si *NOM* est omis ; l'un de
    `tiny`, `base`, `small`, `medium`, `large-v3`, ou leurs variantes
    `.en`) depuis Hugging Face, dans le répertoire de modèles géré
    (`~/.local/share/whispskrid/whisper-models/` par défaut — voir
    FICHIERS), puis quittez. Un modèle déjà téléchargé est détecté et
    l'opération est court-circuitée.

**\--version**
:   Afficher le numéro de version et quitter.

# GESTION D'UNE SESSION EN COURS

Chacun des drapeaux suivants se connecte à la socket de la session en cours,
effectue l'action, affiche la réponse résultante (`OK`, `OK <text>` ou
`ERR <reason>`), et se termine avec le statut `0` sur `OK`, et `1` sinon. Ils
sont destinés à être associés à des raccourcis clavier du bureau.

**\--dictate**
:   Débuter une capture. Échoue avec `ERR already-capturing` si une capture est déjà en cours.

**\--dictate-stop**
:   Arrêtez l'enregistrement en cours, transcrivez-le et injectez le résultat.  Échoue avec `ERR not-capturing` s'il n'y a pas d'enregistrement en cours.

**\--toggle**
:   **\--dictate** ou **\--dictate-stop**, selon l'état actuel de la session : un raccourci unique pour une touche "appuyer pour démarrer / arrêter" qui active la fonction "talkie-walkie" et qui est configurée au niveau du bureau.

**\--cancel**
:   Abandonner l'enregistrement en cours sans transcrire ni injecter
    rien.

**\--status**
:   Affiche l'état de la session actuelle (`state=idle|capturing model=<name>
    language=<lang|auto>`) sans la modifier.

**\--stop**
:   Fermez proprement la session active en cours.

# TOUCHES DE RACCOURCI

`pynput` Les touches de raccourci globales sont activées chaque fois que `hotkeys.pynput_enabled` est
vrai dans le fichier de configuration et qu'un serveur d'affichage est
joignable (`DISPLAY` défini) — quel que soit le type de session, Wayland
compris, puisque `pynput` surveille lui-même le serveur X. Le service d'écoute ne consomme pas
l'événement de touche : la frappe atteint également la fenêtre active. La
configuration de l'usine associe la fonction "push-to-talk" à :

**Ctrl droit**
:   Maintenez la touche pour enregistrer, relâchez-la pour arrêter. La transcription et l'injection utilisent les mécanismes natifs de pression/relâchement de `pynput`.  Cela permet d'implémenter la fonction "talkie-walkie" directement sur ce chemin (contrairement au chemin de la "control-socket" mentionné ci-dessus, qui ne reçoit que des commandes discrètes et doit donc exposer **--toggle** à la place).

Les clés liées sont configurables sous `hotkeys.push_to_talk` dans le
fichier de configuration (`ctrl_r`, `ctrl_l`, `alt_r`, `alt_l`, `shift_r`,
`shift_l`, `cmd`).

Pour changer la ou les touches associées, modifiez `hotkeys.push_to_talk`
dans le fichier de configuration (voir CONFIGURATION ci-dessous pour son
chemin exact), puis redémarrez la session persistante pour que le
changement prenne effet :

```
whispskrid --stop
whispskrid
```

# CONFIGURATION

Le comportement en cours d'exécution est contrôlé par un fichier de configuration YAML : il définit la langue par défaut, le backend, les paramètres du modèle, la durée de capture, le périphérique audio, le post-traitement et les raccourcis clavier.

Le fichier de configuration est trouvé selon la première règle correspondante ci-dessous ; une fois qu'une règle correspond, les règles restantes ne sont pas consultées.

1. Le chemin spécifié dans la variable d'environnement **WHISPSKRID_CONFIG**, si elle est définie.
   Utilisé tel quel ; jamais créé automatiquement.
2. `config/config.yaml`, relatif au répertoire du projet, lors de l'exécution
   depuis une branche Git (mode développement).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (par défaut
   `~/.config/whispskrid/config.yaml`). Créé automatiquement lors de la première exécution,
   à partir du modèle par défaut.
4. Le modèle par défaut : `/usr/share/whispskrid/config.yaml` (installation du paquet Debian), sinon le `config/config.yaml` intégré au projet
   (permet de fonctionner à partir d'une archive source sans répertoire `.git`).

Le fichier résolu peut être partiel : toute clé qui lui manque reprend la valeur du modèle par défaut, fusionnée clé par clé.

La langue active est choisie, dans l'ordre suivant : l'**\--lang** option, si elle est spécifiée ; sinon, `default_language` depuis le fichier de configuration ; sinon, détection automatique par le moteur de reconnaissance.

Consultez **configuration.md** dans la documentation du projet pour obtenir la référence complète de chaque clé de configuration.

# DÉPANNAGE

**Modèle introuvable.** Lancez **\--diagnose** et lisez sa ligne de
synthèse finale, qui nomme d'elle-même la première vérification
bloquante — ne devinez pas à partir de la sortie brute au-dessus :

```
whispskrid --diagnose
```

Si la ligne de synthèse nomme la vérification du modèle, téléchargez-en
un :

```
whispskrid --download-model
```

Puis relancez **\--diagnose** ; il se termine avec le code `0` dès que
toutes les vérifications bloquantes réussissent (voir CODE DE SORTIE).

# FICHIERS

`~/.config/whispskrid/config.yaml`
:   Fichier de configuration par utilisateur.

`/usr/share/whispskrid/config.yaml`
:   Modèle de configuration d'usine (installation du paquet Debian), en lecture seule.

`~/.local/share/whispskrid/whisper-models/`
:   Répertoire par défaut pour les modèles Whisper téléchargés.

`config/config.yaml`
:   Fichier de configuration utilisé lors de l'exécution à partir d'un dépôt Git.

`whisper-models/`
:   Emplacement par défaut où les modèles Whisper sont recherchés lors de l'exécution à partir d'un dépôt Git ou d'une archive source.

`$XDG_RUNTIME_DIR/whispskrid.sock`
:   Socket de contrôle de la session en cours (mode `0600`).

# CODE DE SORTIE

**0**
:   Le programme s'est terminé correctement, ou une commande de contrôle a été reçue `OK`.

Non nul
:   Démarrage échoué (pas de backend d'injection, de modèle ou de périphérique audio disponible),
    ou une commande de contrôle a été reçue `ERR`.

# EXEMPLES

Démarrez une session utilisateur avec la langue par défaut spécifiée dans le fichier de configuration :

```
whispskrid
```

Forcer l'anglais pour cette session.

```
whispskrid --lang en
```

Associez des raccourcis clavier pour la fonction "push-to-talk" sans dépendre de `pynput` :

```
whispskrid --dictate
whispskrid --dictate-stop
```

VOIR ÉGALEMENT

faster-whisper: *https://github.com/SYSTRAN/faster-whisper*

Catalogue des modèles Whisper : *https://huggingface.co/Systran*

Page d'accueil du projet : *https://whispskrid.davalan.fr/*

# BUGS

Signalez les problèmes sur le système de suivi des problèmes du projet :
*https://github.com/RonanDavalan/whispskrid/issues*

# AUTEUR

Ronan Davalan, et les contributeurs mentionnés dans CONTRIBUTORS.md.
