import unittest
from deployfish.aws.systems_manager import Parameter
from testfixtures import compare


class TestParameter__parse(unittest.TestCase):

    # def setUp(self):
    #     warnings.simplefilter("ignore", ResourceWarning)

    def test_no_value_raises_ValueError(self):
        self.assertRaises(ValueError, Parameter, 'foobar-service', 'foobar-cluster', yml='KEY')

    def test_external(self):
        p = Parameter('foobar-service', 'foobar-cluster', yml='KEY:external')
        self.assertEqual(p.key, 'KEY')
        self.assertEqual(p.value, None)
        self.assertEqual(p.is_external, True)
        self.assertEqual(p.is_secure, False)
        self.assertEqual(p.kms_key_id, None)

    def test_external_secure(self):
        p = Parameter('foobar-service', 'foobar-cluster', yml='KEY:external:secure')
        self.assertEqual(p.key, 'KEY')
        self.assertEqual(p.value, None)
        self.assertEqual(p.is_external, True)
        self.assertEqual(p.is_secure, True)
        self.assertEqual(p.kms_key_id, None)

    def test_external_secure_plus_kms_key(self):
        p = Parameter(
            'foobar-service',
            'foobar-cluster',
            yml='KEY:external:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab'
        )
        self.assertEqual(p.key, 'KEY')
        self.assertEqual(p.value, None)
        self.assertEqual(p.is_external, True)
        self.assertEqual(p.is_secure, True)
        self.assertEqual(p.kms_key_id, "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab")

    def test_bare_key_with_value(self):
        p = Parameter('foobar-service', 'foobar-cluster', yml='KEY=lkjasdlfkj:a490jlaisfdj\ew')
        self.assertEqual(p.key, 'KEY')
        self.assertEqual(p.value, "lkjasdlfkj:a490jlaisfdj\ew")
        self.assertEqual(p.is_external, False)
        self.assertEqual(p.is_secure, False)
        self.assertEqual(p.kms_key_id, None)

    def test_bare_key_dots_with_value(self):
        p = Parameter(
            'foobar-service', 'foobar-cluster', yml='cluster-name.service-name.KEY=lkjasdlfkj:a490jlaisfdj\ew'
        )
        self.assertEqual(p.key, 'cluster-name.service-name.KEY')
        self.assertEqual(p.value, "lkjasdlfkj:a490jlaisfdj\ew")
        self.assertEqual(p.is_external, False)
        self.assertEqual(p.is_secure, False)
        self.assertEqual(p.kms_key_id, None)

    def test_secure_with_value(self):
        p = Parameter('foobar-service', 'foobar-cluster', yml='KEY:secure=lkjasdlfkj:a490jlaisfdj\ew')
        self.assertEqual(p.key, 'KEY')
        self.assertEqual(p.value, "lkjasdlfkj:a490jlaisfdj\ew")
        self.assertEqual(p.is_external, False)
        self.assertEqual(p.is_secure, True)
        self.assertEqual(p.kms_key_id, None)

    def test_secure_with_value_plus_kms_key(self):
        p = Parameter(
            'foobar-service',
            'foobar-cluster',
            yml='KEY:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=lkjasdlfkj:a490jlaisfdj\ew'
        )
        self.assertEqual(p.key, 'KEY')
        self.assertEqual(p.value, "lkjasdlfkj:a490jlaisfdj\ew")
        self.assertEqual(p.is_external, False)
        self.assertEqual(p.is_secure, True)
        self.assertEqual(p.kms_key_id, "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab")


class TestParameter__render_write(unittest.TestCase):

    def test_bare_key_with_value(self):
        p = Parameter('foobar-service', 'foobar-cluster', yml='KEY=lkjasdlfkj:a490jlaisfdj\ew',)
        compare(
            p._render_write(),
            {
                'Name': 'foobar-cluster.foobar-service.KEY',
                'Value': 'lkjasdlfkj:a490jlaisfdj\ew',
                'Overwrite': True,
                'Type': 'String'
            }
        )

    def test_secure_with_value(self):
        p = Parameter('foobar-service', 'foobar-cluster', yml='KEY:secure=lkjasdlfkj:a490jlaisfdj\ew')
        compare(
            p._render_write(),
            {
                'Name': 'foobar-cluster.foobar-service.KEY',
                'Value': 'lkjasdlfkj:a490jlaisfdj\ew',
                'Overwrite': True,
                'Type': 'SecureString'
            }
        )

    def test_secure_with_value_plus_kms_key(self):
        p = Parameter(
            'foobar-service',
            'foobar-cluster',
            yml='KEY:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=lkjasdlfkj:a490jlaisfdj\ew'
        )
        compare(
            p._render_write(),
            {
                'Name': 'foobar-cluster.foobar-service.KEY',
                'Value': 'lkjasdlfkj:a490jlaisfdj\ew',
                'Overwrite': True,
                'Type': 'SecureString',
                'KeyId': 'arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab'
            }
        )
