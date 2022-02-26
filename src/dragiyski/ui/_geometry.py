from sdl2 import *
import typing
import math


class Rectangle:
    def __init__(
        self,
        x: typing.Optional[int] = None,
        y: typing.Optional[int] = None,
        width: typing.Optional[int] = None,
        height: typing.Optional[int] = None,
        *,
        top: typing.Optional[int] = None,
        right: typing.Optional[int] = None,
        bottom: typing.Optional[int] = None,
        left: typing.Optional[int] = None,
    ):
        if x is None:
            if left is not None:
                x = left
            elif right is not None and width is not None:
                x = right - width + 1
            else:
                raise TypeError('missing argument: either `x` or `left` or (`width` and `right`) are required)')
        if y is None:
            if top is not None:
                y = top
            elif bottom is not None and height is not None:
                y = bottom - height + 1
            else:
                raise TypeError('missing argument: either `y` or `top` or (`height` and `bottom`) are required)')
        if width is None:
            if right is not None:
                width = right - x + 1
            else:
                raise TypeError('missing argument: either `width` or ((`x` or `left`) and `right`) are required)')
        if height is None:
            if bottom is not None:
                height = bottom - y + 1
            else:
                raise TypeError('missing argument: either `height` or ((`y` or `top`) and `bottom`) are required)')
        if right is not None and (right - width + 1) != x:
            raise TypeError('conflicting argument: `right` is present, but does not match `(x + width - 1)`')
        if left is not None and left != x:
            raise TypeError('conflicting argument: `left` is present, but does not match `x` or `(right - width + 1)`')
        if bottom is not None and (bottom - height + 1) != x:
            raise TypeError('conflicting argument: `bottom` is present, but does not match `(y + height - 1)`')
        if top is not None and top != x:
            raise TypeError('conflicting argument: `top` is present, but does not match `y` or `(bottom - height + 1)`')
        if width <= 0:
            raise ValueError('argument `width` cannot be negative')
        if height <= 0:
            raise ValueError('argument `height` cannot be negative')
        self.__impl = SDL_Rect()
        self.__impl.x = x
        self.__impl.y = y
        self.__impl.w = width
        self.__impl.h = height

    @property
    def x(self):
        return self.__impl.x

    @x.setter
    def x(self, value: int):
        self.__impl.x = value

    @property
    def y(self):
        return self.__impl.y

    @y.setter
    def y(self, value: int):
        self.__impl.y = value

    @property
    def width(self):
        return self.__impl.w

    @width.setter
    def width(self, value: int):
        if value <= 0:
            raise ValueError('`width` cannot be negative')
        self.__impl.w = value

    @property
    def height(self):
        return self.__impl.h

    @height.setter
    def height(self, value: int):
        if value <= 0:
            raise ValueError('`height` cannot be negative')
        self.__impl.h = value

    @property
    def left(self):
        return self.__impl.x

    @left.setter
    def left(self, value: int):
        self.__impl.x = value

    @property
    def top(self):
        return self.__impl.y

    @top.setter
    def top(self, value: int):
        self.__impl.y = value

    @property
    def right(self):
        return self.__impl.x + self.__impl.w - 1

    @right.setter
    def right(self, value: int):
        self.__impl.x = value - self.__impl.w + 1

    @property
    def bottom(self):
        return self.__impl.y + self.__impl.h - 1

    @bottom.setter
    def bottom(self, value: int):
        self.__impl.y = value - self.__impl.h + 1

    def move_by(self, dx: int = 0, dy: int = 0):
        self.__impl.x += dx
        self.__impl.y += dy
        return self
    
    def move_to(self, x: int = 0, y: int = 0):
        self.__impl.x = x
        self.__impl.y = y
        return self

    def resize_around(self, x: int, y: int, width: int, height: int):
        if width <= 0:
            raise ValueError('`width` cannot be negative')
        if height <= 0:
            raise ValueError('`height` cannot be negative')
        to_left = self.__impl.x - x
        to_top = self.__impl.y - y
        new_left = x + math.floor(to_left / self.__impl.w * width)
        new_top = y + math.floor(to_top / self.__impl.h * height)
        self.__impl.x = new_left
        self.__impl.y = new_top
        self.__impl.w = width
        self.__impl.h = height
        return self
        
    def resize_to(self, width: int, height: int):
        if width <= 0:
            raise ValueError('`width` cannot be negative')
        if height <= 0:
            raise ValueError('`height` cannot be negative')
        self.__impl.w = width
        self.__impl.h = height
        
    def resize_by(self, delta_width: int, delta_height: int):
        return self.resize_to(self.__impl.w + delta_width, self.__impl.h + delta_height)
    
    def __repr__(self):
        return f'Rectangle(x={self.x}, y={self.y}, width={self.width}, height={self.height})'
    
def create_rectangle(rect: SDL_Rect):
    storage = Rectangle.__new__(Rectangle)
    storage._Rectangle__impl = rect
    return storage
