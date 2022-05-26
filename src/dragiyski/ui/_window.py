from sdl2 import *
from enum import Enum
from ._geometry import Rectangle
from ._error import UIError
from ._thread import window_map, window_map_lock, event_thread, in_event_thread
from . import display
from typing import Optional, Union
import threading


class WindowDatabase(type):
    """
    Ensure one instance per window. Calling Window(<id>) multiple times will return the same object.
    """

    def __call__(self, id: int):
        if not event_thread.is_alive() or threading.current_thread() is not event_thread:
            raise RuntimeError('Window() cannot only be called from the UIEvent thread. Use Window.create() instead.')
        with window_map_lock:
            if id in window_map:
                return window_map[id]
            raise Window.NotFound('The window with ID [{id}] does not exists or not created with dragiyski.ui module.')


class Window(metaclass=WindowDatabase):
    class Position:
        def __init__(self, /, x: int, y: int, width: Optional[int] = None, height: Optional[int] = None, display: Optional[int] = 0):
            self._args = [x, y, width, height]
            self._display = display

        @classmethod
        def from_rectangle(cls, position: Rectangle):
            return cls(position.x, position.y, position.width, position.height)

        @classmethod
        def centered(cls, width: Optional[int] = None, height: Optional[int] = None):
            return cls(SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, width, height)

        @classmethod
        def centered_at(cls, display: int, width: Optional[int] = None, height: Optional[int] = None):
            return cls(SDL_WINDOWPOS_CENTERED_DISPLAY(display), SDL_WINDOWPOS_CENTERED_DISPLAY(display), width, height, display)

        @classmethod
        def undefined(cls, width: Optional[int] = None, height: Optional[int] = None):
            return cls(SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, width, height)

        @classmethod
        def centered_at(cls, display: int, width: Optional[int] = None, height: Optional[int] = None):
            return cls(SDL_WINDOWPOS_UNDEFINED_DISPLAY(display), SDL_WINDOWPOS_UNDEFINED_DISPLAY(display), width, height, display)

    class NotFound(UIError):
        pass

    class Mode(Enum):
        WINDOW = 0
        DESKTOP = 1
        FULLSCREEN = 2

    @classmethod
    def create(
        cls,
        *,
        title: Union[str, bytes] = "",
        position: Position = Position.undefined(),
        visible: bool = True,
        resizable: bool = True,
        minimized: bool = False,
        maximized: bool = False,
        window_mode: Mode = Mode.WINDOW,
        **kwargs
    ):
        """Creates a window.

        Args:
            title (Union[str, bytes], optional): The window title, displayed in the title bar.
            position (WindowPosition, optional): The window position and size.
            visible (bool, optional): Should the window be visible immediately? Hidden windows are not shown anywhere, including into the window list.
            resizable (bool, optional): Whether the window can be resized by the user using the window borders by default.
            minimized (bool, optional): Should the window be minimized on creation. Minimized windows are hidden, but appear in the window list.
            maximized (bool, optional): Should the window be maximized on creation. Maximized windows expands to useable bounds of the display, but can be restored to their original size.
            fullscreen (FullScreen, optional): Determines whether and how to display the window in the display.
        """
        if isinstance(title, str):
            title = title.encode('utf-8')
        sdl_args = [title, *get_arguments_from_position(position), 0]
        if visible:
            sdl_args[5] |= SDL_WINDOW_SHOWN
        else:
            sdl_args[5] |= SDL_WINDOW_HIDDEN
        if resizable:
            sdl_args[5] |= SDL_WINDOW_RESIZABLE
        if minimized:
            sdl_args[5] |= SDL_WINDOW_MINIMIZED
        if maximized:
            sdl_args[5] |= SDL_WINDOW_MAXIMIZED
        if window_mode == Window.Mode.DESKTOP:
            sdl_args[5] |= SDL_WINDOW_FULLSCREEN_DESKTOP
        elif window_mode == Window.Mode.FULLSCREEN:
            sdl_args[5] |= SDL_WINDOW_FULLSCREEN
        cls._create(sdl_args)

    @classmethod
    @in_event_thread
    def _create(cls, sdl_args):
        SDL_ClearError()
        sdl_window = SDL_CreateWindow(*sdl_args)
        if sdl_window is None:
            raise UIError
        try:
            sdl_window.contents
        except:
            raise UIError
        SDL_ClearError()
        window_id = SDL_GetWindowID(sdl_window)
        if id == 0:
            message = SDL_GetError().decode('utf-8')
            SDL_DestroyWindow(sdl_window)
            raise UIError(message)
        return cls._from_sdl_window(cls, sdl_window, window_id)

    def _from_sdl_window(cls, sdl_window, window_id):
        with window_map_lock:
            self = super().__new__(cls)
            self.__window = sdl_window
            self.__id = window_id
            self.__event_listener_lock = threading.RLock()
            self.__event_listener_by_type = dict()
            window_map[window_id] = self
        return self

    @in_event_thread
    def destroy(self):
        if self.__id is None:
            return
        SDL_DestroyWindow(self.__window)
        self.__id = None
        with self.__event_listener_lock:
            for type_map in self.__event_listener_by_type.values():
                for listener in type_map.values():
                    listener.remove()



def get_arguments_from_position(position: Window.Position):
    args = position._args
    if args[2] is None or args[3] is None:
        bounds = display.usable_bounds(position._display)
        if args[2] is None:
            args[2] = bounds.width // 2
        if args[3] is None:
            args[3] = bounds.height // 2
    return args
