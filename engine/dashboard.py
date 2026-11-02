"""Loopback-only visual controls for the existing synthetic source; no schema writes."""
import argparse
import datetime as dt
import json
import math
import pathlib
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import signal_source

ROOT = pathlib.Path(__file__).resolve().parent
ACTIONS = ('insert', 'update', 'delete')


class Manager:
    def __init__(self, profiles, source=signal_source):
        self.profiles = profiles
        self.source = source
        self.lock = threading.RLock()
        self.states = {key: dict(running=False, stopping=False, completed=0, error=None, events=[]) for key in profiles}
        self.threads = {}
        self.stops = {}

    def profile(self, key):
        if key not in self.profiles:
            raise ValueError('未知数据源')
        return self.profiles[key]

    def runtime(self, key):
        self.profile(key)
        with self.lock:
            return json.loads(json.dumps(self.states[key]))

    def event(self, key, action):
        with self.lock:
            state = self.states[key]
            state['completed'] += 1
            state['events'].insert(0, dict(action=action, committedAt=dt.datetime.now().astimezone().isoformat(timespec='seconds')))
            del state['events'][20:]

    def reserve(self, key):
        self.profile(key)
        with self.lock:
            if self.states[key]['running']:
                raise RuntimeError('模拟器正在写入，请先停止自动模拟')
            self.states[key].update(running=True, stopping=False, error=None)

    def manual(self, key, action):
        config = self.profile(key)
        if action not in ACTIONS:
            raise ValueError('不支持的操作')
        self.reserve(key)
        conn = None
        try:
            conn = self.source.connect(config)
            with self.source.ownership_lock(conn, config['engine']):
                self.source.verify_schema(conn, config['engine'])
                self.source.step(conn, config['engine'], action)
                self.event(key, action)
        except Exception:
            with self.lock:
                self.states[key]['error'] = '写入未完成，请检查数据库连接、表结构或是否有其他模拟器占用'
            raise RuntimeError(self.states[key]['error']) from None
        finally:
            if conn:
                conn.close()
            with self.lock:
                self.states[key]['running'] = False

    def start(self, key, interval, ticks):
        config = self.profile(key)
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or not math.isfinite(interval) or not .2 <= interval <= 86400:
            raise ValueError('发送间隔须为0.2至86400秒')
        if type(ticks) is not int or not 1 <= ticks <= 1000000:
            raise ValueError('批次数须为1至1000000的整数')
        with self.lock:
            self.reserve(key)
            stop = threading.Event()
            self.stops[key] = stop
            ready = threading.Event()
            self.states[key].update(interval=interval, ticks=ticks, runCompleted=0)

            def run():
                conn = None
                try:
                    conn = self.source.connect(config)
                    with self.source.ownership_lock(conn, config['engine']):
                        self.source.verify_schema(conn, config['engine'])
                        for number in range(ticks):
                            if stop.is_set():
                                break
                            action = 'delete' if number % 10 == 9 else 'update' if number % 3 == 2 else 'insert'
                            self.source.step(conn, config['engine'], action)
                            self.event(key, action)
                            with self.lock:
                                self.states[key]['runCompleted'] = number + 1
                            ready.set()
                            if number + 1 < ticks and stop.wait(interval):
                                break
                except Exception:
                    with self.lock:
                        self.states[key]['error'] = '自动模拟已停止：请检查数据库连接、表结构或其他模拟器占用'
                finally:
                    if conn:
                        conn.close()
                    with self.lock:
                        self.states[key].update(running=False, stopping=False)
                    ready.set()

            thread = threading.Thread(target=run, name='signal-simulator-' + key, daemon=True)
            self.threads[key] = thread
            thread.start()
        if not ready.wait(30):
            self.stop(key)
            raise RuntimeError('连接等待超时，已请求停止；请刷新确认状态')
        error = self.runtime(key)['error']
        if error:
            raise RuntimeError(error)

    def stop(self, key):
        self.profile(key)
        with self.lock:
            if key in self.stops:
                self.stops[key].set()
                if self.states[key]['running']:
                    self.states[key]['stopping'] = True

    def wait(self, key, timeout):
        with self.lock:
            thread = self.threads.get(key)
        if thread:
            thread.join(timeout)

    def close(self):
        for key in self.profiles:
            self.stop(key)
        for key in self.profiles:
            self.wait(key, 12)

    def snapshot(self, key):
        config = self.profile(key)
        result = dict(profile=key, engine=config['engine'], runtime=self.runtime(key), connected=False, tables={}, error=None)
        conn = None
        try:
            conn = self.source.connect(config)
            self.source.verify_schema(conn, config['engine'])
            for name, table in self.source.TABLES.items():
                columns = [field[0] for field in self.source.COLUMNS[name]]
                if key == 'mysql' and name == 'target':
                    columns.append('_sim_id')
                order = 'id DESC' if name != 'target' else 'insert_time DESC, imsi ASC'
                with conn.cursor() as cur:
                    cur.execute('SELECT COUNT(*) FROM ' + table)
                    count = cur.fetchone()[0]
                    cur.execute('SELECT ' + ','.join(columns) + ' FROM ' + table + ' ORDER BY ' + order + ' LIMIT 10')
                    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
                result['tables'][name] = dict(count=count, columns=columns, rows=rows)
            conn.rollback()
            result['connected'] = True
        except Exception:
            result['error'] = '源库读取失败，请检查本机数据库是否启动及配置文件是否正确'
        finally:
            if conn:
                conn.close()
        return result


def make_server(manager, port, desktop=False):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def respond(self, code, value, content_type='application/json; charset=utf-8'):
            payload = json.dumps(value, ensure_ascii=False, default=str).encode() if content_type.startswith('application/json') else value
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def allowed_host(self):
            return self.headers.get('Host') in ('127.0.0.1:' + str(self.server.server_port), 'localhost:' + str(self.server.server_port))

        def do_GET(self):
            if not self.allowed_host():
                return self.respond(403, {'error': '请通过本机地址访问'})
            path = urlsplit(self.path)
            static = {'/': ('dashboard.html', 'text/html; charset=utf-8'), '/dashboard.js': ('dashboard.js', 'text/javascript; charset=utf-8'), '/connections.js': ('connections.js', 'text/javascript; charset=utf-8'), '/dashboard.css': ('dashboard.css', 'text/css; charset=utf-8')}
            if path.path in static:
                file, kind = static[path.path]
                return self.respond(200, (ROOT / file).read_bytes(), kind)
            if path.path == '/api/bootstrap':
                return self.respond(200, dict(profiles=list(manager.profiles), token=self.server.token, desktop=desktop,
                    connections=manager.public_profiles() if hasattr(manager, 'public_profiles') else {}))
            if path.path == '/api/state':
                try:
                    profile = parse_qs(path.query).get('profile', ['mysql'])[0]
                    return self.respond(200, manager.snapshot(profile))
                except ValueError as exc:
                    return self.respond(400, {'error': str(exc)})
            return self.respond(404, {'error': '入口不存在'})

        def do_POST(self):
            host = self.headers.get('Host', '')
            if not self.allowed_host() or self.headers.get('Origin') != 'http://' + host or not secrets.compare_digest(self.headers.get('X-Simulator-Token', ''), self.server.token):
                return self.respond(403, {'error': '请在本机面板中操作'})
            routes = ['/api/action'] + (['/api/connection/test', '/api/connection/save', '/api/initialize', '/api/shutdown'] if desktop else [])
            if self.path not in routes:
                return self.respond(404, {'error': '入口不存在'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.respond(400, {'error': '需要JSON请求'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 1 <= length <= 16384:
                    raise ValueError('请求大小不正确')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('请求格式不正确')
                if self.path in ('/api/connection/test', '/api/connection/save'):
                    return self.respond(200, manager.configure(data, test_only=self.path.endswith('/test')))
                if self.path == '/api/initialize':
                    return self.respond(200, manager.initialize_profile(data.get('profile')))
                if self.path == '/api/shutdown':
                    self.respond(200, {'ok': True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                key, action = data.get('profile'), data.get('action')
                if action == 'start':
                    manager.start(key, data.get('interval'), data.get('ticks'))
                elif action == 'stop':
                    manager.stop(key)
                elif action in ACTIONS:
                    manager.manual(key, action)
                else:
                    raise ValueError('不支持的操作')
                self.respond(200, {'ok': True, 'runtime': manager.runtime(key)})
            except (ValueError, TypeError):
                self.respond(400, {'error': '参数无效，请检查发送间隔、批次数和操作'})
            except RuntimeError as exc:
                self.respond(409, {'error': str(exc)})
            except Exception:
                self.respond(500, {'error': '操作失败，请检查本机数据库连接'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.token = secrets.token_urlsafe(32)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mysql-config', type=pathlib.Path)
    parser.add_argument('--pg-config', type=pathlib.Path)
    parser.add_argument('--port', type=int, default=18117)
    args = parser.parse_args()
    profiles = {}
    for key, path in (('mysql', args.mysql_config), ('postgresql', args.pg_config)):
        if path:
            config = json.loads(path.read_text(encoding='utf-8-sig'))
            signal_source.validate_config(config)
            if config['engine'] != key:
                parser.error('配置类型与参数不一致')
            profiles[key] = config
    if not profiles:
        parser.error('至少提供一个数据库配置文件')
    manager = Manager(profiles)
    server = make_server(manager, args.port)
    print('信号模拟面板 http://127.0.0.1:' + str(server.server_port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        manager.close()


if __name__ == '__main__':
    main()
