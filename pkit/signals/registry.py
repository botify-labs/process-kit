import collections


class HandlerRegistry(object):
    def __init__(self, extract_from, insert_with):
        """
        :param extract_from: returns the key of the object to find when a
                             signal is triggered.
        :type  extract_from: callable(signum, sigframe)

        :param insert_with: returns the value of the key used to index the
                            object in the registry.
        :type  insert_with: callable(obj)

        """
        self._extract_from = extract_from
        self._insert_with = insert_with
        self._handlers = collections.defaultdict(list)

    def register(self, obj, handler):
        key = self._insert_with(obj)
        self._handlers[key].append(handler)

    def unregister(self, obj, handler):
        key = self._insert_with(obj)
        self._handlers[key].remove(handler)

    def __call__(self, signum, sigframe):
        key = self._extract_from(signum, sigframe)
        for handler in self._handlers[key]:
            handler()
