from sdl2 import *
from ._error import UIError
from ._event_thread import delegate_sync_call
from ._sdl import ensure_subsystem

def count():
    if not SDL_WasInit(SDL_INIT_VIDEO):
        delegate_sync_call(SDL_InitSubSystem, SDL_VideoInit)
    count = SDL_GetNumVideoDisplays()
    if count < 0:
        raise UIError

def name(index: int):
    if not SDL_WasInit(SDL_INIT_VIDEO):
        delegate_sync_call(SDL_InitSubSystem, SDL_VideoInit)
    count = SDL_GetNumVideoDisplays()
    if count < 0:
        raise UIError
    elif count == 0:
        raise IndexError(f'No displays found')
    if index < 0 or index >= count:
        raise IndexError(f'Index must be in range [0, {count - 1}]')
    buffer = SDL_GetDisplayName(index)
    if buffer is None:
        raise UIError
    return buffer.decode('utf-8')
