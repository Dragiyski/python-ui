from sdl2 import *
from ._error import UIError
from ._event_thread import get_delegate_from_args
from ._sdl import ensure_subsystem

def count(**kwargs):
    delegate_call = get_delegate_from_args(kwargs)
    return delegate_call(_sdl_num_video_displays)

def name(index: int, **kwargs):
    delegate_call = get_delegate_from_args(kwargs)
    return delegate_call(_sdl_display_name, index)

def _sdl_num_video_displays():
    ensure_subsystem(SDL_INIT_VIDEO)
    return SDL_GetNumVideoDisplays()

def _sdl_display_name(index):
    ensure_subsystem(SDL_INIT_VIDEO)
    count = SDL_GetNumVideoDisplays()
    if count > 0 and index >= count:
        raise IndexError(f'index must be in range [0, {count - 1}]')
    name = SDL_GetDisplayName(index)
    if name is None:
        raise UIError
    return name.decode('utf-8')
