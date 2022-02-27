from sdl2 import *
from ._geometry import Rectangle
from ._error import UIError
from . import display
from typing import Optional, Union
from ._event_thread import _event_thread, get_delegate_from_args
from threading import current_thread, RLock, Event, Thread

_window_map = {}
_window_map_lock = RLock()
_window_thread = None
_window_thread_event = Event()


def _window_thread_function():
    while len(_window_map) > 0:
        _window_thread_event.clear()
        _window_thread_event.wait()


def _on_window_added():
    global _window_thread
    if _window_thread is None or not _window_thread.is_alive():
        _window_thread = Thread(target=_window_thread_function, daemon=False, name='UI Window Lifeline Thread')
        _window_thread.start()


def _on_window_removed():
    _window_thread_event.set()


class WindowPosition:
    def __init__(self, /, x: int, y: int, width: Optional[int] = None, height: Optiona[int] = None, display: Optional[int] = 0):
        self._args = [x, y, w, h]
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


def get_arguments_from_position(position: WindowPosition):
    args = position._args
    if args[2] is None or args[3] is None:
        bounds = display.usable_bounds(position._display)
        if args[2] is None:
            args[2] = bounds.width // 2
        if args[3] is None:
            args[3] = bounds.height // 2
    return args


class WindowDatabase(type):
    """
    Ensure one instance per window. Calling Window(<id>) multiple times will return the same object.
    """

    def __call__(self, id: int):
        if _event_thread is None or not _event_thread.is_alive() or current_thread() is not _event_thread:
            raise RuntimeError('Window() cannot only be called from the UIEvent thread. Use Window.create() instead.')
        with _window_map_lock:
            if id in _window_map:
                return _window_map[id]
            raise Window.NotFound('The window with ID [{id}] does not exists or not created with dragiyski.ui.')


class Window(metaclass=WindowDatabase):
    class NotFound(UIError):
        pass

    class FullScreen(Enum):
        WINDOW = 0
        DESKTOP = 1
        REAL = 2

    def __init__(self, id: int, sdl_window: SDL_CreateWindow.restype):
        super().__init__()
        self.__id = id
        self._as_parameter_ = self.__window = sdl_window

    @classmethod
    def create(
        cls,
        *,
        title: Union[str, bytes] = "",
        position: WindowPosition = WindowPosition.undefined(),
        visible: bool = True,
        resizable: bool = True,
        minimized: bool = False,
        maximized: bool = False,
        fullscreen: FullScreen = FullScreen.WINDOWED,
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
            args[5] |= SDL_WINDOW_SHOWN
        else:
            args[5] |= SDL_WINDOW_HIDDEN
        if resizable:
            args[5] |= SDL_WINDOW_RESIZABLE
        if minimized:
            args[5] |= SDL_WINDOW_MINIMIZED
        if maximized:
            args[5] |= SDL_WINDOW_MAXIMIZED
        if fullscreen == Window.FullScreen.DESKTOP:
            args[5] |= SDL_WINDOW_FULLSCREEN_DESKTOP
        elif fullscreen == Window.FullScreen.REAL:
            args[5] |= SDL_WINDOW_FULLSCREEN
        delegate = get_delegate_from_args(kwargs)
        return delegate(cls._create, sdl_args)

    @classmethod
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
        with _window_map_lock:
            self = super().__new__(cls)
            self.__init__(window_id, sdl_window)
            _window_map[id] = self
        _on_window_added()
        return self
