from sdl2 import *
import sdl2
from queue import Queue, Empty
from typing import Callable
from ._error import UIError
import sys
import threading
import re

event_listeners = set()
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
        if not SDL_WasInit(SDL_INIT_EVENTS):
            if SDL_InitSubSystem(SDL_INIT_EVENTS) < 0:
                raise UIError
        self.__command_event = command_event = SDL_RegisterEvents(1)
        if command_event == 0xFFFFFFFF:
            raise UIError
        while self.__stage == 2:
            sdl_event = SDL_Event()
            if SDL_WaitEvent(sdl_event) <= 0:
                raise UIError
            if sdl_event.type == command_event:
                self.drain_queue()
            elif sdl_event.type == SDL_QUIT:
                break
            else:
                from ._event import create_event
                event = create_event(sdl_event)
                if event is not None:
                    from ._event import dispatch_event
                    dispatch_event(event.type, event)
            # According to documentation, libSDL uses strdup, which allocate necessary memory to store a string. It is responsibility
            # of the caller for the SDL_*Event functions to release that memory.
            # Since create_event() must decode such strings, which generate a python copy of it, the original is safe to discard.
            if sdl_event.type in [SDL_DROPFILE, SDL_DROPTEXT]:
                SDL_free(next(x for x in sdl_event.drop._fields_ if x[0] == 'file')[1].from_buffer(sdl_event.drop, sdl_event.drop.__class__.file.offset))
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
                # Since all "strong" threads must exit before the ui_threads, it does not matter at which strong thread we are waiting;
                strong_threads[0].join()
            else:
                break
    finally:
        if event_thread.is_alive():
            run_in_event_thread(event_thread.terminate_stage1)
    # TODO: Do the stage-2 here. If there is windows, keep this thread.
    # TODO: Because there is no way to forcefully kill threads, the UIEvent thread might transition to stage2 while
    # TODO: this thread wait for the main thread to exit. In such case, starting another waiting thread is not necessary.


alive_thread_stage1 = threading.Thread(target=wait_for_atexit, name='dragiyski.ui.alive', daemon=False)
ui_threads.add(alive_thread_stage1)

run_in_event_thread = event_thread.execute


def in_event_thread(function):
    def caller(*args, **kwargs):
        return run_in_event_thread(function, *args, **kwargs)
    if hasattr(function, '__qualname__') and isinstance(function.__qualname__, str):
        caller.__qualname__ = function.__qualname__
    return caller

def add_event_listener(listener):
    event_listeners.add(listener)
    if event_thread.is_alive():
        run_in_event_thread(event_thread.terminate_stage1)
    else:
        event_thread.start()
