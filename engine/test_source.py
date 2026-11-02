import importlib.util
import pathlib
import unittest
import json
import sys
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parent

class SourceContractTest(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('signal_source', ROOT / 'signal_source.py')
        self.assertTrue((ROOT / 'signal_source.py').is_file(), 'source simulator implementation is required')
        self.source = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.source)

    def test_exact_postgres_field_order_and_types(self):
        expected = {
            'gps': 'imsi satellite_num position_num lon lat insert_time gps_time means direction alititude speed beam_num terminal_type_name satellite_name region id dumm_flag',
            'ipsession': 'imsi src_ip dest_ip protocol src_port dest_port burst_time packet_len id dumm_flag insert_time',
            'target': 'imsi targetid level insert_time imei dumm_flag target_name target_category country',
        }
        for table, fields in expected.items():
            self.assertEqual([c[0] for c in self.source.COLUMNS[table]], fields.split())
        self.assertEqual(dict((c[0], c[1]) for c in self.source.COLUMNS['gps'])['lon'], 'float8')
        pg = self.source.schema_sql('postgresql')
        self.assertNotIn('_sim_id', pg)
        self.assertIn('alititude', pg)

    def test_generated_data_is_synthetic_and_joinable(self):
        for tick in range(12):
            rows = self.source.generate(tick)
            self.assertEqual(rows['gps']['imsi'], rows['ipsession']['imsi'])
            self.assertEqual(rows['gps']['imsi'], rows['target']['imsi'])
            self.assertTrue(rows['target']['imsi'].startswith('00101'))
            self.assertTrue(rows['ipsession']['src_ip'].startswith('192.0.2.'))
            for row in rows.values():
                self.assertEqual(row['dumm_flag'], 1)
            self.assertTrue(-180 <= rows['gps']['lon'] <= 180)
            self.assertTrue(-90 <= rows['gps']['lat'] <= 90)

    def test_mysql_changes_are_explicit(self):
        sql = self.source.schema_sql('mysql')
        self.assertIn('DECIMAL(20,8)', sql)
        self.assertIn('_sim_id', sql)
        self.assertEqual(sql.count('PRIMARY KEY'), 3)

    def test_invalid_operation_and_database_rejected_before_connect(self):
        with self.assertRaises(ValueError): self.source.validate_config({'database':'production','engine':'mysql'})
        with self.assertRaises(ValueError): self.source.validate_config({'database':'signal_sim_test','engine':'sqlite'})
        with self.assertRaises(ValueError): self.source.step(None, 'mysql', 'truncate')
        with self.assertRaises(ValueError): self.source.restore_rows(None, 'mysql', {'format':'unknown'})

    def test_mysql_existing_nontransactional_table_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'InnoDB'):
            self.source.verify_schema(Metadata(self.source, engine='MyISAM'), 'mysql')

    def test_mysql_wrong_primary_key_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'primary key'):
            self.source.verify_schema(Metadata(self.source, wrong_key=True), 'mysql')

    def test_portable_mysql_declares_fresh_authentication_dependencies(self):
        self.assertIn('PyMySQL[rsa]==', (ROOT.parent / 'requirements.txt').read_text(encoding='utf-8'))

    def test_pg_connection_uses_public_schema_even_with_custom_role_search_path(self):
        driver = Mock()
        with patch.dict(sys.modules, {'psycopg2': driver}):
            self.source.connect(dict(engine='postgresql', database='signal_sim_test', port=5432, user='test'))
        self.assertEqual(driver.connect.call_args.kwargs.get('options'), '-c search_path=public')

class Metadata:
    def __init__(self, source, engine='InnoDB', wrong_key=False):
        self.source, self.engine, self.wrong_key = source, engine, wrong_key
    def cursor(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, args=()):
        key = next((k for k,t in self.source.TABLES.items() if args and args[0]==t), 'gps')
        if 'information_schema.tables' in sql: self.rows=[(self.engine,)]
        elif 'key_column_usage' in sql: self.rows=[('dumm_flag' if self.wrong_key else '_sim_id' if key=='target' else 'id',)]
        else:
            self.rows=[]
            for name, kind, nullable, _ in self.source.COLUMNS[key]:
                data_type='varchar' if kind.startswith('varchar') else 'int' if kind=='int4' else 'smallint' if kind=='int2' else 'decimal' if kind=='float8' else 'datetime'
                self.rows.append((name,'YES' if nullable else 'NO',data_type,255 if data_type=='varchar' else None,20 if data_type=='decimal' else 32,8 if data_type=='decimal' else 0,int(kind[-2]) if kind.startswith('timestamp') else None))
            if key=='target': self.rows.append(('_sim_id','NO','int',None,32,0,None))
    def fetchall(self): return self.rows
    def fetchone(self): return self.rows[0] if self.rows else None

if __name__ == '__main__':
    unittest.main()
