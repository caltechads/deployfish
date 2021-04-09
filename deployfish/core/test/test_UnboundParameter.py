import unittest
from mock import Mock, call
from testfixtures import compare, Replacer

from deployfish.aws.systems_manager import UnboundParameter


class TestUnboundParameter__render(unittest.TestCase):

    def test__render_read(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            compare(p._render_read(), {'Names': ['foo.bar.BAZ'], 'WithDecryption': True})

    def test__render_write_no_encryption(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            p.value = 'my_value'
            compare(
                p._render_write(),
                {
                    'Name': 'foo.bar.BAZ',
                    'Value': 'my_value',
                    'Overwrite': True,
                    'Type': 'String'
                }
            )

    def test__render_write_with_encryption(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ', kms_key_id="my_key")
            p.value = 'my_value'
            compare(
                p._render_write(),
                {
                    'Name': 'foo.bar.BAZ',
                    'Value': 'my_value',
                    'Overwrite': True,
                    'Type': 'SecureString',
                    'KeyId': 'my_key'
                }
            )


class TestUnboundParameter__is_secure(unittest.TestCase):

    def get_mock_boto3_session(self, type):
        get_parameters = Mock(return_value={'Parameters': [{'Type': type}]})
        ssm_mock = Mock()
        ssm_mock.get_parameters = get_parameters
        client_mock = Mock(return_value=ssm_mock)
        session_mock = Mock()
        session_mock.client = client_mock
        fake_boto3_session = Mock(return_value=session_mock)
        return fake_boto3_session

    def setUp(self):
        get_parameters = Mock(return_value={'Parameters': [{'Value': 'my_aws_value'}]})
        ssm_mock = Mock()
        ssm_mock.get_parameters = get_parameters
        client_mock = Mock(return_value=ssm_mock)
        session_mock = Mock()
        session_mock.client = client_mock
        self.fake_boto3_session = Mock(return_value=session_mock)

    def test__is_secure_no_key_no_aws_object_returns_False(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            self.assertFalse(p.is_secure)

    def test__is_secure_key_but_no_aws_object_returns_True(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ', kms_key_id='my_key')
            self.assertTrue(p.is_secure)

    def test__is_secure_no_key_with_un_secure_aws_object_returns_False(self):
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                self.get_mock_boto3_session('String')
            )
            p = UnboundParameter('foo.bar.BAZ')
            self.assertFalse(p.is_secure)

    def test__is_secure_no_key_with_secure_aws_object_returns_True(self):
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                self.get_mock_boto3_session('SecureString')
            )
            p = UnboundParameter('foo.bar.BAZ')
            self.assertTrue(p.is_secure)

    def test__is_secure_with_key_with_secure_aws_object_returns_True(self):
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                self.get_mock_boto3_session('SecureString')
            )
            p = UnboundParameter('foo.bar.BAZ', kms_key_id='my_key')
            self.assertTrue(p.is_secure)


class TestUnboundParameter__prefix(unittest.TestCase):

    def test_get_prefix_returns_correct_prefix(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            self.assertEqual(p.prefix, 'foo.bar.')

    def test_get_prefix_returns_empty_string_if_no_prefix(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('BAZ')
            self.assertEqual(p.prefix, '')

    def test_set_prefix_updates_prefix(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('BAZ')
            self.assertEqual(p.name, 'BAZ')
            self.assertEqual(p.prefix, '')
            p.prefix = 'foo.bar.'
            self.assertEqual(p.name, 'foo.bar.BAZ')
            self.assertEqual(p.prefix, 'foo.bar.')

    def test_set_prefix_accepts_empty_prefixes(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            p.prefix = ''
            self.assertEqual(p.prefix, '')
            self.assertEqual(p.name, 'BAZ')

    def test_set_prefix_converts_None_to_empty_string(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            p.prefix = None
            self.assertEqual(p.prefix, '')
            self.assertEqual(p.name, 'BAZ')

    def test_set_prefix_reloads_aws_object(self):
        from_aws = Mock()
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', from_aws)
            p = UnboundParameter('BAZ')
            p.prefix = 'foo.bar.'
            compare(from_aws.mock_calls, [call(), call()])


class TestUnboundParameter__name(unittest.TestCase):

    def test_get_name_returns_correct_name(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            self.assertEqual(p.name, 'foo.bar.BAZ')

    def test_set_name_refuses_empty_names(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('BAZ')
            with self.assertRaises(ValueError):
                p.name = ''
            with self.assertRaises(ValueError):
                p.name = None

    def test_set_name_sets_name(self):
        from_aws = Mock()
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', from_aws)
            p = UnboundParameter('BAZ')
            p.name = 'foo.bar.BARNEY'
            self.assertEqual(p.name, 'foo.bar.BARNEY')

    def test_set_name_sets_key(self):
        from_aws = Mock()
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', from_aws)
            p = UnboundParameter('BAZ')
            p.name = 'foo.bar.BARNEY'
            self.assertEqual(p.key, 'BARNEY')

    def test_set_name_sets_prefix(self):
        from_aws = Mock()
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', from_aws)
            p = UnboundParameter('BAZ')
            p.name = 'foo.bar.BARNEY'
            self.assertEqual(p.prefix, 'foo.bar.')

    def test_set_name_reloads_aws_object(self):
        from_aws = Mock()
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', from_aws)
            p = UnboundParameter('BAZ')
            p.name = 'foo.bar.BARNEY'
            compare(from_aws.mock_calls, [call(), call()])


class TestUnboundParameter__key(unittest.TestCase):

    def test_get_key_returns_correct_key(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            self.assertEqual(p.key, 'BAZ')

    def test_get_key_returns_correct_key_even_if_no_prefix(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('BAZ')
            self.assertEqual(p.key, 'BAZ')

    def test_set_key_refuses_empty_keys(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('BAZ')
            with self.assertRaises(ValueError):
                p.key = ''
            with self.assertRaises(ValueError):
                p.key = None

    def test_set_key_sets_key(self):
        from_aws = Mock()
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', from_aws)
            p = UnboundParameter('BAZ')
            p.key = 'BARNEY'
            self.assertEqual(p.key, 'BARNEY')

    def test_set_key_sets_key_without_changing_prefix(self):
        from_aws = Mock()
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', from_aws)
            p = UnboundParameter('foo.bar.BAZ')
            p.key = 'BARNEY'
            self.assertEqual(p.key, 'BARNEY')
            self.assertEqual(p.prefix, 'foo.bar.')

    def test_set_key_reloads_aws_object(self):
        from_aws = Mock()
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', from_aws)
            p = UnboundParameter('BAZ')
            p.key = 'BARNEY'
            compare(from_aws.mock_calls, [call(), call()])


class TestUnboundParameter__value(unittest.TestCase):

    def setUp(self):
        get_parameters = Mock(return_value={'Parameters': [{'Value': 'my_aws_value'}]})
        ssm_mock = Mock()
        ssm_mock.get_parameters = get_parameters
        client_mock = Mock(return_value=ssm_mock)
        session_mock = Mock()
        session_mock.client = client_mock
        self.fake_boto3_session = Mock(return_value=session_mock)

    def test_get_value_returns_None_if_no_aws_object_and_no_user_set_value(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            self.assertEqual(p.value, None)

    def test_get_value_returns_aws_value_if_aws_object_and_no_user_set_value(self):
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session', self.fake_boto3_session
            )
            p = UnboundParameter('foo.bar.BAZ')
            self.assertEqual(p.value, 'my_aws_value')

    def test_set_value_sets_value(self):
        with Replacer() as r:
            r.replace('deployfish.aws.systems_manager.UnboundParameter._from_aws', Mock())
            p = UnboundParameter('foo.bar.BAZ')
            self.assertEqual(p.value, None)
            p.value = 'foo'
            self.assertEqual(p.value, 'foo')


class TestUnboundParameter__exists(unittest.TestCase):

    def get_mock_boto3_session(self, response=None):
        if response is None:
            response = {'Parameters': []}
        get_parameters = Mock(return_value=response)
        ssm_mock = Mock()
        ssm_mock.get_parameters = get_parameters
        client_mock = Mock(return_value=ssm_mock)
        session_mock = Mock()
        session_mock.client = client_mock
        fake_boto3_session = Mock(return_value=session_mock)
        return fake_boto3_session

    def test_get_exists_returns_False_if_no_aws_object(self):
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                self.get_mock_boto3_session()
            )
            p = UnboundParameter('foo.bar.BAZ')
            self.assertFalse(p.exists)

    def test_get_exists_returns_True_if_aws_object(self):
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                self.get_mock_boto3_session(response={'Parameters': [{'Type': 'String'}]})
            )
            p = UnboundParameter('foo.bar.BAZ')
            self.assertTrue(p.exists)


class TestUnboundParameter__save(unittest.TestCase):

    def get_mock_boto3_session(self, response=None):
        if response is None:
            response = {'Parameters': []}
        get_parameters = Mock(return_value=response)
        put_parameter = Mock()
        ssm_mock = Mock()
        ssm_mock.get_parameters = get_parameters
        ssm_mock.put_parameter = put_parameter
        client_mock = Mock(return_value=ssm_mock)
        session_mock = Mock()
        session_mock.client = client_mock
        fake_boto3_session = Mock(return_value=session_mock)
        return (fake_boto3_session, put_parameter)

    def test_save_saves_if_no_aws_object(self):
        fake_boto3_session, put_parameter = self.get_mock_boto3_session()
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                fake_boto3_session
            )
            p = UnboundParameter('foo.bar.BAZ', kms_key_id='my_key')
            p.value = 'foobar'
            p.save()
            put_parameter.assert_called_once()
            compare(
                put_parameter.call_args,
                call(Name='foo.bar.BAZ', Value='foobar', Overwrite=True, Type='SecureString', KeyId='my_key')
            )

    def test_save_throws_ValueError_if_aws_object_and_not_overwrite(self):
        fake_boto3_session, put_parameter = self.get_mock_boto3_session(response={'Parameters': [{'Type': 'String'}]})
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                fake_boto3_session
            )
            p = UnboundParameter('foo.bar.BAZ', kms_key_id='my_key')
            p.value = 'foobar'
            with self.assertRaises(ValueError):
                p.save()
            put_parameter.assert_not_called()

    def test_save_saves_if_aws_object_and_overwrite(self):
        fake_boto3_session, put_parameter = self.get_mock_boto3_session(response={'Parameters': [{'Type': 'String'}]})
        with Replacer() as r:
            r.replace(
                'deployfish.aws.systems_manager.get_boto3_session',
                fake_boto3_session
            )
            p = UnboundParameter('foo.bar.BAZ', kms_key_id='my_key')
            p.value = 'foobar'
            p.save(overwrite=True)
            put_parameter.assert_called_once()
            compare(
                put_parameter.call_args,
                call(Name='foo.bar.BAZ', Value='foobar', Overwrite=True, Type='SecureString', KeyId='my_key')
            )
