"""Desktop-only connection lifecycle; SQL simulation remains in signal_source."""
from contextlib import contextmanager
import copy
import re

import signal_source
from dashboard import Manager


DEFAULTS = {
    'mysql': dict(engine='mysql', host='127.0.0.1', port=3306, database='signal_sim_demo', user='root', password=''),
    'postgresql': dict(engine='postgresql', host='127.0.0.1', port=5432, database='signal_sim_demo', user='postgres', password=''),
}


def normalize(config):
    allowed = {'engine', 'host', 'port', 'database', 'user', 'password', 'reusePassword'}
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError('连接参数包含不支持的字段')
    result = {key: config.get(key) for key in ('engine', 'host', 'port', 'database', 'user', 'password')}
    if type(result['port']) is not int or not 1 <= result['port'] <= 65535:
        raise ValueError('端口须为 1～65535 的整数')
    for field, maximum in [('host', 255), ('user', 128)]:
        if not isinstance(result[field], str) or not result[field].strip() or len(result[field]) > maximum or '\x00' in result[field]:
            raise ValueError('主机和用户名不能为空')
        result[field] = result[field].strip()
    if not isinstance(result['password'], str) or len(result['password']) > 4096:
        raise ValueError('密码格式不正确')
    signal_source.validate_config(result)
    return result


def public(config):
    return {**{key: config[key] for key in ('engine', 'host', 'port', 'database', 'user')},
            'hasPassword': bool(config.get('password'))}


@contextmanager
def server_connection(config):
    args = dict(host=config['host'], port=config['port'], user=config['user'],
                password=config['password'], connect_timeout=10)
    if config['engine'] == 'mysql':
        import pymysql
        conn = pymysql.connect(**args, charset='utf8mb4', autocommit=True)
    else:
        import psycopg2
        conn = psycopg2.connect(**args, dbname='postgres')
        conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()


def probe_connection(config):
    """Authenticate and inspect only: this path never creates a database or table."""
    try:
        if config['engine'] == 'postgresql':
            # Existing target users need no CONNECT permission on the maintenance DB.
            try:
                connection = signal_source.connect(config)
            except Exception:
                with server_connection(config) as conn, conn.cursor() as cursor:
                    cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s', (config['database'],))
                    if cursor.fetchone() is not None:
                        raise RuntimeError('Target database cannot be accessed')
                return dict(databaseExists=False, schemaReady=False)
            try:
                try:
                    signal_source.verify_schema(connection, 'postgresql')
                    ready = True
                except (RuntimeError, ValueError):
                    ready = False
                return dict(databaseExists=True, schemaReady=ready)
            finally:
                connection.close()
        with server_connection(config) as conn, conn.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.execute('SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s'
                           if config['engine'] == 'mysql' else 'SELECT datname FROM pg_database WHERE datname=%s',
                           (config['database'],))
            exists = cursor.fetchone() is not None
        ready = False
        if exists:
            connection = signal_source.connect(config)
            try:
                signal_source.verify_schema(connection, config['engine'])
                ready = True
            except (RuntimeError, ValueError):
                pass
            finally:
                connection.close()
        return dict(databaseExists=exists, schemaReady=ready)
    except Exception:
        # Driver exception messages can include endpoint/auth details. Never return them to a log or renderer.
        raise RuntimeError('连接失败，请检查数据库是否启动、主机、端口和账号密码') from None


def prepare_database(config):
    """Explicit operator action, constrained to a validated dedicated simulator database."""
    signal_source.validate_config(config)
    if config['engine'] == 'postgresql':
        try:
            connection = signal_source.connect(config)
        except Exception:
            pass
        else:
            connection.close()
            return
    with server_connection(config) as conn, conn.cursor() as cursor:
        if config['engine'] == 'mysql':
            cursor.execute('SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s', (config['database'],))
            if cursor.fetchone() is None:
                cursor.execute('CREATE DATABASE `' + config['database'] + '` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')
        else:
            cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s', (config['database'],))
            if cursor.fetchone() is None:
                from psycopg2 import sql
                cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(config['database'])))


class DesktopManager(Manager):
    def __init__(self, profiles=None, source=signal_source, probe=probe_connection, prepare=prepare_database):
        chosen = copy.deepcopy(DEFAULTS)
        for key, config in (profiles or {}).items():
            if key not in chosen or config.get('engine') != key:
                raise ValueError('不支持的连接类型')
            chosen[key] = normalize(config)
        super().__init__(chosen, source)
        self.probe = probe
        self.prepare_database = prepare

    def public_profiles(self):
        with self.lock:
            return {key: public(config) for key, config in self.profiles.items()}

    def configure(self, config, test_only=False):
        normalized = normalize(config)
        key = normalized['engine']
        with self.lock:
            if not test_only and self.states[key]['running']:
                raise RuntimeError('请先停止此数据源的自动模拟，再修改连接')
            old = self.profiles[key]
            identity = ('engine', 'host', 'port', 'database', 'user')
            if config.get('reusePassword') is True and not normalized['password'] and all(old[k] == normalized[k] for k in identity):
                normalized['password'] = old['password']
            result = self.probe(normalized)
            if not test_only:
                self.profiles[key] = normalized
                self.states[key].update(error=None)
            return dict(config=public(normalized), **result)

    def initialize_profile(self, key):
        self.reserve(key)
        config = dict(self.profile(key))
        conn = None
        try:
            self.prepare_database(config)
            conn = self.source.connect(config)
            with self.source.ownership_lock(conn, config['engine']):
                with conn.cursor() as cursor:
                    cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=' +
                                   ('DATABASE()' if config['engine'] == 'mysql' else "'public'"))
                    present = {row[0] for row in cursor.fetchall()}
                # Never add simulator tables to a database already holding unrelated tables.
                if present - set(self.source.TABLES.values()):
                    raise RuntimeError('专用库中存在其他业务表，初始化已拒绝')
                created = self.source.initialize(conn, config['engine'])
            return dict(created=created)
        except Exception:
            raise RuntimeError('初始化未完成：需要专用空库和建库建表权限；已有三表须结构一致，不会覆盖或清空数据') from None
        finally:
            if conn:
                conn.close()
            with self.lock:
                self.states[key].update(running=False, stopping=False)
