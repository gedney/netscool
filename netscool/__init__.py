DEFAULT = 'default'

_IMPL = DEFAULT
_SELECTED = {}

def lesson(lesson_tag):
    global _IMPL
    _IMPL = lesson_tag

def implementation(tag):
    def selected_implementation(cls):
        global _SELECTED

        cls_key = "{}.{}".format(cls.__module__, cls.__name__)
        if cls_key not in _SELECTED:
            if cls._impl != _IMPL and cls._impl != DEFAULT:
                return None

            _SELECTED[cls_key] = cls
            return cls

        selected = _SELECTED[cls_key]
        if cls._impl == selected._impl:
            raise Exception(
                "Duplicate class {} for tag {}".format(cls_key, cls._impl))

        if selected._impl == DEFAULT and cls._impl == _IMPL:
            _SELECTED[cls_key] = cls
            return cls
        return selected

    def inner(cls):
        cls._impl = tag
        return selected_implementation(cls)

    return inner
