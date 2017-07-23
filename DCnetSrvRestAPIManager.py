from ryu.app.wsgi import ControllerBase, route
from webob import Response
import subprocess
import json
import socket
import time

class   DCnetSrvRestAPIManager (ControllerBase):

    def __init__ (self, req, link, data, **config):
        super(DCnetSrvRestAPIManager, self).__init__(req, link, data, **config)

        self.controller = data['controller']

    @route ('DCnetSrv', '/DCnetSrv/create-vm', methods=['PUT'], requirements={})
    def create_vm (self, req):

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        if 'uid' not in data.keys():
            return Response(status=400)

        incoming = 0
        if 'incoming' in data.keys():
            incoming = data['incoming']
        uid = data['uid']

        if uid in self.controller.vms.keys():
            return Response(status=400)

        tap = 'tapvm-{0}'.format(uid)
        mac = '98:98:98:00:00:{0:02x}'.format(uid)
        port = self.controller.next_ofport
        self.controller.next_ofport = self.controller.next_ofport + 1

        proc = subprocess.Popen(['tunctl', '-u', 'root', '-t', tap])
        proc.wait()

        proc = subprocess.Popen(['ovs-vsctl',
                                 'add-port', self.controller.srvname, tap,
                                 '--', 'set', 'Interface', tap,
                                 'ofport_request={0}'.format(port)])
        proc.wait()

        self.controller.create_vm(mac, port)

        qmpport = self.controller.qmpport
        self.controller.qmpport = self.controller.qmpport + 1

        if incoming == 0:
            proc = subprocess.Popen(['qemu-system-x86_64', '-enable-kvm',
                                     '-hda', './tiny-core-linux.img',
                                     '-device', 'virtio-net,netdev=net0,mac={0}'.format(mac),
                                     '-netdev', 'tap,id=net0,ifname={0}'.format(tap),
                                     '-serial', 'pty',
                                     '-qmp', 'tcp:localhost:{0},server,nowait'.format(qmpport)])
        else:
            incport = self.controller.incport
            self.controller.incport = self.controller.incport + 1
            proc = subprocess.Popen(['qemu-system-x86_64', '-enable-kvm',
                                     '-hda', './tiny-core-linux.img',
                                     '-device', 'virtio-net,netdev=net0,mac={0}'.format(mac),
                                     '-netdev', 'tap,id=net0,ifname={0}'.format(tap),
                                     '-serial', 'pty',
                                     '-qmp', 'tcp:localhost:{0},server,nowait'.format(qmpport),
                                     '-incoming', 'tcp:[dc98::9898:9800:{0}]:{1},server,nowait'.format(self.controller.uid, incport)])

        time.sleep(1)
        proc.poll()
        if(proc.returncode == 1):
            return Response(status=400)

        print 'proc returncode: ', proc.returncode
        time.sleep(2)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                s.connect(('127.0.0.1', qmpport))
            except socket.error:
                print 'soket Exception!'
                time.sleep(1)
                continue
            break

        f = s.makefile()
        line = f.readline()

        s.send('{"execute":"qmp_capabilities"}')
        line = f.readline()

        s.send('{"execute":"query-chardev"}')
        line = f.readline()
        data = json.loads(line)
        print data

        serial = None
        for dev in data['return']:
            if dev['label'].startswith('serial'):
                serial = dev['filename']
                break
        s.close()

        vm = { "uid" : uid,
               "server" : self.controller.srvname,
               "mac" : mac,
               "tap" : tap,
               "port" : port,
               "qmpport" : qmpport,
               "pid" : proc.pid }
        if serial != None:
            vm['serial'] = serial
        if incoming != 0:
            vm['incport'] = incport
        self.controller.vms[uid] = vm

        return Response(content_type='application/json', body=json.dumps(vm))

    @route ('DCnetSrv', '/DCnetSrv/delete-vm', methods=['PUT'], requirements={})
    def delete_vm (self, req):

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        if 'uid' not in data.keys():
            return Response(status=400)

        uid = data['uid']

        if uid not in self.controller.vms.keys():
            return Response(status=400)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', self.controller.vms[uid]['qmpport']))
        except socket.error:
            return Response(status=400)

        s.send('{"execute" : "qmp_capabilities"}')
        s.send('{"execute" : "quit"}')
        s.close()

        proc = subprocess.Popen(['ovs-vsctl', 'del-port',
                                 self.controller.srvname, self.controller.vms[uid]['tap']])
        proc.wait()

        proc = subprocess.Popen(['ip', 'link', 'del', '{0}'.format(self.controller.vms[uid]['tap'])])
        proc.wait()

        self.controller.delete_vm(self.controller.vms[uid]['mac'], self.controller.vms[uid]['port'])

        del(self.controller.vms[uid])

        return Response(content_type='application/json',body='{}')

    @route ('DCnetSrv', '/DCnetSrv/migrate-vm', methods=['PUT'], requirements={})
    def migrate_vm (self, req):

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        if 'uid' not in data.keys() or 'dst' not in data.keys() or 'port' not in data.keys():
            return Response(status=400)

        uid = data['uid']
        dst = data['dst']
        port = data['port']

        if uid not in self.controller.vms.keys():
            return Response(status=400)

        vm = self.controller.vms[uid]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', vm['qmpport']))
        except socket.error:
            return Response(status=400)

        f = s.makefile()
        f.readline()

        s.send('{"execute" : "qmp_capabilities" }')
        f.readline()

        s.send('{"execute" : "migrate", "arguments" : { "uri" : "tcp:[dc98::9898:9800:%s]:%s" }}' % (dst, port))
        f.readline()

        line = f.readline()
        print 'migrate response: ', line

        while(1):
            s.send('{"execute" : "query-migrate"}')
            line = f.readline()
            resp = json.loads(line)
            if resp['return']['status'] == 'failed' or resp['return']['status'] == 'completed':
                break

        if resp['return']['status'] == 'completed':

            s.send('{"execute" : "quit"}')

            proc = subprocess.Popen(['ovs-vsctl', 'del-port', self.controller.srvname, vm['tap']])
            proc.wait()

            proc = subprocess.Popen(['ip', 'link', 'del', vm['tap']])
            proc.wait()

            self.controller.delete_vm(vm['mac'], vm['port'])

            del(self.controller.vms[uid])
        else:
            return Response(status=500)

        s.close()

        return Response(content_type='application/json', body='{}')
