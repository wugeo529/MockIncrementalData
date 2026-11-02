import importlib.util
import pathlib
import unittest
from unittest.mock import Mock, patch


class DesktopProfileTest(unittest.TestCase):
    def setUp(self):
        path = pathlib.Path(__file__).with_name('desktop_service.py')
        self.assertTrue(path.exists(), 'Desktop connection management is required')
        spec = importlib.util.spec_from_file_location('desktop_service', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.calls = []
        def probe(config):
            self.calls.append(dict(config))
            if config['password'] == 'bad':
                raise RuntimeError('Connection failed')
            return {'databaseExists': True, 'schemaReady': False}
        self.manager = self.module.DesktopManager(probe=probe)
        self.config = dict(engine='mysql', host='127.0.0.1', port=3306,
                           database='signal_sim_demo', user='root', password='test-secret')

    def test_connection_save_exposes_metadata_only(self):
        result = self.manager.configure(self.config)
        self.assertTrue(result['databaseExists'])
        public = self.manager.public_profiles()['mysql']
        self.assertTrue(public['hasPassword'])
        self.assertNotIn('password', public)
        self.assertNotIn('test-secret', str(result))
        self.assertEqual(self.manager.profile('mysql')['password'], 'test-secret')

    def test_failed_test_and_save_leave_active_connection_unchanged(self):
        self.manager.configure(self.config)
        before = dict(self.manager.profile('mysql'))
        with self.assertRaises(RuntimeError):
            self.manager.configure(dict(self.config, password='bad'))
        self.assertEqual(self.manager.profile('mysql'), before)
        self.manager.configure(dict(self.config, database='signal_sim_other'), test_only=True)
        self.assertEqual(self.manager.profile('mysql'), before)

    def test_running_profile_cannot_be_replaced(self):
        self.manager.states['mysql']['running'] = True
        with self.assertRaises(RuntimeError):
            self.manager.configure(self.config)
        self.assertEqual(self.calls, [])

    def test_only_whitelisted_dedicated_database_connections_allowed(self):
        for patch in [dict(engine='sqlite'), dict(database='production'), dict(port=True),
                      dict(port=0), dict(user=''), dict(configPath='secrets.json')]:
            with self.assertRaises(ValueError, msg=str(patch)):
                self.manager.configure(dict(self.config, **patch))
        self.assertEqual(self.calls, [])

    def test_blank_password_is_reused_only_for_same_endpoint(self):
        self.manager.configure(self.config)
        self.manager.configure(dict(self.config, password='', reusePassword=True))
        self.assertEqual(self.calls[-1]['password'], 'test-secret')
        self.manager.configure(dict(self.config, password='', host='localhost', reusePassword=True))
        self.assertEqual(self.calls[-1]['password'], '')

    def test_pg_existing_target_does_not_require_maintenance_database_access(self):
        connection = Mock()
        config = dict(self.config, engine='postgresql')
        with patch.object(self.module.signal_source, 'connect', return_value=connection), \
             patch.object(self.module.signal_source, 'verify_schema'), \
             patch.object(self.module, 'server_connection', side_effect=AssertionError('maintenance access forbidden')):
            self.assertEqual(self.module.probe_connection(config), dict(databaseExists=True, schemaReady=True))
        connection.close.assert_called_once()

    def test_pg_prepare_existing_database_does_not_require_create_database(self):
        connection = Mock()
        with patch.object(self.module.signal_source, 'connect', return_value=connection), \
             patch.object(self.module, 'server_connection', side_effect=AssertionError('maintenance forbidden')):
            self.module.prepare_database(dict(self.config, engine='postgresql'))
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
