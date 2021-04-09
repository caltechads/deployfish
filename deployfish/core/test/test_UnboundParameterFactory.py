import unittest
from mock import MagicMock, Mock, call
from testfixtures import compare, Replacer

from deployfish.aws.systems_manager import UnboundParameterFactory


class TestUnboundParameterFactory__new(unittest.TestCase):

    def get_mock_boto3_session(self, data=None):
        if data:
            if isinstance(data, list):
                if isinstance(data[0], list):
                    data = [{'Parameters': datum} for datum in data]
                else:
                    data = [{'Parameters': data}]
            else:
                data = [{'Parameters': [data]}]
        else:
            data = [{'Parameters': []}]
        # The iterator that boto3.get_client('ssm').get_paginator().paginate() returns
        iterator = MagicMock()
        iterator.__iter__.return_value = data
        # boto3.get_client('ssm').get_paginator().paginate()
        paginate = Mock(return_value=iterator)
        paginator = Mock()
        paginator.paginate = paginate
        # boto3.get_client('ssm').get_paginator()
        get_paginator = Mock(return_value=paginator)
        ssm_mock = Mock()
        ssm_mock.get_paginator = get_paginator
        # boto3.get_client('ssm')
        client_mock = Mock(return_value=ssm_mock)
        session_mock = Mock()
        session_mock.client = client_mock
        # the boto3 session
        fake_boto3_session = Mock(return_value=session_mock)
        return fake_boto3_session, paginate

    def test__single_parameter_search_uses_Equals_filter(self):
        fake_boto3_session, paginate = self.get_mock_boto3_session()
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                fake_boto3_session
            )
            UnboundParameterFactory.new('foo.bar.BAZ')
            paginate.assert_called_once()
            compare(
                paginate.call_args,
                call(
                    PaginationConfig={'MaxItems': 100, 'PageSize': 50},
                    ParameterFilters=[{'Key': 'Name', 'Option': 'Equals', 'Values': ['foo.bar.BAZ']}]
                )
            )

    def test__single_parameter_search_returns_empty_list_if_no_match(self):
        fake_boto3_session, paginate = self.get_mock_boto3_session()
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                fake_boto3_session
            )
            parameters = UnboundParameterFactory.new('foo.bar.BAZ')
            compare(parameters, [])

    def test__single_parameter_search_returns_parameter_if_match(self):
        fake_boto3_session, paginate = self.get_mock_boto3_session(
            data={'Type': 'String', 'Name': 'foo.bar.BAZ'}
        )
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.get_boto3_session', fake_boto3_session)
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            parameters = UnboundParameterFactory.new('foo.bar.BAZ')
            self.assertEqual(len(parameters), 1)
            self.assertEqual(parameters[0].name, 'foo.bar.BAZ')

    def test__single_parameter_search_does_not_set_kms_key_id_on_parameter_if_no_key(self):
        fake_boto3_session, paginate = self.get_mock_boto3_session(
            data={'Type': 'String', 'Name': 'foo.bar.BAZ'}
        )
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.get_boto3_session', fake_boto3_session)
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            parameters = UnboundParameterFactory.new('foo.bar.BAZ')
            self.assertEqual(len(parameters), 1)
            self.assertEqual(parameters[0].kms_key_id, None)

    def test__single_parameter_search_sets_kms_key_id_on_parameter_if_key(self):
        fake_boto3_session, paginate = self.get_mock_boto3_session(
            data={'Type': 'SecureString', 'Name': 'foo.bar.BAZ', 'KeyId': 'my_key_id'}
        )
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.get_boto3_session', fake_boto3_session)
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            parameters = UnboundParameterFactory.new('foo.bar.BAZ')
            self.assertEqual(len(parameters), 1)
            self.assertEqual(parameters[0].kms_key_id, 'my_key_id')

    def test__wildcard_parameter_search_uses_BeginsWith_filter_and_strips_star(self):
        fake_boto3_session, paginate = self.get_mock_boto3_session()
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                fake_boto3_session
            )
            UnboundParameterFactory.new('foo.bar.*')
            paginate.assert_called_once()
            compare(
                paginate.call_args,
                call(
                    PaginationConfig={'MaxItems': 100, 'PageSize': 50},
                    ParameterFilters=[{'Key': 'Name', 'Option': 'BeginsWith', 'Values': ['foo.bar.']}]
                )
            )

    def test__wildcard_parameter_search_returns_parameters_if_match(self):
        fake_boto3_session, paginate = self.get_mock_boto3_session(
            data=[
                {'Type': 'String', 'Name': 'foo.bar.BAZ'},
                {'Type': 'String', 'Name': 'foo.bar.FLA'},
                {'Type': 'String', 'Name': 'foo.bar.BLU'},
            ]
        )
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.get_boto3_session', fake_boto3_session)
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            parameters = UnboundParameterFactory.new('foo.bar.*')
            self.assertEqual(len(parameters), 3)
            self.assertEqual(parameters[0].name, 'foo.bar.BAZ')
            self.assertEqual(parameters[1].name, 'foo.bar.FLA')
            self.assertEqual(parameters[2].name, 'foo.bar.BLU')

    def test__wildcard_parameter_search_deals_with_multiple_lists_from_iterator(self):
        fake_boto3_session, paginate = self.get_mock_boto3_session(data=[
            [
                {'Type': 'String', 'Name': 'foo.bar.BAZ'},
                {'Type': 'String', 'Name': 'foo.bar.BLU'}
            ],
            [
                {'Type': 'String', 'Name': 'foo.bar.FLA'},
            ]
        ])
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.get_boto3_session', fake_boto3_session)
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            parameters = UnboundParameterFactory.new('foo.bar.*')
            self.assertEqual(len(parameters), 3)
            self.assertEqual(parameters[0].name, 'foo.bar.BAZ')
            self.assertEqual(parameters[1].name, 'foo.bar.BLU')
            self.assertEqual(parameters[2].name, 'foo.bar.FLA')
