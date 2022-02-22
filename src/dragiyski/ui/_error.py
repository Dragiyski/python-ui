from sdl2 import SDL_GetError

class UIError(RuntimeError):
    def __init__(self):
        super().__init__(SDL_GetError())
