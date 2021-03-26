

class Adapter(object):

    def __init__(self, data, **kwargs):
        self.data = data

    def convert(self):
        raise NotImplementedError
