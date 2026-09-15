% WHISPSKRID(1) whispskrid | Comandos de usuario
% Ronan Davalan
% 2026-09-11

NOMBRE

whispskrid: Dictado "push-to-talk" sin conexión, a nivel de sistema, para la línea de comandos.

# RESUMEN

**whispskrid** [**-l** *LANG* | **--lang** *LANG*] [**--model** *NAME*]

**whispskrid** **\--diagnose**

whispskrid **\--download-model** [*NAME*]

**whispskrid** {**\--dictate** | **\--dictate-stop** | **\--toggle** | **\--cancel** | **\--status** | **\--stop**}

**whispskrid** **\--version**

# DESCRIPCIÓN

**whispskrid** es una herramienta de dictado de línea de comandos para Linux, impulsada por el motor de reconocimiento de voz offline (**faster-whisper**). La captura es estrictamente "presionar para hablar": el audio se graba solo mientras se mantiene presionada una tecla (o, equivalentemente, entre un comando **\--dictate** y un comando **\--dictate-stop**), y el texto reconocido se inyecta directamente en la ventana que actualmente tiene el foco del teclado, ya sea un terminal, un navegador, un editor o cualquier otra aplicación, por lo que funciona a nivel de todo el sistema en lugar de dentro de un solo programa.

Todo el reconocimiento de voz se realiza localmente: ni el audio ni el texto transcrito se envían nunca a un servicio remoto.

Solo una sesión se ejecuta por usuario a la vez. Cuando se inicia sin una bandera de control, se inicia una sesión residente: carga el modelo, abre un socket de control Unix privado en `$XDG_RUNTIME_DIR/whispskrid.sock` (modo `0600`), y inicia un listener de teclas de acceso rápido `pynput` si está habilitado. El mismo comando invocado con una bandera de control (ver CONTROLANDO UNA SESIÓN EN EJECUCIÓN) se conecta a ese socket en lugar de iniciar una nueva sesión.

Se inyecta el texto colocándolo en el portapapeles y simulando un pegado, por lo que
se necesitan dos tipos de herramientas: un simulador de pulsaciones de teclas y una herramienta de portapapeles.
Bajo Wayland, esto es **ydotool** (necesita el demonio `ydotoold` y acceso a `/dev/uinput`) más **wl-clipboard**; bajo X11, es **xdotool** más **xclip**. Sin ninguno de estos backends, la inyección recurre a un modo degradado.
La elección entre los dos se realiza una sola vez, al inicio, comprobando qué
binario y demonio responden realmente, no comprobando directamente el tipo de sesión. **whispskrid \--diagnose** informa qué herramientas, dispositivo de audio y acceso al portapapeles están presentes, y luego se cierra.

# INSTALACIÓN

Instala el paquete de Debian:

```
sudo dpkg -i whispskrid_<version>_all.deb
```

El paso `postinst` instala **faster-whisper** a través de pip e informa sobre su propio progreso; el paquete incluye `Recommends` que cubren el backend de inyección para tu tipo de sesión (**ydotool** + **wl-clipboard** en Wayland, **xdotool** + **xclip** en X11); ninguno de ellos es una dependencia obligatoria, por lo que un entorno incompleto aún se instala, pero a costa de un modo de inyección degradado (ver **--diagnose** a continuación).

Ningún modelo de Whisper se incluye en el paquete. Descargue uno antes del primer uso;
los modelos provienen de las conversiones oficiales de CTranslate2 en Hugging Face
(*https://huggingface.co/Systran*), y se descargan automáticamente en el directorio de modelos gestionado
(consulte FILES a continuación):

```
whispskrid --download-model
```

Omitir este paso no es crítico: la sesión residente descarga el modelo predeterminado por sí misma al iniciarse por primera vez, avisando previamente de ello, ya que la descarga de Hugging Face no muestra una barra de progreso (una transferencia de varios cientos de MB sin ninguna actividad visible).

Luego, verifica el entorno:

```
whispskrid --diagnose
```

Atajos globales a través de `pynput` monitorizando el servidor X: bajo Wayland, solo alcanzan las ventanas que se ejecutan a través de XWayland, nunca una ventana nativa de Wayland que tenga el foco. Asigna los subcomandos de control a la configuración de atajos propia de tu escritorio para un control que funcione en todas partes.

# OPCIONES

-l *LANG*, **\--lang** *LANG*
:   Fuerza el idioma de la interfaz y el reconocimiento de voz para esta sesión
    (`en`, `fr`, `de` o `es`), sobrescribiendo el valor de `default_language` del
    archivo de configuración. También selecciona el idioma de los propios mensajes de la
    interfaz de línea de comandos (incluido el texto de ayuda).

**\--model** *NOMBRE*
:   Sustituye `models.default` del archivo de configuración para esta sesión: puede ser el nombre corto de un modelo (uno de `tiny`, `base`, `small`, `medium`,
    `large-v3`, o sus variantes `.en` — consulta **\--download-model** a continuación)
    o una ruta de sistema de archivos.

**\--diagnose**
:   Verifique el entorno (tipo de sesión, backend de inyección, herramientas, GPU/CUDA,
    presencia del modelo, entrada de audio, portapapeles, socket de control, configuración)
    y salga. El estado de salida es `0` cuando todas las verificaciones que pueden bloquear la ejecución se aprueban; algunas
    verificaciones (aceleración de la GPU, presencia de `ydotool`/`xdotool` tomadas
    individualmente) son solo informativas y nunca bloquean el estado de salida.

**\--download-model** [*NAME*]
:   Descargue un modelo Whisper (`base` cuando *NAME* se omite; uno de `tiny`,
    `base`, `small`, `medium`, `large-v3`, o sus variantes `.en`),
    desde Hugging Face en el directorio de modelos gestionados
    (`~/.local/share/whispskrid/whisper-models/` por defecto; consulte FILES),
    y luego salga. Los modelos ya descargados se detectan y se omiten.

**\--version**
:   Imprimir el número de versión y salir.

# CONTROLANDO UNA SESIÓN EN CURSO

Cada una de las siguientes opciones de línea de comandos se conecta al socket de la sesión en ejecución,
realiza la acción, imprime la respuesta resultante (`OK`, `OK <text>` o
`ERR <reason>`), y finaliza con el código de estado `0` en `OK`, y con `1` en caso contrario. Están
diseñadas para ser asignadas a atajos de teclado del escritorio.

**\--dictate**
:   Comienza la captura. Falla con `ERR already-capturing` si ya hay una captura en progreso.

**\--dictate-stop**
:   Detener la captura actual, transcribirla e inyectar el resultado. Falla
    con `ERR not-capturing` si no hay ninguna captura en progreso.

**\--toggle**
:   **\--dictate** o **\--dictate-stop**, dependiendo del estado actual de la sesión; un único atajo para una tecla de "presionar para iniciar/detener" que funciona como un botón de "hablar/escuchar" y está configurada a nivel del escritorio.

**\--cancel**
:   Descartar la captura en curso sin transcribir ni inyectar
    nada.

**\--status**
:   Imprime el estado actual de la sesión (`state=idle|capturing model=<name>
    language=<lang|auto>`) sin modificarlo.

**\--stop**
:   Finalizar la sesión activa del usuario de forma limpia.

TECLAS DE ACCESO RÁPIDO

`pynput` global hotkeys are started whenever `hotkeys.pynput_enabled` is
true in the configuration file and a display server is reachable
(`DISPLAY` set) — on any session type, Wayland included, since `pynput`
itself watches the X server. The listener does not consume the key
event: the keystroke also reaches the focused window. The factory
configuration binds push-to-talk to:

**Mayús derecho**
:   Mantener para grabar, soltar para detener; transcribe e inyecta: la semántica nativa de presionar/soltar de `pynput` implementa el "push-to-talk" directamente en esta ruta (a diferencia de la ruta del "control-socket" mencionada anteriormente, que solo ve comandos discretos y, por lo tanto, debe exponer **--toggle** en su lugar).

Las teclas asignadas son configurables en `hotkeys.push_to_talk` en el
archivo de configuración. Cada nombre a continuación designa una tecla física:
`ctrl_r` (Control derecho), `ctrl_l` (Control izquierdo), `alt_r`
(Alt derecho), `alt_l` (Alt izquierdo), `shift_r` (Shift derecho), `shift_l` (Shift
izquierdo), `cmd`. Indicar varias las convierte en una combinación: todas
deben mantenerse pulsadas a la vez, en cualquier orden, para activar
"push-to-talk" (por ejemplo `["alt_l", "shift_r"]`); en `mode: hold`,
soltar cualquiera de ellas detiene la captura y la inyecta.

`hotkeys.min_hold_ms` (milisegundos, valor predeterminado `250`) se aplica a `mode: hold`
solo: una pulsación liberada antes de este retardo cancela la captura en lugar de
transcribirla e inyectarla; esto sirve como protección contra una breve y no intencionada
pulsación de la tecla asignada (por ejemplo, un acceso directo del escritorio que comparte la misma tecla) que, de lo contrario, capturaría ruido de fondo o casi silencio, lo que Whisper podría
interpretar como texto incorrecto.

`hotkeys.mode` (`hold`, the default, `toggle`, or `armed`) controls what
pressing the bound key does. `hold` is the behavior described above,
guarded by `hotkeys.min_hold_ms`. `toggle` starts capture on the first
press and stops, transcribes and injects on the next press of the same
key; releasing the key does nothing in this mode — useful to avoid holding
a key down for a long dictation. `armed` arms continuous listening for a
spoken phrase on the first press — a short phrase opens a capture segment,
another closes and injects it, until a second press disarms; see the
`wakeword` key in **configuration.md** (CONFIGURATION below).

Para cambiar la(s) clave(s) de acceso o el modo, edite `hotkeys.push_to_talk` /
`hotkeys.mode` en el archivo de configuración (consulte la sección CONFIGURACIÓN a continuación para su
ruta exacta), luego reinicie la sesión activa para que el cambio surta efecto:

```
whispskrid --stop
whispskrid
```

Para vincular **\--toggle** a un acceso directo a nivel de escritorio, en lugar de usar el menú de aplicaciones —la única opción en Wayland para ventanas que no pasan por XWayland, a la que `pynput` no puede acceder—, la mayoría de los entornos de escritorio ofrecen una configuración de acceso directo personalizada. En GNOME: *Configuración → Teclado → Ver y personalizar accesos directos → Accesos directos personalizados → Agregar acceso directo*, con `whispskrid --toggle` como el comando y la combinación de teclas de su elección. KDE Plasma ofrece lo equivalente en *Configuración del sistema → Accesos directos → Accesos directos personalizados*.

# CONFIGURACIÓN

El comportamiento en tiempo de ejecución está controlado por un archivo de configuración YAML: lenguaje predeterminado, parámetros de backend y modelo, duración máxima de la captura, dispositivo de audio, procesamiento posterior y atajos de teclado.

El archivo de configuración se encuentra mediante la primera regla que coincida; una vez que una regla coincide, las reglas restantes no se consultan.

1. La ruta especificada en la variable de entorno **WHISPSKRID_CONFIG**, si está definida.
   Se utiliza tal cual; nunca se crea automáticamente.
2. `config/config.yaml`, relativo al directorio del proyecto, al ejecutarse
   desde un repositorio Git (modo de desarrollo).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (predeterminado
   `~/.config/whispskrid/config.yaml`). Se crea automáticamente en la primera ejecución,
   a partir de la plantilla predeterminada.
4. La plantilla predeterminada: `/usr/share/whispskrid/config.yaml` (instalación de paquete Debian), de lo contrario, la `config/config.yaml` incluida en el proyecto
   (cubre la ejecución desde un archivo tarball de origen sin un directorio `.git`).

El archivo resuelto puede ser parcial: cualquier clave que omita recurre al valor de la plantilla predeterminada, y las claves se combinan una por una.

El idioma activo se elige, en el siguiente orden: la opción **\--lang**, si se proporciona; de lo contrario, `default_language` del archivo de configuración; de lo contrario, detección automática por el backend de reconocimiento.

Consulte **configuration.md** en la documentación del proyecto para obtener la referencia completa de cada clave de configuración.

SOLUCIÓN DE PROBLEMAS

**Modelo no encontrado.** Ejecute **--diagnose** y lea su línea de resumen final,
que indica la primera verificación que impide el proceso; no intente deducirla de la
salida sin procesar que se muestra arriba:

```
whispskrid --diagnose
```

Si la línea de resumen indica el nombre de la prueba del modelo, descargue una:

```
whispskrid --download-model
```

Luego, ejecute **--diagnose**; este sale `0` una vez que todas las comprobaciones de bloqueo se completan
(consulte el ESTADO DE SALIDA).

# ARCHIVOS

`~/.config/whispskrid/config.yaml`
:   Archivo de configuración por usuario.

`/usr/share/whispskrid/config.yaml`
:   Plantilla de configuración de fábrica (instalación de paquete Debian), solo lectura.

`~/.local/share/whispskrid/whisper-models/`
:   Directorio predeterminado para los modelos de Whisper descargados.

`config/config.yaml`
:   Archivo de configuración utilizado al ejecutar desde un repositorio Git.

`whisper-models/`
:   Ubicación predeterminada donde se buscan los modelos de Whisper al ejecutar desde un
    clon de Git o un archivo tarball de código fuente.

`$XDG_RUNTIME_DIR/whispskrid.sock`
:   Control socket de la sesión en ejecución (modo `0600`).

ESTADO DE SALIDA

El programa finalizó correctamente, o se recibió un comando de control `OK`.

No nulo
:   El inicio falló (no se encontró un backend de inyección, modelo o dispositivo de audio),
    o se recibió un comando de control `ERR`.

# EJEMPLOS

Comienza una sesión para residentes utilizando el idioma predeterminado del archivo de configuración:

```
whispskrid
```

Fuerza en inglés para esta sesión:

```
whispskrid --lang en
```

Asigna atajos de escritorio para la función de "push-to-talk" sin depender de `pynput`:

```
whispskrid --dictate
whispskrid --dictate-stop
```

# VEA TAMBIÉN

faster-whisper: *https://github.com/SYSTRAN/faster-whisper*

Catálogo de modelos Whisper: *https://huggingface.co/Systran*

Página de inicio del proyecto: *https://whispskrid.davalan.fr/*

# ERRORES

Reporte los errores en el sistema de seguimiento de problemas del proyecto:
*https://github.com/RonanDavalan/whispskrid/issues*

# AUTOR

Ronan Davalan, y los colaboradores mencionados en CONTRIBUTORS.md.
