from sdl2 import *
from ._error import UIError
from ._event_thread import delegate_sync_call
from ._sdl import ensure_subsystem

def count() -> int:
    if not SDL_WasInit(SDL_INIT_VIDEO):
        delegate_sync_call(SDL_InitSubSystem, SDL_INIT_VIDEO)
    count = SDL_GetNumVideoDisplays()
    if count < 0:
        raise UIError
    return count

def name(index: int) -> str:
    c = count()
    if c < 0:
        raise UIError
    elif c == 0:
        raise IndexError(f'No displays found')
    if index < 0 or index >= c:
        raise IndexError(f'Index must be in range [0, {count - 1}]')
    buffer = SDL_GetDisplayName(index)
    if buffer is None:
        raise UIError
    return buffer.decode('utf-8')

