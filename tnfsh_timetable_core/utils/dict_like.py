def dict_like(cls):

    def _get_root(self):
        return self.root

    setattr(cls, '__getitem__', lambda self, k: _get_root(self)[k])
    setattr(cls, '__setitem__', lambda self, k, v: _get_root(self).__setitem__(k, v))
    setattr(cls, '__delitem__', lambda self, k: _get_root(self).__delitem__(k))
    setattr(cls, '__contains__', lambda self, k: k in _get_root(self))
    setattr(cls, '__iter__', lambda self: iter(_get_root(self)))
    setattr(cls, '__len__', lambda self: len(_get_root(self)))
    setattr(cls, 'get', lambda self, k, default=None: _get_root(self).get(k, default))
    setattr(cls, 'keys', lambda self: _get_root(self).keys())
    setattr(cls, 'values', lambda self: _get_root(self).values())
    setattr(cls, 'items', lambda self: _get_root(self).items())
    setattr(cls, 'update', lambda self, *args, **kwargs: _get_root(self).update(*args, **kwargs))
    return cls