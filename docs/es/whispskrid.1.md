% WHISPSKRID(1) whispskrid | Comandos de usuario
% Ronan Davalan
% 2026-09-11

# NOMBRE

whispskrid: dictado offline y a nivel de sistema, activado por pulsación de tecla (push-to-talk), para la línea de comandos.

# SINOPSIS

**whispskrid** [**-l** *LANG* | **--lang** *LANG*] [**--model** *NAME*]

**whispskrid** **\--diagnose**

**whispskrid** **\--download-model** [*NAME*]

**whispskrid** {**\--dictate** | **\--dictate-stop** | **\--toggle** | **\--cancel** | **\--status** | **\--stop**}

**whispskrid** **\--version**

# DESCRIPCIÓN

**whispskrid** es una herramienta de dictado por línea de comandos para Linux, impulsada por el motor de reconocimiento de voz offline **Whisper** (**faster-whisper**). La captura es estrictamente "push-to-talk": el audio se graba solo mientras se mantiene presionada una tecla (o, equivalentemente, entre un comando **\--dictate** y un comando **\--dictate-stop**), y el texto reconocido se inyecta directamente en la ventana que actualmente tiene el foco del teclado, ya sea una terminal, un navegador, un editor o cualquier otra aplicación, por lo que funciona a nivel de sistema en lugar de dentro de un solo programa.

Todo el reconocimiento de voz se realiza localmente: ni el audio ni el texto transcrito se envían nunca a un servicio remoto.

Solo una sesión se ejecuta por usuario a la vez. Cuando se inicia sin una bandera de control, se crea una sesión residente: se carga el modelo, se abre un socket de control Unix privado en `$XDG_RUNTIME_DIR/whispskrid.sock` (modo `0600`), y se inicia un listener de teclas de acceso rápido `pynput` si está habilitado. El mismo comando invocado con una bandera de control (ver CONTROLANDO UNA SESIÓN EN EJECUCIÓN) se conecta a ese socket en lugar de iniciar una nueva sesión.

Se inyecta el texto colocándolo en el portapapeles y simulando un pegado, por lo que se necesitan dos tipos de herramientas: un simulador de pulsaciones de teclas y una herramienta de portapapeles. Bajo Wayland, esto es **ydotool** (necesita el demonio `ydotoold` y acceso a `/dev/uinput`) más **wl-clipboard**; bajo X11, es **xdotool** más **xclip**. Sin ninguno de estos backends, la inyección recurre a un modo degradado. La elección entre ambos se hace una sola vez, al iniciar, comprobando directamente cuál de los dos binarios y su demonio responde realmente — no verificando el tipo de sesión de forma directa. **whispskrid \--diagnose** informa qué herramientas, dispositivo de audio y acceso al portapapeles están disponibles, y luego finaliza.

# INSTALACIÓN

Instale el paquete Debian:

```
sudo dpkg -i whispskrid_<version>_all.deb
```

El paso postinst instala **faster-whisper** mediante pip e informa de su
propio progreso; los `Recommends` del paquete cubren el backend de
inyección adecuado para su tipo de sesión (**ydotool** + **wl-clipboard**
en Wayland, **xdotool** + **xclip** en X11) — ninguno es una dependencia
estricta, por lo que un entorno incompleto se instala igualmente, al
precio de un modo de inyección degradado (véase **\--diagnose** más
abajo).

El paquete no incluye ningún modelo Whisper. Descargue uno antes del
primer uso — los modelos provienen de las conversiones CTranslate2
oficiales alojadas en Hugging Face (*https://huggingface.co/Systran*),
obtenidas automáticamente en el directorio de modelos gestionado (véase
ARCHIVOS más abajo):

```
whispskrid --download-model
```

Omitir este paso no es grave: la sesión persistente descarga ella misma
el modelo por defecto en el primer arranque, anunciándolo antes — la
descarga desde Hugging Face no muestra ninguna barra de progreso, y una
transferencia de varios cientos de Mo quedaría sin actividad visible.

Luego verifique el entorno:

```
whispskrid --diagnose
```

Atajos globales a través de `pynput` observando el servidor X: bajo Wayland, solo alcanzan las
ventanas que se ejecutan a través de XWayland, nunca una ventana nativa de Wayland que tenga el foco.
Asigna los subcomandos de control a la configuración de atajos propia de tu escritorio para
un control que funcione en todas partes.

# OPCIONES

-l *LANG*, **\--lang** *LANG*
:   Fuerza el idioma de la interfaz y el reconocimiento de voz para esta sesión
    (`en`, `fr`, `de` o `es`), anulando el valor de `default_language` del
    archivo de configuración. También selecciona el idioma de los propios mensajes
    de la interfaz de línea de comandos (incluido el texto de ayuda).

**\--model** *NOMBRE*
:   Sustituye `models.default` del archivo de configuración para esta sesión: un nombre corto del modelo (por ejemplo, `base`) o una ruta en el sistema de archivos.

**\--diagnose**
:   Verifique el entorno (tipo de sesión, backend de inyección, herramientas, GPU/CUDA,
    presencia del modelo, entrada de audio, portapapeles, socket de control, configuración)
    y salga. El estado de salida es `0` cuando todas las verificaciones que pueden bloquear la ejecución se aprueban; algunas
    verificaciones (aceleración de la GPU, presencia de `ydotool`/`xdotool`) son solo informativas y nunca bloquean el estado de salida.

**\--download-model** [*NOMBRE*]
:   Descargue un modelo de Whisper (`base` cuando *NOMBRE* se omite; uno
    de `tiny`, `base`, `small`, `medium`, `large-v3`, o sus variantes
    `.en`) desde Hugging Face al directorio de modelos gestionado
    (`~/.local/share/whispskrid/whisper-models/` por defecto — véase
    ARCHIVOS), y luego salga. Un modelo ya descargado se detecta y la
    operación se omite.

**\--version**
:   Imprimir el número de versión y salir.

# CONTROLANDO UNA SESIÓN EN CURSO

Cada una de las siguientes opciones de línea de comandos se conecta al socket de la sesión en ejecución,
ejecuta la acción, imprime la respuesta resultante (`OK`, `OK <text>` o
`ERR <reason>`), y finaliza con el código de estado `0` en `OK`, y con `1` en caso contrario. Están
diseñadas para ser asignadas a atajos de teclado del escritorio.

**\--dictate**
:   Iniciar captura. Falla con `ERR already-capturing` si ya se está llevando a cabo una captura.

**\--dictate-stop**
:   Detener la captura actual, transcribirla e inyectar el resultado. Falla
    con `ERR not-capturing` si no hay una captura en progreso.

**\--toggle**
:   **\--dictate** o **\--dictate-stop**, dependiendo del estado actual de la sesión; un atajo único para una tecla de "presionar para iniciar/detener" o "presionar para hablar" que está configurada a nivel del escritorio.

**\--cancel**
:   Descartar la captura en curso sin transcribir ni inyectar
    nada.

**\--status**
:   Imprime el estado actual de la sesión (`state=idle|capturing model=<name>
    language=<lang|auto>`) sin modificarlo.

**\--stop**
:   Cerrar la sesión activa del usuario de forma segura.

# TECLAS DE ACCESO RÁPIDO

`pynput` Los atajos de teclado globales se activan siempre que `hotkeys.pynput_enabled` es
verdadero en el archivo de configuración y un servidor de visualización
sea alcanzable (`DISPLAY` definido) — sea cual sea el tipo de sesión,
Wayland incluido, ya que `pynput` observa por sí mismo el servidor X. El listener no consume el evento de tecla: el golpe de tecla también llega a la ventana enfocada. La configuración de la fábrica asigna la función de "push-to-talk" a:

**Ctrl derecho**
:   Mantener para grabar, soltar para detener; transcribe e inyecta: la semántica nativa de presionar/soltar de `pynput` implementa el sistema de "hablar al presionar" directamente en esta ruta (a diferencia de la ruta del socket de control, que solo ve comandos discretos y, por lo tanto, debe exponer **--toggle** en su lugar).

Las claves restringidas se pueden configurar en `hotkeys.push_to_talk` en el
archivo de configuración (`ctrl_r`, `ctrl_l`, `alt_r`, `alt_l`, `shift_r`,
`shift_l`, `cmd`).

Para cambiar la tecla o teclas asignadas, edite `hotkeys.push_to_talk` en
el archivo de configuración (véase CONFIGURACIÓN más abajo para su ruta
exacta) y reinicie la sesión residente para que el cambio surta efecto:

```
whispskrid --stop
whispskrid
```

# CONFIGURACIÓN

El comportamiento en tiempo de ejecución está controlado por un archivo de configuración YAML que define parámetros predeterminados del lenguaje, el backend y el modelo, la duración máxima de la captura, el dispositivo de audio, el procesamiento posterior y las combinaciones de teclas.

El archivo de configuración se encuentra mediante la primera regla que coincida a continuación; una vez que una regla coincide, las reglas restantes no se consultan.

1. La ruta especificada en la variable de entorno **WHISPSKRID_CONFIG**, si está definida.
   Se utiliza tal cual; nunca se crea automáticamente.
2. `config/config.yaml`, relativo al directorio del proyecto, cuando se ejecuta
   desde un repositorio Git (modo de desarrollo).
3. `$XDG_CONFIG_HOME/whispskrid/config.yaml` (por defecto
   `~/.config/whispskrid/config.yaml`). Se crea automáticamente en la primera ejecución,
   a partir de la plantilla predeterminada.
4. La plantilla predeterminada: `/usr/share/whispskrid/config.yaml` (instalación de paquete Debian), de lo contrario, la `config/config.yaml` incrustada en el proyecto
   (cubre la ejecución desde un archivo tarball de código fuente sin un directorio `.git`).

El archivo resuelto puede ser parcial: cualquier clave que se omita tomará el valor de la plantilla predeterminada y se combinará clave por clave.

El idioma activo se elige, en el siguiente orden: la opción **\--lang**, si se proporciona; de lo contrario, `default_language` del archivo de configuración; de lo contrario, detección automática por el componente de reconocimiento.

Consulte **configuration.md** en la documentación del proyecto para obtener la referencia completa
de cada clave de configuración.

# SOLUCIÓN DE PROBLEMAS

**Modelo no encontrado.** Ejecute **\--diagnose** y lea su línea de
resumen final, que nombra por sí misma la primera verificación
bloqueante — no adivine a partir de la salida en bruto anterior:

```
whispskrid --diagnose
```

Si la línea de resumen nombra la verificación del modelo, descargue uno:

```
whispskrid --download-model
```

Luego vuelva a ejecutar **\--diagnose**; finaliza con el código `0` en
cuanto todas las verificaciones bloqueantes se aprueban (véase ESTADO DE
SALIDA).

# ARCHIVOS

`~/.config/whispskrid/config.yaml`
:   Archivo de configuración por usuario.

`/usr/share/whispskrid/config.yaml`
:   Plantilla de configuración de fábrica (instalación de paquete Debian), de solo lectura.

`~/.local/share/whispskrid/whisper-models/`
:   Directorio predeterminado gestionado para los modelos Whisper descargados.

`config/config.yaml`
:   Archivo de configuración que se utiliza al ejecutar desde un repositorio Git.

`whisper-models/`
:   Ubicación predeterminada donde se buscan los modelos de Whisper al ejecutar desde un
    clon de Git o un archivo tarball de código fuente.

`$XDG_RUNTIME_DIR/whispskrid.sock`
:   Control de socket de la sesión en ejecución (modo `0600`).

# ESTADO DE SALIDA

**0**
:   El programa finalizó correctamente, o se recibió un comando de control `OK`.

No nulo
:   El inicio falló (no hay un backend de inyección, modelo o dispositivo de audio disponible),
    o se recibió un comando de control `ERR`.

# EJEMPLOS

Inicia una sesión para residentes utilizando el idioma predeterminado del archivo de configuración:

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

Reporte los errores en el rastreador de problemas del proyecto:
*https://github.com/RonanDavalan/whispskrid/issues*

# AUTOR

Ronan Davalan, y los colaboradores que figuran en CONTRIBUTORS.md.
