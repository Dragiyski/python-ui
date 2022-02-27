from sdl2 import *
import sys
import atexit
import asyncio
import functools
import re
from threading import Thread, Event, current_thread
from queue import Queue, Empty
from ._error import UIError
from typing import Optional, Callable
from traceback import print_exc

_window_event_names = {id: name for (name, id) in [(x[len('SDL_WINDOWEVENT_'):].lower(), getattr(video, x)) for x in dir(video) if x.startswith('SDL_WINDOWEVENT_')]}
_re_word_to_under = re.compile('(.)([A-Z][a-z]+)')
_re_upper_follow = re.compile('([a-z0-9])([A-Z])')
_re_replacement = r'\1_\2'

def convert_event_name(name: str):
    name = re.sub(_re_word_to_under, _re_replacement, name)
    name = re.sub(_re_upper_follow, _re_replacement, name)
    return name.lower()

def _event_thread_function():
    global _event_thread_ready, _event_thread_function, _event_thread_exception, _sdl_command_event
    _event_thread_exception = None
    try:
        if not SDL_WasInit(SDL_INIT_EVENTS):
            _sdl_command_event = None
            if SDL_InitSubSystem(SDL_INIT_EVENTS) < 0:
                raise UIError
        if _sdl_command_event is None:
            command_event = SDL_RegisterEvents(1)
            if command_event > SDL_LASTEVENT:
                raise UIError
            _sdl_command_event = command_event
        _event_thread_ready.set()
    except:
        _event_thread_exception = sys.exc_info()
        _event_thread_ready.set()
    try:
        event = SDL_Event()
        while True:
            if SDL_WaitEvent(event) < 0:
                raise UIError()
            if event.type == _sdl_command_event:
                _drain_queue()
                continue
            if event.type == SDL_QUIT:
                SDL_Quit()
                break
            if event.type == SDL_DISPLAYEVENT:
                from ._display import dispatch_event
                dispatch_event(event)
                continue
            # _comsume_event(event)
            if event.type in [SDL_DROPFILE, SDL_DROPTEXT]:
                SDL_free(next(x for x in event.drop._fields_ if x[0] == 'file')[1].from_buffer(event.drop, event.drop.__class__.file.offset))
    except:
        _event_thread_exception = sys.exc_info()
        print_exc()
    finally:
        _event_thread_ready.clear()


_event_thread = None
_event_thread_ready = Event()
_event_thread_exception = None
_event_thread_queue = Queue(maxsize=0)
_event_thread_queue_running = False
_sdl_command_event = None


def _get_task():
    try:
        return _event_thread_queue.get_nowait()
    except Empty:
        return None


def _drain_queue():
    global _event_thread_queue_running
    _event_thread_queue_running = True
    while True:
        task = _get_task()
        if task is None:
            break
        task.dispatch()
    _event_thread_queue_running = False


class EventDelegate:
    def __init__(self, function, args, kwargs):
        self.__function = function
        self.__args = args
        self.__kwargs = kwargs
        self.__event = Event()
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
        self.__event.set()


class EventFuture(asyncio.Future):
    def __init__(self, function, args, kwargs, *args2, **kwargs2):
        super(EventFuture, self).__init__(*args2, **kwargs2)
        self.__function = function
        self.__args = args
        self.__kwargs = kwargs

    def dispatch(self):
        if self.done():
            return
        try:
            result = self.__function(*self.__args, **self.__kwargs)
        except:
            exception = sys.exc_info()[1]
            # Due to a race condition, set_* can be called in between the line above and this line,
            # but in this case we must not throw.
            try:
                self.set_exception(exception)
            except:
                pass
            return
        try:
            self.set_result(result)
        except:
            pass


def _comsume_event(event):
    try:
        from ._window import Window
        if event.type == SDL_WINDOWEVENT:
            try:
                window = Window(event.window.windowID)
            except Window.NotFound:
                return
            window_event = _window_event_names[event.window.event]
            if event.window.event in [SDL_WINDOWEVENT_MOVED, SDL_WINDOWEVENT_RESIZED, SDL_WINDOWEVENT_SIZE_CHANGED]:
                window.emit_event(window_event, event.window.data1, event.window.data2)
            else:
                window.emit_event(window_event)
            if event.window.event == SDL_WINDOWEVENT_CLOSE:
                window._destroy()
    except:
        print_exc()


def _ensure_event_thread():
    global _event_thread, _event_thread_exception, _event_thread_ready
    if _event_thread is None or not _event_thread.is_alive():
        _event_thread_ready.clear()
        # We shall use daemon thread here to ensure any non-window UI operations (like getting the screen information)
        # does not hold the process alive. For window operation, there should be another really light-weight non-daemon
        # thread, that is blocked most of the time, except on creation and removal of windows.
        # Therefore, the process will remain alive only if there are non-closed windows.
        _event_thread = Thread(target=_event_thread_function, daemon=True, name='UI Event Thread')
        _event_thread.start()
    _event_thread_ready.wait()
    if _event_thread_exception is not None:
        raise _event_thread_exception[1]


def delegate_sync_call(function, /, *args, **kwargs):
    _ensure_event_thread()
    # Do not do complex dispatch, if we are already in the event thread.
    if current_thread() is _event_thread:
        return function(*args, **kwargs)
    delegate = EventDelegate(function, args, kwargs)
    _event_thread_queue.put(delegate)
    if not _event_thread_queue_running:
        event = SDL_Event()
        event.type = _sdl_command_event
        # SDL_PushEvent is thread-safe
        if SDL_PushEvent(event) < 0:
            raise UIError
    # Block the current thread until the task is ready.
    delegate.wait()
    if delegate.has_exception():
        raise delegate.exception()[1]
    return delegate.result()

def delegate_async_call(loop, function, /, *args, **kwargs):
    _ensure_event_thread()
    # Do not do complex dispatch, if we are already in the event thread.
    if current_thread() is _event_thread:
        return function(*args, **kwargs)
    if loop is None:
        loop = asyncio.get_running_loop()
    return loop.run_in_executor(None, functools.partial(delegate_sync_call, function, *args, **kwargs))

def get_delegate_from_args(kwargs):
    if kwargs.get('sync') is True:
        if kwargs.get('async') is True:
            raise ValueError('Function cannot be both "sync" and "async" at the same time')
        return delegate_sync_call
    loop = kwargs.get('loop')
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
    if kwargs.get('async') is True:
        if loop is None:
            loop = asyncio.get_event_loop()
        return functools.partial(delegate_async_call, loop)
    if loop is None:
        return delegate_sync_call
    else:
        return functools.partial(delegate_async_call, loop)


@atexit.register
def on_process_exit():
    # Once the process exits, if there is an existing daemon event thread, we send SDL_QUIT to the message queue and
    # wait for the thread to exit. The thread will call SDL_Quit, releasing any associated SDL resources.
    global _event_thread
    if _event_thread is not None and _event_thread.is_alive():
        event = SDL_Event()
        event.type = SDL_QUIT
        if SDL_PushEvent(event) < 0:
            return
        _event_thread.join()
