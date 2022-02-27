from sdl2 import SDL_GetError


class UIError(RuntimeError):
    def __init__(self, message: str = None):
        super().__init__(SDL_GetError().decode('utf-8') if message is None else message)
