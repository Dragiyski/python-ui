from sdl2 import *
from typing import Callable
from ._error import UIError
import threading

application_storage = threading.local()
application_singleton = None

class ApplicationFactory(type):
    def __call__(cls, *args, **kwargs):
        global application_singleton
        if application_singleton is not None:
            raise ReferenceError('There is already an active application')
        application_singleton = super(ApplicationFactory, cls).__call__(*args, **kwargs)
        return application_singleton
    
def ensure_subsystem(system):
    def subsystem_decorator(dependent: Callable):
        def subsystem_initializer(*args, **kwargs):
            if SDL_WasInit(system) == 0:
                if SDL_InitSubSystem(system) < 0:
                    raise UIError
            return dependent(*args, **kwargs)
        return subsystem_initializer
    return subsystem_decorator

def ensure_application_thread(context: Callable):
    def decorator(*args, **kwargs):
        if application_singleton is None:
            raise RuntimeError('There is no active application')
        if not hasattr(application_storage, 'application') or application_storage.application is not application_singleton:
            raise RuntimeError(f'Cannot call {context} outside of the application thread')
        return context(*args, **kwargs)
    return decorator

class Application(metaclass=ApplicationFactory):
    def __init__(self):
        self.__window_by_id = {}
        self.__thread = threading.current_thread()
        if hasattr(application_storage, 'application'):
            raise RuntimeError('There is already an active application')
        application_storage.application = self
        from ._display import DisplayList
        self.__display = DisplayList(self)
        SDL_InitSubSystem(SDL_INIT_EVERYTHING)
        
    @property
    def display(self):
        return self.__display
        
    @ensure_subsystem(SDL_INIT_EVENTS)
    def run(self):
        if not SDL_WasInit(SDL_INIT_EVENTS):
            if SDL_InitSubSystem(SDL_INIT_EVENTS) == 0:
                raise UIError
        in_event_loop = True
        while in_event_loop:
            event = SDL_Event()
            if SDL_WaitEvent(event) < 0:
                raise UIError
            if event.type == SDL_QUIT:
                self._quit()
                break
            if event.type == SDL_QUIT:
                in_event_loop = False
            elif event.type == SDL_DISPLAYEVENT:
                if event.display.event == SDL_DISPLAYEVENT_CONNECTED:
                    self.on_display_connected(event.display.display)
                if event.display.event == SDL_DISPLAYEVENT_DISCONNECTED:
                    self.on_display_disconnected(event.display.display)
                if event.display.event == SDL_DISPLAYEVENT_ORIENTATION:
                    # Rotations in SDL are misleading and directly map android's getRotation()
                    # (which returns ROTATION_0, ROTATION_90, ...) into SDL misleading names.
                    # Generally, those will be correct on most phones and some tablets.
                    # However, android states ROTATION_0 to be "natural" rotation of the device, which can be landscape (width > height)
                    rotation = None
                    if event.display.data1 == SDL_ORIENTATION_PORTRAIT:
                        rotation = 0
                    elif event.display.data1 == SDL_ORIENTATION_LANDSCAPE:
                        rotation = 90
                    elif event.display.data1 == SDL_ORIENTATION_PORTRAIT_FLIPPED:
                        rotation = 180
                    elif event.display.data1 == SDL_ORIENTATION_LANDSCAPE_FLIPPED:
                        rotation = 270
                    if rotation is not None:
                        self.on_display_orientation_change(event.display.display, rotation)
            if event.type in [SDL_DROPFILE, SDL_DROPTEXT]:
                SDL_free(next(x for x in event.drop._fields_ if x[0] == 'file')[1].from_buffer(event.drop, event.drop.__class__.file.offset))
                
    def on_display_connected(display: int):
        """Event: a display has been attached.

        Args:
            display (int): The index of the display.
        """
        pass
    
    def on_display_disconnected(display: int):
        """Event: a display has been detached.

        Args:
            display (int): The index of the display. That index will no longer be valid.
        """
        pass
    
    def on_display_orientation_change(display: int, rotation: int):
        """Event: The orientation of the device has changed. It will be called only when the application is running on device with orientation change sensors.
        Currently, only applicable for android devices.
        
        Rotation is measured in degrees and can be 0, 90, 180 and 270. Rotation 0 degrees is the "natural" device orientation.
        Most phones "natural" orientation is portrait mode (width < height), while in some tablets the "natural" orientation is (width > height).
        Rotation 90 degrees means the device has rotated 90 degrees counter-clockwise, thus image on the screen rotated 90 degrees clockwise.
        Reading English text in the "natural" orientation of the device, means lines of text goes from left to right next line is to the bottom of the current line.
        Rotating device counter-clockwise by 90 degrees, with orientation change turned off, will make the lines go from bottom to top and the next line will be to the right of the current line.
        Orientation change compensate for this rotation by rotating the image clockwise, restoring the left-to-right order of lines and next line appering to the bottom of the current line.
        The result is an image in the same orientation to the user's eyes.

        Args:
            display (int): The index of the display.
            rotation (int): The new orientation in degrees. Can only be 0, 90, 180 and 270.
        """
        pass