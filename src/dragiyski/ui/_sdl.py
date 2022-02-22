from sdl2 import *

def ensure_subsystem(flag):
    if not SDL_WasInit(flag):
        SDL_InitSubSystem(flag)

