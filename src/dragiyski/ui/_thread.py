from sdl2 import *
import sdl2
from queue import Queue, Empty
from typing import Callable
import sys
import threading
import re

event_listeners = set()
event_listener_by_type = dict()
event_listener_lock = threading.RLock()
window_map = dict()
window_map_lock = threading.RLock()
window_count_event = threading.Event()
ui_threads = set()

re_word_to_under = re.compile('(.)([A-Z][a-z]+)')
re_upper_follow = re.compile('([a-z0-9])([A-Z])')
re_replacement = r'\1_\2'

def convert_event_name(name: str):
    name = re.sub(re_word_to_under, re_replacement, name)
    name = re.sub(re_upper_follow, re_replacement, name)
    return name.lower()


class EventTask:
    def __init__(self, function: Callable, /, *args, **kwargs):
        self.__function = function
        self.__args = args
        self.__kwargs = kwargs
        self.__event = threading.Event()
        self.__return = None
        self.__exception = None
        self.__done = False

    def has_exception(self):
        return self.__done and self.__exception is not None

    def exception(self):
        return self.__exception

    def result(self):
        return self.__return

    def done(self):
        return self.__done

    def wait(self):
        if self.__done:
            return
        self.__event.clear()
        self.__event.wait()

    def dispatch(self):
        if self.__done:
            return
        self.__done = True
        try:
            self.__return = self.__function(*self.__args, **self.__kwargs)
        except:
            self.__exception = sys.exc_info()
        finally:
            self.__event.set()

map_sdl_window_events = dict((getattr(sdl2, x), 'window_' + x.removeprefix('SDL_WINDOWEVENT_').lower()) for x in dir(sdl2) if x.startswith('SDL_WINDOWEVENT_'))

class EventThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(EventThread, self).__init__(*args, **kwargs)
        self.__task_queue = Queue(maxsize=0)
        self.__stage = 0
        self.__in_queue = threading.Event()

    def run(self):
        alive_thread_stage1.start()
        self.__stage = 1
        self.__in_queue.set()
        while self.__stage == 1:
            if len(event_listeners) > 0:
                break
            task = self.__task_queue.get()
            task.dispatch()
            self.__task_queue.task_done()
        self.__in_queue.clear()
        if len(event_listeners) + len(window_map) <= 0:
            return
        self.__stage = 2
        self.__command_event = command_event = SDL_RegisterEvents(1)
        if command_event == 0xFFFFFFFF:
            raise UIError
        while self.__stage == 2:
            event = SDL_Event()
            if SDL_WaitEvent(event) <= 0:
                raise UIError
            if event.type == command_event:
                self.drain_queue()
            elif event.type == SDL_QUIT:
                break
            elif event.type == SDL_DISPLAYEVENT:
                if event.display.event == SDL_DISPLAYEVENT_CONNECTED:
                    from ._event import DisplayEvent
                    dispatch_event('display_connected', DisplayEvent(display=event.display.display, type=event.type, timestamp=event.timestamp))
                elif event.display.event == SDL_DISPLAYEVENT_DISCONNECTED:
                    from ._event import DisplayOrientationEvent
                    dispatch_event('display_disconnected', DisplayOrientationEvent(data1=event.display.data1, display=event.display.display, type=event.type, timestamp=event.timestamp))
            elif event.type == SDL_WINDOWEVENT:
                from ._window import Window
                try:
                    window = Window(event.window.windowID)
                except Window.NotFound:
                    continue
                if event.window.event in [SDL_WINDOWEVENT_RESIZED, SDL_WINDOWEVENT_SIZE_CHANGED]:
                    from ._event import WindowSizeEvent
                    dispatch_event(map_sdl_window_events[event.window.event], WindowSizeEvent(width=event.window.data1, height=event.window.data2, window=window, type=event.type, timestamp=event.timestamp))
                elif event.window.event == SDL_WINDOWEVENT_MOVED:
                    from ._event import WindowPositionEvent
                    dispatch_event(map_sdl_window_events[event.window.event], WindowPositionEvent(x=event.window.data1, y=event.window.data2, window=window, type=event.type, timestamp=event.timestamp))
                elif event.window.event == SDL_WINDOWEVENT_DISPLAY_CHANGED:
                    dispatch_event(map_sdl_window_events[event.window.event], window, event.window.data1)
                else:
                    dispatch_event(map_sdl_window_events[event.window.event], window)
            if event.type in [SDL_DROPFILE, SDL_DROPTEXT]:
                SDL_free(next(x for x in event.drop._fields_ if x[0] == 'file')[1].from_buffer(event.drop, event.drop.__class__.file.offset))
        with window_map_lock:
            for window in window_map.values():
                window.destroy()
        SDL_Quit()

    def get_task(self):
        try:
            return self.__task_queue.get_nowait()
        except Empty:
            return None

    def drain_queue(self):
        try:
            self.__in_queue.set()
            while True:
                task = self.get_task()
                if task is None:
                    break
                task.dispatch()
        finally:
            self.__in_queue.clear()

    def execute(self, function: Callable, /, *args, **kwargs):
        if threading.current_thread() is event_thread:
            return function(*args, **kwargs)
        if not event_thread.is_alive():
            event_thread.start()
        task = EventTask(function, *args, **kwargs)
        self.__task_queue.put(task)
        if self.__stage == 2 and not self.__in_queue.is_set():
            assert self.__command_event is not None
            event = SDL_Event()
            event.type = self.__command_event
            SDL_PushEvent(event)
        task.wait()
        if task.has_exception():
            raise task.exception()[1]
        return task.result()

    def terminate_stage1(self):
        if self.__stage == 1:
            self.__stage = 0
        elif self.__state == 2:
            if len(event_listeners) + len(window_map) <= 0:
                self.__stage = 0


event_thread = EventThread(name='dragiyski.ui.event', daemon=False)
ui_threads.add(event_thread)


def wait_for_atexit():
    """Stage 1 of the `dragiyski.ui.alive` thread is idle thread intended to signal to the `dragiyski.ui.event` when
    there is no other non-daemon (strongly-referencing) threads except the UI threads.

    Since this process terminates when no non-UI non-daemon threads are alive, it should not prevent the process to exit normally.
    """
    try:
        main_thread = threading.main_thread()
        if isinstance(main_thread, threading.Thread) and main_thread.is_alive():
            main_thread.join()
        while True:
            strong_threads = [x for x in threading.enumerate() if x.is_alive() and x.daemon is False and x not in ui_threads]
            if len(strong_threads) > 0:
                strong_threads[0].join()
            else:
                break
    finally:
        run_in_event_thread(event_thread.terminate_stage1)
    # TODO: Do the stage-2 here. If there is windows, keep this thread.
    # TODO: Because there is no way to forcefully kill threads, the UIEvent thread might transition to stage2 while
    # TODO: this thread wait for the main thread to exit. In such case, starting another waiting thread is not necessary.


alive_thread_stage1 = threading.Thread(target=wait_for_atexit, name='dragiyski.ui.alive')
ui_threads.add(alive_thread_stage1)

run_in_event_thread = event_thread.execute


def in_event_thread(function):
    def caller(*args, **kwargs):
        return run_in_event_thread(function, *args, **kwargs)
    if hasattr(function, '__qualname__') and isinstance(function.__qualname__, str):
        caller.__qualname__ = function.__qualname__
    return caller

class EventListenerType(type):
    def __call__(cls, event_type: str, function: Callable):
        if event_type in event_listener_by_type:
            type_map = event_listener_by_type[event_type]
            if function in type_map:
                return type_map[function]
        return super(EventListenerType, cls).__call__(event_type, function)

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
                if event_type not in event_listener_by_type:
                    event_listener_by_type[event_type] = dict()
                type_map = event_listener_by_type[event_type]
                if function not in type_map:
                    Class = EventListenerOnce if once is True else EventListener
                    listener = Class(event_type, function)
                    type_map[function] = listener
                    event_listeners.add(listener)
            return function
        if len(kwargs) == 0 and len(args) == 1 and callable(args[0]):
            return event_decorator(args[0])
        return event_decorator

def event_dispatch(name, /, *args, **kwargs):
    pass
