from sdl2 import *
import sdl2, ctypes
from enum import Enum
from ._error import UIError
from ._event_thread import delegate_sync_call, convert_event_name
from ._sdl import ensure_subsystem
from ._geometry import create_rectangle
from ._event_emitter import EventEmitter

_display_emitter = EventEmitter()

def count() -> int:
    if not SDL_WasInit(SDL_INIT_VIDEO):
        delegate_sync_call(SDL_InitSubSystem, SDL_INIT_VIDEO)
    SDL_ClearError()
    count = SDL_GetNumVideoDisplays()
    if count < 0:
        raise UIError
    return count


def validate_display_index(display: int):
    c = count()
    if c > 0:
        if display >= 0 and display < c:
            return
        raise IndexError(f'param `display` out of range: [0, {c-1}]')
    raise IndexError('param `display` out of range')


def name(display: int) -> str:
    c = count()
    validate_display_index(display)
    SDL_ClearError()
    buffer = SDL_GetDisplayName(display)
    if buffer is None:
        raise UIError
    return buffer.decode('utf-8')


PixelFormat = Enum('PixelFormat', dict([(x.removeprefix('SDL_PIXELFORMAT_'), getattr(sdl2, x)) for x in dir(sdl2) if x.startswith('SDL_PIXELFORMAT_')]))


class DisplayMode:
    def __init__(self, pixel_format: PixelFormat, width: int, height: int, refresh_rate: int):
        self.__impl = SDL_DisplayMode()
        self.__impl.format = pixel_format.value
        self.__impl.w = width
        self.__impl.h = height
        self.__impl.refresh_rate = refresh_rate
        self._as_parameter_ = self.__impl

    @property
    def pixel_format(self):
        return PixelFormat(self.__impl.format)

    @pixel_format.setter
    def pixel_format(self, pixel_format: PixelFormat):
        self.__impl.format = pixel_format.value

    @property
    def width(self):
        return self.__impl.w

    @width.setter
    def width(self, value: int):
        if value < 0:
            raise ValueError('`width` cannot be negative')
        self.__impl.w = value

    @property
    def height(self):
        return self.__impl.h

    @height.setter
    def height(self, value: int):
        if value < 0:
            raise ValueError('`height` cannot be negative')
        self.__impl.h = value

    @property
    def refresh_rate(self):
        return self.__impl.refresh_rate

    @refresh_rate.setter
    def refresh_rate(self, value: int):
        if value < 0:
            raise ValueError('`refresh_rate` cannot be negative')
        self.__impl.refresh_rate = value

    def __repr__(self):
        return f'DisplayMode(pixel_format=PixelFormat.{self.pixel_format.name}, width={self.width}, height={self.height}, refresh_rate={self.refresh_rate})'


def create_display_mode(mode: SDL_DisplayMode):
    wrapper = DisplayMode.__new__(DisplayMode)
    wrapper._DisplayMode__impl = wrapper._as_parameter_ = mode
    return wrapper


def current_mode(display: int) -> DisplayMode:
    validate_display_index(display)
    storage = SDL_DisplayMode()
    SDL_ClearError()
    if SDL_GetCurrentDisplayMode(display, storage) < 0:
        raise UIError
    return create_display_mode(storage)

def desktop_mode(display: int) -> DisplayMode:
    validate_display_index(display)
    storage = SDL_DisplayMode()
    SDL_ClearError()
    if SDL_GetDesktopDisplayMode(display, storage) < 0:
        raise UIError
    return create_display_mode(storage)

def desktop_mode(display: int) -> DisplayMode:
    validate_display_index(display)
    storage = SDL_DisplayMode()
    SDL_ClearError()
    if SDL_GetDesktopDisplayMode(display, storage) < 0:
        raise UIError
    return create_display_mode(storage)

def mode_count(display: int) -> int:
    validate_display_index(display)
    count = SDL_GetNumDisplayModes(display)
    if count < 0:
        raise UIError
    return count

def validate_mode_index(display: int, mode: int):
    c = mode_count(display)
    if mode < 0 or mode >= c:
        raise IndexError('param `mode` out of range: [0, {c}]')

def mode(display: int, mode: int) -> DisplayMode:
    validate_display_index(display)
    validate_mode_index(display, mode)
    storage = SDL_DisplayMode()
    SDL_ClearError()
    if SDL_GetDisplayMode(display, mode, storage) < 0:
        raise UIError
    return create_display_mode(storage)

def modes(display: int):
    validate_display_index(display)
    c = mode_count(display)
    return [mode(display=display, mode=x) for x in range(c)]

def closest_mode(display: int, mode: DisplayMode) -> DisplayMode:
    validate_display_index(display)
    storage = SDL_DisplayMode()
    SDL_ClearError()
    if SDL_GetClosestDisplayMode(display, mode, storage) is None:
        raise UIError
    return create_display_mode(storage)

def dpi(display: int):
    validate_display_index(display)
    ddpi = ctypes.c_float()
    hdpi = ctypes.c_float()
    vdpi = ctypes.c_float()
    SDL_ClearError()
    if SDL_GetDisplayDPI(display, ddpi, hdpi, vdpi) < 0:
        raise UIError
    return (ddpi.value, hdpi.value, vdpi.value)

def bounds(display: int):
    validate_display_index(display)
    result = SDL_Rect()
    SDL_ClearError()
    if SDL_GetDisplayBounds(display, result) < 0:
        raise UIError
    return create_rectangle(result)

def usable_bounds(display: int):
    validate_display_index(display)
    result = SDL_Rect()
    SDL_ClearError()
    if SDL_GetDisplayUsableBounds(display, result) < 0:
        raise UIError
    return create_rectangle(result)

add_event_listener = _display_emitter.add_event_listener
remove_event_listener = _display_emitter.remove_event_listener
_display_event_names = {id: name for (name, id) in [(convert_event_name(x.removeprefix('SDL_DISPLAYEVENT_')), getattr(sdl2.video, x)) for x in dir(sdl2.video) if x.startswith('SDL_DISPLAYEVENT_')]}

def dispatch_event(event: SDL_Event):
    assert event.type == SDL_DISPLAYEVENT
    