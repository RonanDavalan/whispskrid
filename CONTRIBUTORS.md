# Acknowledgments and Contributors

WhispSkrid could not exist without the people and models who worked on it, and
the open-source projects it stands on. Roles are written down here to reflect
the work actually done, not a single vague "AI assistance" line. This list is
updated as people contribute, not at release time.

## Design and Development

*   **Ronan Davalan** — Architect and arbiter. Product vision, requirements, decisions, validation and testing. All architectural decisions are validated by him.
*   **Claude Code (Anthropic)** — Systems engineer and lead developer. Principal author of the source code, the Debian/RPM/Arch packaging, the internal tooling, the documentation and the website.
*   **Gemini (Google)** — Synthesizer and strategic advisor. Architectural analysis, logical conflict resolution, co-writing of the collaboration rules; occasional measurement runs.
*   **Muse Spark 1.3 (Contributor Free)** — Usage tester. Command-line trials, installation of the `.deb` package on a second machine, reading the documentation in four languages.
*   **DeepSeek V4 Flash (via OpenCode)** — Tester and reviewer. Installation on a Raspberry Pi (aarch64), review of documentation and website copy.
*   **Grok (xAI)** — External validator. Critical review of hypotheses, editorial audit of the PDF manuals.
*   **translategemma 12B (Google, run locally with Ollama)** — Machine translation of the user manual into English, German and Spanish.

## Heritage

WhispSkrid started from the framework of
[vosk-cli-dictation](https://github.com/RonanDavalan/vosk-cli-dictation) and is
now independent. The people and models credited in that project's
[CONTRIBUTORS.md](https://github.com/RonanDavalan/vosk-cli-dictation/blob/main/CONTRIBUTORS.md)
shaped the working method it was born from, including the blind cross-audit of
its interaction core (GLM-5.3, among others).

## Core Projects and Libraries

*   **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** (SYSTRAN) and **CTranslate2**: the speech recognition engine.
*   **[OpenAI Whisper](https://github.com/openai/whisper)**: the models.
*   **[Python](https://www.python.org/)**, **[PyYAML](https://pyyaml.org/)**, **[NumPy](https://numpy.org/)**, **[pynput](https://pynput.readthedocs.io/)**, **[PyAudio](https://pypi.org/project/PyAudio/)**, **[pyperclip](https://github.com/asweigart/pyperclip)**.
*   **[xdotool](https://github.com/jordansissel/xdotool)**, **[wtype](https://github.com/atx/wtype)**, **[wl-clipboard](https://github.com/bugaevc/wl-clipboard)**, **[ydotool](https://github.com/ReimuNotMoe/ydotool)**: keystroke injection and clipboard on X11 and Wayland.

## Code and Documentation Contributors

People who contributed through pull requests or issues will be listed here.

*(No outside contribution yet — your name could be the first.)*

---
*To contribute, open an issue on the [issue tracker](https://github.com/RonanDavalan/whispskrid/issues) before sending a large change.*
