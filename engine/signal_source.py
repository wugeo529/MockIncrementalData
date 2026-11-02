"""Synthetic signal source. Writes only its explicitly named simulator database."""
import argparse
import datetime as dt
import json
import math
import os
import pathlib
import time
from contextlib import contextmanager

TABLES = {'gps': 's_signal_2_1_gps', 'ipsession': 's_signal_2_1_ipsession', 'target': 's_signal_2_1_target'}
# name, original PostgreSQL type, nullable, comment. Preserve the source spelling alititude.
COLUMNS = {
    'gps': [
        ('imsi', 'varchar(255)', True, ''),
        ('satellite_num', 'int4', True, '卫星编号，5，6，8，9，65535'),
        ('position_num', 'int4', True, '阵地编号，0，1，99，3'),
        ('lon', 'float8', True, '经度'), ('lat', 'float8', True, '纬度'),
        ('insert_time', 'timestamp(6)', True, '输入时间'), ('gps_time', 'timestamp(6)', True, '位置时间'),
        ('means', 'varchar(255)', True, '手段,只有3'), ('direction', 'int4', True, '方向'),
        ('alititude', 'float8', True, '高度'), ('speed', 'float8', True, '速度'),
        ('beam_num', 'int4', True, '波束号，0~255'), ('terminal_type_name', 'varchar(255)', True, '终端类型名称'),
        ('satellite_name', 'varchar(255)', True, '卫星名称'), ('region', 'int4', True, '洋区'),
        ('id', 'int4', False, ''), ('dumm_flag', 'int2', False, '仿真标识，1：仿真数据，0真实数据'),
    ],
    'ipsession': [
        ('imsi', 'varchar(255)', True, ''), ('src_ip', 'varchar(255)', True, '源IP地址'),
        ('dest_ip', 'varchar(255)', True, '目的IP地址'), ('protocol', 'int4', True, '协议类型，6，1，17，89'),
        ('src_port', 'int4', True, '源端口，0~65535'), ('dest_port', 'int4', True, '目的端口，0~65535'),
        ('burst_time', 'timestamp(6)', True, '出联时间或突发时间'), ('packet_len', 'int4', True, '报文长度'),
        ('id', 'int4', False, ''), ('dumm_flag', 'int2', False, '仿真标识，1：仿真数据，0真实数据'),
        ('insert_time', 'timestamp(6)', True, '输入时间'),
    ],
    'target': [
        ('imsi', 'varchar(255)', True, 'imsi'), ('targetid', 'varchar(255)', True, '目标ID'),
        ('level', 'varchar(255)', True, '等级'), ('insert_time', 'timestamp(0)', True, '新增时间'),
        ('imei', 'varchar(255)', True, 'IMEI'), ('dumm_flag', 'int2', False, '仿真标识，1：仿真数据，0真实数据'),
        ('target_name', 'varchar(255)', True, '目标名称'), ('target_category', 'varchar(255)', True, '目标类别'),
        ('country', 'varchar(255)', True, '国家'),
    ],
}

def mysql_type(original):
    return {'int4': 'INT', 'int2': 'SMALLINT', 'float8': 'DECIMAL(20,8)',
            'timestamp(6)': 'DATETIME(6)', 'timestamp(0)': 'DATETIME(0)'}.get(original, original.upper())

def schema_sql(engine):
    if engine not in ('postgresql', 'mysql'):
        raise ValueError('engine must be postgresql or mysql')
    statements = []
    for key, table in TABLES.items():
        fields = []
        for name, kind, nullable, comment in COLUMNS[key]:
            field = f'{name} {mysql_type(kind) if engine == "mysql" else kind}' + ('' if nullable else ' NOT NULL')
            if engine == 'mysql' and comment:
                field += " COMMENT '" + comment.replace("'", "''") + "'"
            fields.append(field)
        if key == 'gps' or (key == 'ipsession' and engine == 'mysql'):
            fields.append('PRIMARY KEY (id)')
        if key == 'target' and engine == 'mysql':
            fields.extend(['_sim_id INT NOT NULL', 'PRIMARY KEY (_sim_id)'])
        statements.append(f'CREATE TABLE {table} (\n  ' + ',\n  '.join(fields) +
                          ('\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;' if engine == 'mysql' else '\n);'))
        if engine == 'postgresql':
            for name, _, _, comment in COLUMNS[key]:
                if comment:
                    statements.append(f"COMMENT ON COLUMN {table}.{name} IS '" + comment.replace("'", "''") + "';")
    return '\n\n'.join(statements) + '\n'

def generate(tick, now=None):
    if not isinstance(tick, int) or tick < 0 or tick > 2000000000:
        raise ValueError('tick outside int4 simulation range')
    now = (now or dt.datetime.now(dt.timezone.utc)).replace(tzinfo=None)
    unit = tick % 6 + 1
    imsi = '001010000000' + f'{unit:03d}'
    ident = 1000001 + tick
    gps = dict(imsi=imsi, satellite_num=[5, 6, 8, 9, 65535][tick % 5], position_num=[0, 1, 99, 3][tick % 4],
               lon=round(121.2 + unit * .03 + math.sin(tick / 9) * .01, 8),
               lat=round(29.8 + unit * .02 + math.cos(tick / 9) * .01, 8),
               insert_time=now, gps_time=now - dt.timedelta(seconds=2), means='3', direction=(tick * 17) % 360,
               alititude=round(20 + unit * 2.5, 8), speed=round(8 + (tick % 12) * .7, 8), beam_num=(tick * 13) % 256,
               terminal_type_name='仿真遥测终端', satellite_name='模拟通信星-' + str(tick % 3 + 1),
               region=tick % 4, id=ident, dumm_flag=1)
    ip = dict(imsi=imsi, src_ip=f'192.0.2.{unit + 10}', dest_ip=f'198.51.100.{unit + 20}',
              protocol=[6, 17, 1, 89][tick % 4], src_port=10000 + tick % 50000,
              dest_port=[443, 8080, 9000][tick % 3], burst_time=now - dt.timedelta(seconds=1),
              packet_len=128 + tick % 1300, id=ident, dumm_flag=1, insert_time=now)
    target = dict(imsi=imsi, targetid=f'SIM-TARGET-{unit:03d}', level=['一般', '关注', '重点'][tick % 3],
                  insert_time=now.replace(microsecond=0), imei='990000000000' + f'{unit:03d}', dumm_flag=1,
                  target_name=f'模拟科考终端-{unit:02d}', target_category='仿真移动遥测终端', country='测试区域-' + str(unit % 3 + 1))
    return {'gps': gps, 'ipsession': ip, 'target': target}

def validate_config(config):
    import re
    if config.get('engine') not in ('postgresql', 'mysql'):
        raise ValueError('Only postgresql/mysql profiles are supported')
    if not re.fullmatch(r'signal_sim_[a-z0-9_]{1,40}', config.get('database', '')):
        raise ValueError('Use a dedicated database named signal_sim_<name>; production names are refused')
    if not 1 <= int(config.get('port', 0)) <= 65535:
        raise ValueError('Invalid database port')

def connect(config):
    validate_config(config)
    password = os.environ.get(config.get('password_env', 'SIGNAL_SIM_DB_PASSWORD'), config.get('password', ''))
    args = dict(host=config.get('host', '127.0.0.1'), port=int(config['port']),
                user=config['user'], password=password, database=config['database'], connect_timeout=10)
    if config['engine'] == 'mysql':
        import pymysql
        return pymysql.connect(**args, charset='utf8mb4', autocommit=False)
    import psycopg2
    return psycopg2.connect(**args, options='-c search_path=public')

@contextmanager
def ownership_lock(conn, engine):
    """Exclusive simulator ownership; not a product/source checkpoint."""
    with conn.cursor() as cursor:
        cursor.execute('SELECT GET_LOCK(%s,0)' if engine == 'mysql' else 'SELECT pg_try_advisory_lock(%s)',
                       ('signal_simulator_v1' if engine == 'mysql' else 20710301,))
        if not cursor.fetchone()[0]:
            raise RuntimeError('Another simulator owns this database/server; stop it first')
    try:
        yield
    finally:
        conn.rollback()
        with conn.cursor() as cursor:
            cursor.execute('SELECT RELEASE_LOCK(%s)' if engine == 'mysql' else 'SELECT pg_advisory_unlock(%s)',
                           ('signal_simulator_v1' if engine == 'mysql' else 20710301,))
        conn.commit()

def insert(cursor, key, row, engine):
    values = dict(row)
    if key == 'target' and engine == 'mysql':
        values['_sim_id'] = int(row['imsi'][-3:])
    fields = list(values)
    cursor.execute(f'INSERT INTO {TABLES[key]} (' + ','.join(fields) + ') VALUES (' + ','.join(['%s'] * len(fields)) + ')',
                   tuple(values[f] for f in fields))

def initialize(conn, engine, seed=True):
    """Never drop, truncate, or reinterpret an existing schema."""
    with conn.cursor() as cursor:
        cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=' +
                       ('DATABASE()' if engine == 'mysql' else "'public'"))
        present = {r[0] for r in cursor.fetchall()}
        overlap = present.intersection(TABLES.values())
        if overlap:
            if overlap != set(TABLES.values()):
                raise RuntimeError('Partial schema exists; inspect manually, no destructive reset provided')
            verify_schema(conn, engine)
            return False
        for statement in schema_sql(engine).split(';'):
            if statement.strip(): cursor.execute(statement)
        if seed:
            for tick in range(6):
                for key, row in generate(tick).items(): insert(cursor, key, row, engine)
    conn.commit()
    verify_schema(conn, engine)
    return True

def verify_schema(conn, engine):
    with conn.cursor() as cursor:
        for key, table in TABLES.items():
            schema = 'DATABASE()' if engine == 'mysql' else "'public'"
            if engine == 'mysql':
                cursor.execute('SELECT engine FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s', (table,))
                table_meta = cursor.fetchone()
                if not table_meta or table_meta[0] != 'InnoDB': raise RuntimeError('InnoDB required for atomic simulation: ' + table)
            cursor.execute('SELECT k.column_name FROM information_schema.table_constraints t JOIN information_schema.key_column_usage k '
                           'ON k.constraint_schema=t.constraint_schema AND k.constraint_name=t.constraint_name '
                           'AND k.table_schema=t.table_schema AND k.table_name=t.table_name '
                           "WHERE t.constraint_type='PRIMARY KEY' AND t.table_schema=" + schema + ' AND t.table_name=%s ORDER BY k.ordinal_position', (table,))
            expected_key = ['_sim_id'] if engine == 'mysql' and key == 'target' else ['id'] if engine == 'mysql' or key == 'gps' else []
            if [r[0] for r in cursor.fetchall()] != expected_key: raise RuntimeError('Unexpected primary key: ' + table)
            cursor.execute('SELECT column_name,is_nullable,data_type,character_maximum_length,numeric_precision,numeric_scale,datetime_precision FROM information_schema.columns WHERE table_schema=' +
                           ('DATABASE()' if engine == 'mysql' else "'public'") + ' AND table_name=%s ORDER BY ordinal_position', (table,))
            actual = list(cursor.fetchall())
            expected = [(c[0], 'YES' if c[2] else 'NO') for c in COLUMNS[key]]
            if key == 'target' and engine == 'mysql': expected.append(('_sim_id', 'NO'))
            if [r[:2] for r in actual] != expected: raise RuntimeError('Schema mismatch: ' + table)
            for row, column in zip(actual, COLUMNS[key]):
                kind = column[1]
                valid = True
                if kind.startswith('varchar'): valid = row[2] in ('character varying', 'varchar') and row[3] == 255
                elif kind == 'int4': valid = row[2] in ('integer', 'int')
                elif kind == 'int2': valid = row[2] == 'smallint'
                elif kind == 'float8': valid = row[2] == 'double precision' if engine == 'postgresql' else row[2] == 'decimal' and row[4:6] == (20, 8)
                elif kind.startswith('timestamp'): valid = row[2] == ('timestamp without time zone' if engine == 'postgresql' else 'datetime') and row[6] == int(kind[-2])
                if not valid: raise RuntimeError('Type/precision mismatch: ' + table + '.' + column[0])

def step(conn, engine, action='insert', fail_after=None):
    if action not in ('insert', 'update', 'delete'):
        raise ValueError('Unknown operation')
    try:
        with conn.cursor() as cursor:
            cursor.execute(f'SELECT MAX(id) FROM {TABLES["gps"]} WHERE dumm_flag=1')
            last = cursor.fetchone()[0]
            if last is None: raise RuntimeError('No synthetic GPS rows; run init against a fresh database')
            if action == 'insert':
                rows = generate(int(last) - 1000000)
                for key in ('gps', 'ipsession'): insert(cursor, key, rows[key], engine)
                target = rows['target']
                cursor.execute(f'UPDATE {TABLES["target"]} SET level=%s,target_name=%s WHERE imsi=%s AND dumm_flag=1',
                               (target['level'], target['target_name'], target['imsi']))
                if cursor.rowcount == 0:
                    cursor.execute(f'SELECT COUNT(*) FROM {TABLES["target"]} WHERE imsi=%s AND dumm_flag=1', (target['imsi'],))
                    if cursor.fetchone()[0] == 0: insert(cursor, 'target', target, engine)
            elif action == 'update':
                cursor.execute(f'UPDATE {TABLES["gps"]} SET speed=COALESCE(speed,0)+1,direction=MOD(COALESCE(direction,0)+5,360) WHERE id=%s AND dumm_flag=1', (last,))
                cursor.execute(f'UPDATE {TABLES["ipsession"]} SET packet_len=COALESCE(packet_len,0)+1 WHERE id=%s AND dumm_flag=1', (last,))
                cursor.execute(f'UPDATE {TABLES["target"]} SET level=%s WHERE imsi=(SELECT imsi FROM {TABLES["gps"]} WHERE id=%s LIMIT 1) AND dumm_flag=1', ('已复核', last))
            else:
                cursor.execute(f'SELECT imsi FROM {TABLES["gps"]} WHERE id=%s AND dumm_flag=1 LIMIT 1', (last,))
                imsi = cursor.fetchone()[0]
                cursor.execute(f'DELETE FROM {TABLES["gps"]} WHERE id=%s AND dumm_flag=1', (last,))
                cursor.execute(f'DELETE FROM {TABLES["ipsession"]} WHERE id=%s AND dumm_flag=1', (last,))
                cursor.execute(f'DELETE FROM {TABLES["target"]} WHERE imsi=%s AND dumm_flag=1', (imsi,))
            if fail_after: raise RuntimeError('Injected rollback check')
        conn.commit()
    except BaseException:
        conn.rollback()
        raise

def status(conn, engine):
    verify_schema(conn, engine)
    result = {'engine': engine, 'counts': {}, 'latest': {}}
    with conn.cursor() as cursor:
        for key, table in TABLES.items():
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            result['counts'][key] = cursor.fetchone()[0]
            cursor.execute(f'SELECT * FROM {table} ORDER BY insert_time DESC LIMIT 1')
            row = cursor.fetchone()
            result['latest'][key] = dict(zip([d[0] for d in cursor.description], row)) if row else None
    conn.rollback()
    return result

def export_rows(conn, engine):
    verify_schema(conn, engine)
    conn.rollback()
    result = {'format': 'SIGNAL_SIM_V1', 'timeConvention': 'UTC without timezone', 'tables': {}}
    with conn.cursor() as cursor:
        # One source transaction gives a consistent snapshot of all three tables.
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        for key, table in TABLES.items():
            fields = [c[0] for c in COLUMNS[key]]
            cursor.execute('SELECT ' + ','.join(fields) + f' FROM {table} ORDER BY ' + ('imsi' if key == 'target' else 'id'))
            result['tables'][key] = [dict(zip(fields, row)) for row in cursor.fetchall()]
    conn.rollback()
    return result

def restore_rows(conn, engine, snapshot):
    if snapshot.get('format') != 'SIGNAL_SIM_V1' or set(snapshot.get('tables', {})) != set(TABLES):
        raise ValueError('Unsupported source snapshot')
    initialize(conn, engine, seed=False)
    try:
        with conn.cursor() as cursor:
            for key, table in TABLES.items():
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                if cursor.fetchone()[0]: raise RuntimeError('Restore requires empty tables; existing data is never overwritten')
                for row in snapshot['tables'][key]:
                    if set(row) != {c[0] for c in COLUMNS[key]} or row.get('dumm_flag') != 1:
                        raise ValueError('Snapshot contains unexpected fields or non-synthetic records')
                    insert(cursor, key, row, engine)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'status', 'step', 'run', 'stop', 'ddl', 'export', 'restore'])
    parser.add_argument('--config', type=pathlib.Path)
    parser.add_argument('--engine', choices=['mysql', 'postgresql'], default='postgresql')
    parser.add_argument('--operation', choices=['insert', 'update', 'delete'], default='insert')
    parser.add_argument('--interval', type=float, default=5)
    parser.add_argument('--ticks', type=int, default=120, help='bounded run; default 120 batches')
    parser.add_argument('--state-dir', type=pathlib.Path, default=pathlib.Path('.signal-sim-runtime'))
    parser.add_argument('--file', type=pathlib.Path, help='snapshot JSON path for export/restore')
    args = parser.parse_args()
    if args.action == 'ddl':
        print(schema_sql(args.engine)); return
    if not args.config: parser.error('--config is required')
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    validate_config(config)
    # Separate stop request by database identity, so one profile cannot stop the other.
    import hashlib
    identity = json.dumps([config['engine'], config.get('host'), config['port'], config['database']])
    stop = args.state_dir / (hashlib.sha256(identity.encode()).hexdigest()[:16] + '.stop')
    args.state_dir.mkdir(parents=True, exist_ok=True)
    if args.action == 'stop':
        stop.write_text('stop', encoding='utf-8'); print('Stop requested; current committed batch finishes first'); return
    if args.interval < .2 or not math.isfinite(args.interval) or not 1 <= args.ticks <= 1000000:
        parser.error('interval must be finite >=0.2 seconds; ticks 1..1000000')
    conn = connect(config)
    try:
        if args.action == 'status':
            print(json.dumps(status(conn, config['engine']), ensure_ascii=False, default=str, indent=2)); return
        with ownership_lock(conn, config['engine']):
            if args.action == 'init':
                created = initialize(conn, config['engine']); print('Initialized synthetic rows' if created else 'Existing schema verified; data preserved')
            elif args.action == 'step':
                verify_schema(conn, config['engine']); step(conn, config['engine'], args.operation); print('Committed ' + args.operation)
            elif args.action in ('export', 'restore'):
                if not args.file: parser.error('--file is required for export/restore')
                if args.action == 'export':
                    conn.rollback()
                    snapshot = export_rows(conn, config['engine'])
                    with args.file.open('x', encoding='utf-8') as output:
                        json.dump(snapshot, output, ensure_ascii=False, default=str, indent=2)
                    print('Synthetic rows exported; credentials are not included')
                else:
                    restore_rows(conn, config['engine'], json.loads(args.file.read_text(encoding='utf-8-sig')))
                    print('Snapshot restored into empty simulator tables')
            else:
                verify_schema(conn, config['engine'])
                stop.unlink(missing_ok=True)
                for n in range(args.ticks):
                    if stop.exists(): break
                    # Repeating inserts/updates/deletes demonstrates source DML, not full table replacement.
                    operation = 'delete' if n % 10 == 9 else 'update' if n % 3 == 2 else 'insert'
                    step(conn, config['engine'], operation)
                    print(json.dumps({'batch': n + 1, 'operation': operation, 'committedAt': dt.datetime.now(dt.timezone.utc).isoformat()}), flush=True)
                    until = time.monotonic() + args.interval
                    while time.monotonic() < until and not stop.exists(): time.sleep(min(.2, max(0, until-time.monotonic())))
    finally:
        conn.close()

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: print('Stopped; uncommitted transaction rolled back')
