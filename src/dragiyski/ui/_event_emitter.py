from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

_executor = ThreadPoolExecutor(thread_name_prefix='dragiyski.ui.event:')


class EventEmitter:
    def __init__(self, parent: Optional[EventEmitter] = None):
        self.__listeners = {}
        self.__parent = parent

    def add_event_listener(self, name: str, callback: Callable):
        if name not in self.__listeners:
            self.__listeners[name] = []
        if callback not in self.__listeners[name]:
            self.__listeners[name].append(callback)
            return True
        return False

    def remove_event_listener(self, name: str, callback: Callable):
        if name in self.__listeners:
            try:
                self.__listeners[name].remove(callback)
            except ValueError:
                return False
            if len(self.__listeners[name]) <= 0:
                del self.__listeners[name]
            return True
        return False

    def _execute(self, listener: Callable, name: str, args, kwargs):
        exc_info = [None, None, None]
        result = None
        is_success = True
        try:
            result, listener(*args, **kwargs)
        except:
            exc_info = sys.exc_info()
            is_success = False
        return (is_success, name, listener, result, *exc_info, args, kwargs)

    def _exception_check(self, name: str, futures, args, kwargs):
        for future in as_completed(futures):
            try:
                call_info = future.result()
            except:
                continue
            if not call_info[0]:
                # Emit called every time, because call_info[2] (the listener responsible for the exception) is different every time.
                # There is no significant performance penalty multiple calls, since this is just a submit to the event executor.
                self.emit_event('exception', call_info[1], call_info[2], call_info[4], call_info[5], call_info[6], *call_info[7], **call_info[8])

    def emit_event(self, name: str, /, *args, **kwargs):
        if name not in self.__listeners:
            return
        futures = [_executor.submit(self._execute, listener, name, args, kwargs) for listener in self.__listeners]
        if name != 'exception':
            _executor.submit(self._exception_check, name, futures, args, kwargs)
