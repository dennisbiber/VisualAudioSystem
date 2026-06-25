# VisualAudioSystem

A real-time, audio-reactive **video synthesizer**. It renders generative visuals on the GPU and modulates them live from audio — a file or a microphone/line input — and from keyboard control, with a MIDI control layer planned.

## What it is

A performance instrument for visuals. A GLSL fragment shader generates the image — procedural gradients, layered noise, stars, aurora, lightning, a domain-warp lens — composited over still-image or video backgrounds, and every parameter is driven each frame by a modulation system fed from live audio analysis and your inputs. The architecture is deliberately decoupled: audio analysis, modulation, rendering, and control are separate engines that communicate through one shared state object and a single YAML config.

## Architecture

| Module | Role |
|--------|------|
| `audio_engine.py` | Real-time audio analysis — RMS level, bass energy, and transients — from either a played-back file or a live input device, via `sounddevice` + NumPy FFT. |
| `shader_core.py` | The renderer: an OpenGL fragment shader (via `moderngl`) for the generative visuals, plus still-image and video background loading (`Pillow` / OpenCV) with crossfade transitions. Stateless by design — it reads the modulator every frame. |
| `modulator.py`, `mod_primitives.py` | The modulation matrix: sine/triangle/square **LFOs** and **ADSR-style envelopes** — the same primitives a sound synth uses, applied to visuals — plus per-frame rules and expressions that map audio and modulation onto visual parameters. |
| `safe_expr.py` | A sandboxed AST expression evaluator, so config-defined math can be evaluated without executing arbitrary code. |
| `controls.py` | A generic event → action → parameter mapper driven by YAML; written to extend from keyboard to MIDI. |
| `controls.yml` | The single source of truth: variables, LFOs, per-frame rules, key bindings, and actions. |

## Features

- GPU-rendered generative visuals: noise fields, stars, an aurora band, lightning, domain-warp lensing, strobe, and HSV color modulation
- Still-image **and** video backgrounds, with crossfade or instant transitions, scroll, and zoom
- Live audio reactivity defined entirely in config (e.g. brightness tracks bass; transients push energy)
- Synth-style modulation: LFOs and ADSR envelopes running continuously
- Fully data-driven control and modulation — re-map or re-tune by editing `controls.yml`, no code changes
- Two audio sources: play an audio file, or react to a live input device

## Controls

A representative selection — the full map lives in `controls.yml`:

| Key | Action |
|-----|--------|
| `1` / `2` / `3` / `4` | strobe · aurora · lightning pulse · color-mod toggle |
| `Q` / `W` | density down / up |
| `A` / `S` | brightness down / up |
| `Z` / `X` | drift speed down / up |
| `C` / `V` | warp amount down / up |
| arrow keys | move the warp center |
| `[` / `]` | background blend down / up |
| numpad `1`–`5` | select background |
| numpad `+` / `-` | video speed up / down |
| `Esc` | quit |

## Requirements

Python 3, plus:

```bash
pip install moderngl pygame numpy sounddevice soundfile opencv-python Pillow PyYAML
```

A GPU and driver supporting OpenGL 3.3+ are required for the shader.

## Running

**React to an audio file** (testing mode):

```bash
python main.py --testing -i path/to/track.wav
```

**React to a live input device** (defaults to an input named `USB Audio Device`):

```bash
python main.py
```

Both open a fullscreen window. Press `Esc` to exit.

## Roadmap

- **MIDI control** — the control layer is already abstracted as a generic event→action mapper, so adding MIDI input is a matter of feeding MIDI events into the same path the keyboard uses.

## Status

A working real-time instrument. Rendering is OpenGL/GLSL via `moderngl`; audio analysis is lightweight (level, bass, transients) and fully drives the visuals through the config. The control and modulation systems are data-driven and intended to grow — new effects, bindings, and input sources without restructuring the code.
