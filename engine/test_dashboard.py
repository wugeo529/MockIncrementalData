import importlib.util
import json
import pathlib
import threading
import time
import unittest
import urllib.request
import urllib.error
from contextlib import contextmanager

ROOT=pathlib.Path(__file__).resolve().parent

class DashboardTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'dashboard.py').exists(),'local simulator dashboard is required')
        spec=importlib.util.spec_from_file_location('dashboard',ROOT/'dashboard.py')
        self.d=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.d)
        self.writes=[]
        outer=self
        class Source:
            @staticmethod
            def connect(config): return type('Connection',(),{'close':lambda self:None})()
            @staticmethod
            @contextmanager
            def ownership_lock(conn,engine): yield
            @staticmethod
            def verify_schema(conn,engine): pass
            @staticmethod
            def step(conn,engine,action): outer.writes.append(action)
        self.manager=self.d.Manager({'mysql':{'engine':'mysql','host':'127.0.0.1','port':13429,'database':'signal_sim_test'}},source=Source)

    def test_manual_and_source_whitelist(self):
        self.manager.manual('mysql','insert')
        self.assertEqual(self.writes,['insert'])
        with self.assertRaises(ValueError): self.manager.manual('unknown','insert')
        with self.assertRaises(ValueError): self.manager.manual('mysql','DROP TABLE')

    def test_start_is_bounded_and_manual_is_excluded_until_stop(self):
        self.manager.start('mysql',.2,50)
        with self.assertRaises(RuntimeError):self.manager.manual('mysql','update')
        with self.assertRaises(RuntimeError):self.manager.start('mysql',.2,50)
        self.manager.stop('mysql')
        self.manager.wait('mysql',2)
        self.assertFalse(self.manager.runtime('mysql')['running'])
        self.assertGreaterEqual(len(self.writes),1)
        self.manager.manual('mysql','update')
        self.assertEqual(self.writes[-1],'update')

    def test_bad_frequency_rejected_without_writing(self):
        for interval,ticks in [(0,1),(float('nan'),1),(.2,0),(.2,1000001),(.2,1.5)]:
            with self.assertRaises(ValueError):self.manager.start('mysql',interval,ticks)
        self.assertEqual(self.writes,[])

    def test_http_commands_require_same_origin_nonce_and_known_action(self):
        server=self.d.make_server(self.manager,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        def post(origin,token,action='insert'):
            request=urllib.request.Request(base+'/api/action',method='POST',data=json.dumps({'profile':'mysql','action':action}).encode(),headers={'Content-Type':'application/json','Origin':origin,'X-Simulator-Token':token})
            return urllib.request.urlopen(request)
        try:
            with self.assertRaises(urllib.error.HTTPError) as result:post('http://foreign.example',server.token)
            self.assertEqual(result.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError):post(base,'wrong-token')
            with post(base,server.token) as response:self.assertEqual(response.status,200)
            with self.assertRaises(urllib.error.HTTPError):post(base,server.token,'arbitrary-sql')
            self.assertEqual(self.writes,['insert'])
        finally:server.shutdown();server.server_close();self.manager.close()

if __name__=='__main__':unittest.main()
