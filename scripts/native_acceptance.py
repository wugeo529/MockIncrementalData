"""Native source acceptance. Creates and cleans only its own randomly named fixture DB."""
from pathlib import Path
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import signal_source
from dashboard import make_server
from desktop_service import DesktopManager, server_connection


def run(config):
    engine = config['engine']
    database = 'signal_sim_accept_' + uuid.uuid4().hex[:16]
    config = dict(config, database=database)
    created = False
    manager = DesktopManager()
    server = None
    results = []
    try:
        proof = manager.configure(config, test_only=True)
        assert not proof['databaseExists']
        manager.configure(config)
        if engine == 'postgresql':
            manager.prepare_database(config)
            created = True
            from psycopg2 import sql
            with server_connection(config) as connection, connection.cursor() as cursor:
                cursor.execute(sql.SQL('ALTER DATABASE {} SET search_path=fixture_shadow,public').format(sql.Identifier(database)))
            connection = signal_source.connect(config)
            try:
                with connection.cursor() as cursor:
                    cursor.execute('CREATE SCHEMA fixture_shadow')
                    cursor.execute('SHOW search_path')
                    assert cursor.fetchone()[0] == 'public'
                connection.commit()
            finally:
                connection.close()
            results.append('custom database search_path overridden to public before DDL/DML')
        assert manager.initialize_profile(engine)['created']
        created = True
        assert not manager.initialize_profile(engine)['created']
        def counts():
            snapshot = manager.snapshot(engine)
            assert snapshot['connected'], snapshot.get('error')
            return {key: value['count'] for key, value in snapshot['tables'].items()}
        assert counts() == {'gps': 6, 'ipsession': 6, 'target': 6}
        manager.manual(engine, 'insert')
        assert counts() == {'gps': 7, 'ipsession': 7, 'target': 6}
        manager.manual(engine, 'update')
        assert counts() == {'gps': 7, 'ipsession': 7, 'target': 6}
        manager.manual(engine, 'delete')
        assert counts() == {'gps': 6, 'ipsession': 6, 'target': 5}
        manager.start(engine, .2, 3)
        manager.wait(engine, 10)
        assert not manager.runtime(engine)['running']
        assert manager.runtime(engine)['runCompleted'] == 3
        assert counts()['gps'] == 8
        manager.start(engine, 5, 100)
        manager.stop(engine)
        manager.wait(engine, 10)
        assert not manager.runtime(engine)['running']
        results.append('initialize / preserve existing / INSERT / UPDATE / DELETE / bounded auto / active stop')
        server = make_server(manager, 0, desktop=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(server.server_port)
        with urllib.request.urlopen(base + '/api/bootstrap') as response:
            public = json.load(response)
        assert config['password'] not in json.dumps(public) if config['password'] else True
        def post(route, body, token):
            request = urllib.request.Request(base + route, data=json.dumps(body).encode(),
                headers={'Content-Type': 'application/json', 'Origin': base, 'X-Simulator-Token': token})
            return urllib.request.urlopen(request)
        try:
            post('/api/connection/save', config, 'wrong')
            raise AssertionError('Wrong nonce was accepted')
        except urllib.error.HTTPError as failure:
            assert failure.code == 403
        with post('/api/connection/test', config, public['token']) as response:
            assert json.load(response)['schemaReady']
        with post('/api/connection/save', config, public['token']) as response:
            assert 'password' not in json.load(response)['config']
        results.append('HTTP connection test/save / no secret response / wrong nonce rejected')
        # Initialization must never add/reinterpret tables in a nonempty foreign schema.
        connection = signal_source.connect(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute('CREATE TABLE unrelated_guard (id INTEGER)')
            connection.commit()
        finally:
            connection.close()
        before = counts()
        try:
            manager.initialize_profile(engine)
            raise AssertionError('Foreign table was silently accepted')
        except RuntimeError:
            pass
        assert counts() == before
        results.append('foreign table initialization rejected / existing records preserved')
        return dict(engine=engine, passed=True, checks=results, finalCounts=counts())
    finally:
        if server:
            server.shutdown()
            server.server_close()
        manager.close()
        if created:
            assert database.startswith('signal_sim_accept_') and len(database) == 34
            with server_connection(config) as conn, conn.cursor() as cursor:
                if engine == 'mysql':
                    cursor.execute('DROP DATABASE `' + database + '`')
                else:
                    from psycopg2 import sql
                    cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    engine = os.environ.get('SOURCE_ENGINE', 'mysql')
    config = json.loads(args.config.read_text(encoding='utf-8-sig')) if args.config else dict(
        engine=engine, host=os.environ.get('DATABASE_HOST', '127.0.0.1'),
        port=int(os.environ.get('DATABASE_PORT', '3306' if engine == 'mysql' else '5432')),
        user=os.environ.get('DATABASE_USER', 'root' if engine == 'mysql' else 'postgres'),
        password=os.environ.get('DATABASE_PASSWORD', ''))
    print(json.dumps(run(config), ensure_ascii=False, indent=2))
