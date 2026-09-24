"""MessageHandler: dispatch inbound WrapperMessage bodies by kind."""


class MessageHandler(object):
    _handlers = {}

    def __init__(self, kind):
        self._kind = kind

    def __call__(self, func):
        MessageHandler._handlers[self._kind] = func
        return func

    @classmethod
    def dispatch(cls, wrapper):
        if wrapper is None or wrapper.kind is None:
            return None
        handler = cls._handlers.get(wrapper.kind)
        if handler is None:
            return None
        return handler(wrapper)

    @classmethod
    def clear(cls):
        cls._handlers.clear()
