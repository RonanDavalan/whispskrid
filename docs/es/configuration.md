Guía de configuración del proyecto.

Este documento explica todas las opciones disponibles en `config.yaml`. Configurar correctamente este archivo le permite adaptar WhispSkrid a su hardware, su idioma y su entorno de escritorio.

¿Cómo se encuentra el archivo de configuración?

El archivo se encuentra según la primera regla que coincida a continuación; una vez que una regla coincide, las reglas restantes no se consultan.

1. La ruta especificada en la variable de entorno **WHISPSKRID_CONFIG**, si está definida.
   Se utiliza tal cual; nunca se crea automáticamente.
2. `config/config.yaml`, relativo al directorio del proyecto, cuando se ejecuta
   desde un repositorio Git (modo de desarrollo, que se activa cuando `.git` existe
   junto a la raíz del proyecto **y** el archivo existe allí).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (por defecto
   `~/.config/whispskrid/config.yaml`). Se crea automáticamente en la primera ejecución
   copiando la plantilla de fábrica, con un mensaje que indica el nombre del archivo creado.
4. La plantilla de fábrica: `/usr/share/whispskrid/config.yaml` (instalación de paquete Debian), de lo contrario, la `config/config.yaml`
   incrustada en el proyecto (cubre la ejecución desde un archivo tarball de origen sin un directorio `.git`).

El archivo resuelto puede ser **parcial**: cualquier clave que se omita tomará el valor de la plantilla predeterminada, y las claves se fusionarán una por una (las secciones anidadas se fusionan recursivamente; solo es necesario repetir los elementos que se desean modificar, nunca todo el bloque).

Estructura general de `config.yaml`.

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

## Secciones de configuración en detalle.

### `default_language`

Fuerza el idioma de la interfaz y el idioma del reconocimiento de voz.  Un valor vacío
(el valor predeterminado de fábrica) significa: interfaz en el idioma del sistema,
reconocimiento de voz en la detección automática de idioma de Whisper. Se puede
anular por sesión con `-l`/`--lang`.

```yaml
default_language: ""
```

### `backend`

Selecciona el motor de reconocimiento de voz. `faster-whisper` es el único valor aceptado en la versión 0.1.0; la clave está reservada para un segundo backend en el futuro (`whisper.cpp`).

- **`name`** (cadena de texto): `"faster-whisper"`, el único valor aceptado.
- **`beam_size`** (entero, valor predeterminado `5`): ancho del haz que se pasa a `WhisperModel.transcribe()`. Valores más altos pueden mejorar la precisión a costa de la latencia.

```yaml
backend:
  name: "faster-whisper"
  beam_size: 5
```

### `models`

¿Qué modelo de Whisper cargar y cómo hacerlo?

- **`default`** (string, valor predeterminado `"base"`): un nombre de modelo corto (`tiny`,
  `base`, `small`, `medium`, `large-v3`, y sus variantes `.en`), resuelto
  dentro de `models.dir`, o una ruta absoluta a un directorio de modelos. Se puede
  anular por sesión con `--model`.
- **`dir`** (string, valor predeterminado: cadena vacía): el directorio de modelos gestionados.  Una cadena vacía
  significa: resolver automáticamente, en orden.
  `$WHISPSKRID_MODELS_DIR` (si está configurado) → `~/.local/share/whispskrid/whisper-models/`
  (si ya contiene un modelo) → `/usr/share/whispskrid/whisper-models/`
  (instalación de paquetes) → `whisper-models/` en la raíz de un repositorio Git; el
  primero de estos que exista y contenga al menos un modelo es el que se utiliza. Si ninguno
  existe, se crea el directorio del usuario y se utiliza como destino para
  `--download-model`.
- **`device`** (string, valor predeterminado `"auto"`): `"cpu"`, `"cuda"`, o `"auto"`
  (dejar que `faster-whisper` decida).
- **`compute_type`** (string, valor predeterminado `"auto"`): `"int8"`,
  `"int8_float16"`, `"float16"`, o `"auto"` (`int8` en CPU, `float16` en
  CUDA).

```yaml
models:
  default: "base"
  dir: ""
  device: "auto"
  compute_type: "auto"
```

### `capture`

- **`max_seconds`** (entero, valor por defecto `300`): límite de seguridad. Si la
  tecla de push-to-talk se mantiene presionada durante más de este número de segundos, la
  grabación se detiene automáticamente, se transcribe y se inyecta lo que se grabó,
  y se registra una advertencia. Esto sirve como protección contra una tecla atascada
  o un búfer de audio ilimitado, no como un temporizador de comodidad para el
  uso normal.

```yaml
capture:
  max_seconds: 300
```

### `audio`

Parámetros para el flujo de entrada del micrófono, que se abren una vez al inicio de la sesión y se mantienen abiertos entre las dictados.

- **`sample_rate`** (entero, valor predeterminado `16000`): debe coincidir con la tasa que Whisper espera.
- **`channels`** (entero, valor predeterminado `1`): mono.
- **`frames_per_buffer`** (entero, valor predeterminado `4096`): granularidad de lectura de PortAudio; también es la unidad de redondeo de `capture.max_seconds` y de la duración de un episodio grabado.

```yaml
audio:
  sample_rate: 16000
  channels: 1
  frames_per_buffer: 4096
```

### `vad`

Reservado para una futura función de parada automática basada en el silencio. **No implementado en
v0.1.0**: `vad.enabled: true` muestra una advertencia de "no implementado" y
la herramienta continúa funcionando como un sistema de "push-to-talk" estricto (la tecla que se mantiene es lo único que inicia y detiene la grabación).

```yaml
vad:
  enabled: false
  silence_ms: 800
```

`post_processing`

Whisper formatea automáticamente las oraciones, añadiendo signos de puntuación y mayúsculas; el procesamiento posterior de WhispSkrid es deliberadamente mínimo.

- **`trim`** (booleano, valor predeterminado: `true`): eliminar los espacios en blanco al principio y al final
  del texto transcrito.
- **`capitalize_sentence_start`** (booleano, valor predeterminado: `true`): forzar
  la mayúscula en la primera letra del texto inyectado; a veces
  Whisper la omite en un fragmento corto.

```yaml
post_processing:
  trim: true
  capitalize_sentence_start: true
```

### `hotkeys`

- **`pynput_enabled`** (booleano, valor predeterminado `true`): inicia el listener global de `pynput`. `pynput` observa el servidor X, por lo que se inicia cada vez que uno está disponible (establecido con `DISPLAY`), en cualquier tipo de sesión; bajo Wayland, solo ve los eventos de teclado para las ventanas que se ejecutan a través de XWayland, nunca una ventana nativa de Wayland con foco. Establece en `false` para que nunca se inicie y controle la herramienta solo a través de los subcomandos de control vinculados a los atajos de tu escritorio.
- **`push_to_talk`** (lista, valor predeterminado `["shift_r"]`): la tecla de "push-to-talk".
  Mantener presionada → captura; al soltar → transcribe e inyecta (en `mode: hold`, ver abajo). `pynput` distingue la pulsación de la liberación de forma nativa, por lo que la semántica de "mantener presionado" es exacta en esta ruta. Los subcomandos de socket de control (`--dictate`, `--dictate-stop`, `--toggle`) existen para los escritorios cuyo sistema de atajos no puede transmitir "tecla mantenida", donde actúan como un interruptor de inicio/parada en su lugar.
- **`min_hold_ms`** (entero, milisegundos, valor predeterminado `250`): en `mode: hold` solo, si se libera una pulsación antes de este retraso, se cancela la captura en lugar de transcribirla e inyectarla; esto evita una pulsación breve e involuntaria de la tecla vinculada (por ejemplo, un atajo de escritorio que comparte la misma tecla) que, de otro modo, abriría una captura en ruido de fondo o silencio, lo que Whisper podría interpretar como texto. No tiene ningún efecto fuera de `mode: hold`.
- **`mode`** (uno de `hold`, `toggle`, o `armed`, valor predeterminado `hold`): lo que hace una pulsación de la tecla vinculada. `hold` es el comportamiento descrito anteriormente, protegido por `min_hold_ms`. `toggle` inicia la captura en la primera pulsación y se detiene, transcribe e inyecta en la siguiente pulsación de la misma tecla; la liberación de la tecla no hace nada en este modo. `armed` activa la escucha continua de una frase hablada en la primera pulsación (ver `wakeword` a continuación); una segunda pulsación la desactiva. Puramente aditivo: `push_to_talk` y su semántica de "mantener presionado" no cambian cuando `mode` está ausente o establecido en `hold`.

```yaml
hotkeys:
  pynput_enabled: true
  push_to_talk: ["shift_r"]
  min_hold_ms: 250
  mode: "hold"
```

### `wakeword`

Solo se utiliza cuando `hotkeys.mode` es `armed`. Un sistema de escucha continua con botones:
una breve frase hablada inicia un segmento de grabación, otra lo finaliza e lo inserta, hasta que una segunda pulsación de botón desactiva el sistema.

- **`threshold`** (flotante de 0 a 1, valor predeterminado `0.5`): confianza mínima antes de que una
  frase se considere coincidente.
- **`models_dir`** (cadena de texto, valor predeterminado: vacío): directorio que contiene los
  modelos de frases ( `<lang>_open.onnx` / `<lang>_close.onnx`, un par por idioma).
  Si está vacío, se utilizarán las ubicaciones de instalación estándar.

```yaml
wakeword:
  threshold: 0.5
  models_dir: ""
```

Traduce a español. Solo la traducción, no incluyas tokens como `control_socket`.

Booleano, valor predeterminado `true`. Cuando está habilitado, la sesión en ejecución escucha en un socket Unix en `$XDG_RUNTIME_DIR/whispskrid.sock` (modo `0600`), para que los subcomandos de control puedan controlarla. Establezca en `false` para deshabilitar el socket por completo.

```yaml
control_socket: true
```

`clipboard`

El texto se inyecta colocándolo en el portapapeles y simulando un pegado.

- **`restore`** (booleano, valor predeterminado: `true`): Restaura el contenido anterior del portapapeles del usuario después de pegar. Un portapapeles que no contenga texto (por ejemplo, una imagen) nunca se guarda ni se sobrescribe.
- **`restore_delay_ms`** (entero, valor predeterminado: `400`): Máximo tiempo que la ventana permanece abierta, en pequeños intervalos, para que la aplicación de destino pueda leer la selección antes de que se restaure el portapapeles. La espera finaliza anticipadamente si el portapapeles ya ha cambiado (otro programa lo ha tomado), en cuyo caso la restauración se abandona en lugar de intentarse forzar.
- **`defer_restore`** (booleano, valor predeterminado: `false`): Cuando `true` es verdadero, el portapapeles nunca se restaura directamente; el contenido original, es decir, el contenido que existía antes de la primera dictado de la sesión, se restaura una sola vez, al final de la sesión (o a través de `atexit` en caso de un fallo). Elimina la competencia por el portapapeles que se observa en Wayland con aplicaciones GTK, a costa de que el portapapeles conserve el último segmento dictado entre dos dictados de una sesión activa.
- **`confirm_timeout_ms`** (entero, valor predeterminado: `500`): Tiempo máximo de espera para confirmar que el portapapeles realmente contiene el texto dictado antes de enviar la pulsación de tecla para pegar.

```yaml
clipboard:
  restore: true
  restore_delay_ms: 400
  defer_restore: false
  confirm_timeout_ms: 500
```

### `injection`

El sistema de gestión de pulsaciones de teclas se elige una sola vez, al inicio, mediante una búsqueda directa;
nunca se vuelve a probar antes de cada operación de pegado. La secuencia es **`ydotool`** (si el
ejecutable existe y su demonio responde) → **`xdotool`** (si el ejecutable
existe) → modo degradado (el texto permanece en el portapapeles, pero no se envía ninguna pulsación de tecla).
Consulte las notas de compatibilidad de Wayland del proyecto para saber por qué **`wtype`**
no forma parte intencionadamente de esta secuencia.

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

Ruta absoluta a un archivo de sonido corto para notificaciones (por ejemplo, `.oga`, `.wav`),
reproducido a través de `paplay` para confirmar el inicio de la grabación. Un valor vacío o la falta de `paplay` desactiva silenciosamente el sonido.

```yaml
sound_file: "/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga"
```

### `theme`

Tema de color de la consola. Los valores deben ser nombres de color `colorama` válidos (por ejemplo, `GREEN`, `RED`, `BLUE`, `RESET`).

- **`ready_message`**: color del banner de "listo".
- **`help_text`**, **`help_title`**: colores del mensaje de ayuda.
- **`info`**, **`success`**, **`warning`**, **`error`**: colores del mensaje de estado.

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
