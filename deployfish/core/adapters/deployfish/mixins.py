class SSHConfigMixin(object):

    def convert(self):
        data = {}
        kwargs = {}
        if 'ssh' in self.data:
            if 'proxy' in self.data['ssh']:
                kwargs['ssh_proxy_type'] = self.data['ssh']['proxy']
        return data, kwargs
