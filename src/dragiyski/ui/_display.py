from sdl2 import *
import sdl2
from enum import Enum
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
    if SDL_GetCurrentDisplayMode(display, storage) < 0:
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
    if SDL_GetDisplayMode(display, mode, storage) < 0:
        raise UIError
    return create_display_mode(storage)

def modes(display: int):
    validate_display_index(display)
    c = mode_count(display)
    return [mode(display=display, mode=x) for x in range(c)]
        