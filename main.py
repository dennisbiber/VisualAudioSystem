import argparse
import numpy as np
import pygame
import sounddevice as sd
import sys

from audio_engine import AudioEngine
from controls import ControlEngine
from modulator import Modulator
from shader_core import VisualSynthRenderer

AUDIO_FILE = sys.argv[-1]

def ArgParser():
    parser = argparse.ArgumentParser(description="Argument Handler.")
    parser.add_argument(
        "-i", 
        "--input_file", 
        type=str, 
        required=False, 
        help="The path to the input audio file (e.g., .wav, .mp3)"
    )

    parser.add_argument("--testing", 
                        action="store_true",
                        help="Enable testing mode (sets mode to True)")

    args = parser.parse_args()
    return args

# =========================================================
# MAIN
# =========================================================

def main(args):

    pygame.init()

    pygame.display.set_mode(
        (0,0),
        pygame.FULLSCREEN | pygame.OPENGL | pygame.DOUBLEBUF
    )

    clock = pygame.time.Clock()

    testing = args.testing

    if testing:
        audio = AudioEngine(
            use_file=True,
            filename=args.input_file
        )
        audio.start()
    else:
        audio = AudioEngine(
            use_file=False,
            device="USB Audio Device",
            samplerate=sd.query_devices('USB Audio Device', 'input')["default_samplerate"]
        )
        audio.start()

    mod = Modulator()
    renderer = VisualSynthRenderer(mod)

    controls = ControlEngine(
        "controls.yml",
        context={
            "mod": mod,
            "audio": audio,
            "renderer": renderer
        }
    )

    running = True

    while running:

        dt = clock.tick(120) / 1000.0

        for e in pygame.event.get():

            if e.type == pygame.QUIT:
                running = False

            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False
            # ==============================
            # SYSTEM
            # ==============================
            controls.handle_event(e)
            controls.update(dt)

        mod.update_from_audio(audio, dt)
        renderer.render()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    args = ArgParser()
    main(args)
