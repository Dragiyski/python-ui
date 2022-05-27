from typing import Callable
from ._thread import event_listeners, event_listener_lock
from ._window import Window
from sdl2 import *
import sdl2

event_listener_by_type = dict()
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
    args = {
        'timestamp': event.common.timestamp,
        'type': type
    }
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
    if type is not None and Class is not None:
        return Class(**args)


def dispatch_event(name: str, event: Event):
    pass


class EventListenerType(type):
    """
    Used with event_listener_by_type to ensure a listener to the same type+function produce the same object.
    As a result, adding an event listener twice with the same type+function would not result in double-call.
    """
    def __call__(cls, event_type: str, function: Callable):
        if event_type not in event_listener_by_type:
            type_map = event_listener_by_type[event_type] = dict()
        if function in type_map:
            if cls is EventListenerOnce or not isinstance(type_map[function], EventListenerOnce):
                return type_map[function]
            # Current state is EventListenerOnce while the request is for EventListener
            # In this case the function is promoted to EventListener class, replacing EventListenerOnce
        self = super(EventListenerType, cls).__call__(event_type, function)
        type_map[function] = self
        return self


class EventListener(metaclass=EventListenerType):
    def __init__(self, event_type: str, function: Callable):
        # We intentionally do not add self to listeners, this will be done by the decorators.
        # The user can retrieve the listener by calling EventListener("type", func),
        # and since this is light-weight object, it doubles as dummy EventListener.
        self.__event_type = event_type
        self.__function = function

    def __call__(self, *args, **kwargs):
        return self.__function(*args, **kwargs)

    @property
    def type() -> str:
        return self.__event_type

    @property
    def function() -> Callable:
        return self.__function

    def remove():
        with event_listener_lock:
            if self.__event_type in event_listener_by_type:
                type_map = event_listener_by_type[self.__event_type]
                if self.__function in type_map:
                    del self.__function[type_map]
                    if len(type_map) <= 0:
                        del event_listener_by_type[self.__event_type]
            event_listeners.remove(self)


class EventListenerOnce(EventListener):
    def __call__(self, *args, **kwargs):
        self.remove()
        return super().__call__(*args, **kwargs)


def event_decorator_factory(event_type: str):
    def event_decorator_optional_arguments(*args, once=False, **kwargs):
        def event_decorator(function: Callable):
            with event_listener_lock:
                listener = Class(event_type, function)
                event_listeners.add(listener)
            return function
        if len(kwargs) == 0 and len(args) == 1 and callable(args[0]):
            return event_decorator(args[0])
        return event_decorator


def on_display_connected(*args, **kwargs):
    return event_decorator_factory('display_connected')(*args, **kwargs)


def on_display_disconnected(*args, **kwargs):
    return event_decorator_factory('display_disconnected')(*args, **kwargs)
