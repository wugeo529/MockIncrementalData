"""Private child-process entry. Profiles arrive on stdin, never in arguments or stdout."""
import json
import os
import sys
import threading

from desktop_service import DesktopManager
from dashboard import make_server


def main():
    manager = None
    server = None
    try:
        initial = json.loads(sys.stdin.readline(65537))
        if set(initial) != {'profiles'}:
            raise ValueError('Invalid startup request')
        manager = DesktopManager(initial['profiles'])
        server = make_server(manager, 0, desktop=True)
        def watch_parent():
            for _ in sys.stdin:
                pass
            server.shutdown()
        threading.Thread(target=watch_parent, daemon=True).start()
        print(json.dumps(dict(event='ready', url='http://127.0.0.1:' + str(server.server_port), token=server.token)), flush=True)
        server.serve_forever(poll_interval=.2)
    except Exception:
        print('模拟引擎无法启动，请查看应用版本与运行目录是否完整', file=sys.stderr, flush=True)
        return 1
    finally:
        if server:
            server.server_close()
        if manager:
            manager.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
