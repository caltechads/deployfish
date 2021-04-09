import inspect2
from pydoc import locate


class FunctionTypeCommentParser(object):

    class TypeCommentParseError(Exception):
        pass

    def _get_type_annotations(self, obj):
        line = inspect2.getsourcelines(obj)[0][1].strip()
        if line.startswith('# hint:'):
            args = line[7:].strip()
            if not (args.startswith('(') and args.endswith(')')):
                raise self.TypeParseError('{}.: {} is not a valid type definition'.format(str(obj), line))
            args = [arg.strip() for arg in args[1:-1].split(',')]
            return args
        else:
            return None

    def parse_type(self, type_str):
        is_list = False
        type_def = {'type': type_str}
        if type_str.startswith('Optional['):
            type_def['type'] = type_str[9:-1]
        if type_str.startswith("Union["):
            type_def['type'] = [t.strip() for t in type_str[6:-1].split(',')]
        if type_str.startswith("list["):
            is_list = True
            type_str = type_str[5:-1]
        if type_str.startswith("str["):
            # look for string specs
            type_def = {
                'type': str,
                'specs': [spec.strip('"') for spec in type_str[4:-1].split(',')]
            }
        if is_list:
            type_def['multiple'] = True
        actual_type = locate(type_def['type'])
        if actual_type is not None:
            type_def['type'] = actual_type
        return type_def

    def parse(self, func):
        """
        Return a dict describing the arguments for `func` a function or method object, with type annotations (if any)
        and default values.  Example::

            def foo(self, arg1, kwarg1='Hello', kwarg2=None):
                # hint: (str, str, Union[None, str])

        For that function, we will return:
        (
            {
                'arg1': {'type': 'str'}
            },
            {
                'kwarg1': {'type': str, 'default': 'Hello'},
                'kwarg2': {'type': ['None', str], 'default': None},
            },
        )

        :param func function: a function or method object

        :rtype: dict(str, dict(str, Any))
        """
        arg_annotations = self._get_type_annotations(func)
        argspec = inspect2.getfullargspec(func)
        args = argspec.args
        if argspec.args[0] in ['self', 'cls']:
            args = args[1:]
        if not arg_annotations:
            arg_annotations = ['UNSPECIFIED'] * len(args)
        if argspec.defaults:
            firstdefault = len(args) - len(argspec.defaults)
            defaults = ['REQUIRED'] * firstdefault + list(argspec.defaults)
        else:
            defaults = ['REQUIRED'] * len(args)
        response_args = {}
        response_kwargs = {}
        for i, arg in enumerate(args):
            arg_type = arg_annotations[i]
            arg_def = self.parse_type(arg_type)
            if defaults[i] != 'REQUIRED':
                response_kwargs[arg] = arg_def
                response_kwargs[arg]['default'] = defaults[i]
            else:
                response_args[arg] = arg_def
        return response_args, response_kwargs
