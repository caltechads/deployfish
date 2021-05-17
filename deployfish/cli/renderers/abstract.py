class AbstractRenderer(object):

    def __init__(self, *args, **kwargs):
        pass

    def render(self, data, **kwargs):
        raise NotImplementedError
