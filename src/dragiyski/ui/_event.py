from ._thread import event_decorator_factory
from ._window import Window
from sdl2 import *
import sdl2

map_sdl_window_events = dict((getattr(sdl2, x), 'window_' + x.removeprefix('SDL_WINDOWEVENT_').lower()) for x in dir(sdl2) if x.startswith('SDL_WINDOWEVENT_'))


class Event:
    def __init__(self, type: str, timestamp, *args, **kwargs):
        self.timestamp = stimestamp
        self.type = type


class DisplayEvent(Event):
    def __init__(self, *, display, **kwargs):
        super().__init__(**kwargs)
        self.display = display


class DisplayOrientationEvent(DisplayEvent):
    def __init__(self, orientation, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.orientation = orientation


class WindowEvent(Event):
    def __init__(self, window: Window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = window


class WindowPositionEvent(WindowEvent):
    def __init__(self, x: int, y: int, *args):
        super().__init__(*args, **kwargs)
        self.x = x
        self.y = y


class WindowSizeEvent(WindowEvent):
    def __init__(self, width: int, height: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = width
        self.height = height


def create_event(sdl_event: SDL_Event):
    type = None
    Class = None
    args = {}
    if sdl_event.type == SDL_DISPLAYEVENT:
        Class = DisplayEvent
        args['display'] = sdl_event.display.display
        if event.display.event == SDL_DISPLAYEVENT_CONNECTED:
            type = 'display_connected'
        elif event.display.event == SDL_DISPLAYEVENT_DISCONNECTED:
            type = 'display_disconnected'
        elif event.display.event == SDL_DISPLAYEVENT_ORIENTATION:
            Class = DisplayOrientationEvent
            type = 'display_orientation'
            args['orientation'] = sdl_event.display.data1
        else:
            return None
    elif sdl_event.type == SDL_WINDOWEVENT:
        Class = WindowEvent
        args['type'] = map_sdl_window_events[sdl_event.window.event]
        try:
            args['window'] = Window(sdl_event.window.windowID)
        except Window.NotFound:
            return None
        if sdl_event.window.event in [SDL_WINDOWEVENT_RESIZED, SDL_WINDOWEVENT_SIZE_CHANGED]:
            Class = WindowSizeEvent
            args['width'] = event.window.data1
            args['height'] = event.window.data2
        elif sdl_event.window.event == SDL_WINDOWEVENT_MOVED:
            Class = WindowPositionEvent
            args['x'] = event.window.data1
            args['y'] = event.window.data2

        
