import inspect

from std_msgs import msg as std_msgs

_type_defs = {}


def def_type_named(name, type_def):
    _type_defs[name] = type_def


def def_type(type_def):
    def_type_named(type_def.__name__, type_def)


def def_types(module):
    for msg_type in inspect.getmembers(module, inspect.isclass):
        def_type_named(*msg_type)


def_types(std_msgs)


def resolve_type(name):
    try:
        return _type_defs[name]
    except KeyError:
        raise TypeError('Unknown message type: ' + name)
