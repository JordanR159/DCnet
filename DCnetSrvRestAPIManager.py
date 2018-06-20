from ryu.app.wsgi import ControllerBase, route
from ryu.lib import hub
from webob import Response
import subprocess
import json
import socket
import time
import os

class   DCnetSrvRestAPIManager (ControllerBase):

    def __init__ (self, req, link, data, **config):
        super(DCnetSrvRestAPIManager, self).__init__(req, link, data, **config)

        self.controller = data['controller']

    # Method to handle create-vm requests
    @route ('DCnetSrv', '/DCnetSrv/create-vm', methods=['PUT'], requirements={})
    def create_vm (self, req):

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        # UID must be present in the request
        if 'uid' not in data.keys():
            return Response(status=400)

        # Check if we need to create incoming connection for migration
        incoming = 0
        if 'incoming' in data.keys():
            incoming = data['incoming']
        uid = data['uid']

        # If we already have the VM, fail
        if uid in self.controller.vms.keys():
            return Response(status=400)

        # Generate the tap device name
        tap = 'tapvm-{0}'.format(uid)

        # Generate the MAC address of the VM
        mac = '98:98:98:00:00:{0:02x}'.format(uid)

        # Generate the port on the local OVS
        port = self.controller.next_ofport
        self.controller.next_ofport = self.controller.next_ofport + 1

        # Create the tap device
        proc = subprocess.Popen(['tunctl', '-u', 'root', '-t', tap])
        proc.wait()

        # Add the tap device to the local OVS
        proc = subprocess.Popen(['ovs-vsctl',
                                 'add-port', self.controller.srvname, tap,
                                 '--', 'set', 'Interface', tap,
                                 'ofport_request={0}'.format(port)])
        proc.wait()

        # Add rules related to this VM to the local OVS
        if incoming == 0:
            self.controller.create_vm(mac, port)

        # Generate the QMP port for QEMU Machine Protocol
        qmpport = self.controller.qmpport
        self.controller.qmpport = self.controller.qmpport + 1

        image = '/home/rajas/nfs_files/tiny-core-linux-{0}.img'.format(uid)

        if incoming == 0:
            # Create a copy of the image for this new VM
            proc = subprocess.Popen(['cp', './tiny-core-linux.img', image])
            proc.wait()

        # Instantiate the VM
        if incoming == 0:
            proc = subprocess.Popen(['qemu-system-x86_64', '-enable-kvm',
                                     '-hda', image,
                                     '-device', 'virtio-net,netdev=net0,mac={0}'.format(mac),
                                     '-netdev', 'tap,id=net0,ifname={0}'.format(tap),
                                     '-serial', 'pty',
                                     '-display', 'none',
                                     '-qmp', 'tcp:localhost:{0},server,nowait'.format(qmpport)])
        else:
            incport = self.controller.incport
            self.controller.incport = self.controller.incport + 1
            proc = subprocess.Popen(['qemu-system-x86_64', '-enable-kvm',
                                     '-hda', image,
                                     '-device', 'virtio-net,netdev=net0,mac={0}'.format(mac),
                                     '-netdev', 'tap,id=net0,ifname={0}'.format(tap),
                                     '-serial', 'pty',
                                     '-display', 'none',
                                     '-qmp', 'tcp:localhost:{0},server,nowait'.format(qmpport),
                                     '-incoming', 'tcp:[dc98::9898:9800:{0}]:{1},server,nowait'.format(self.controller.uid, incport)])

        time.sleep(1)
        proc.poll()
        if(proc.returncode == 1):
            return Response(status=400)

        print 'proc returncode: ', proc.returncode
        time.sleep(2)

        # Establish a connection with the QMP server
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

        # Get the name of the serial device being used on the host
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

        # Generate a record of the VM
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

        # Add the VM record in the list of VMs hosted locally
        self.controller.vms[uid] = vm

        return Response(content_type='application/json', body=json.dumps(vm))

    # Method to handle delete-vm requests
    @route ('DCnetSrv', '/DCnetSrv/delete-vm', methods=['PUT'], requirements={})
    def delete_vm (self, req):

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        # UID must be present in the request
        if 'uid' not in data.keys():
            return Response(status=400)

        uid = data['uid']

        # Fail if we do not have a VM with this UID
        if uid not in self.controller.vms.keys():
            return Response(status=400)

        delete_rule = 0
        if 'delete_rule' in data.keys():
            delete_rule = data['delete_rule']

        # If we only need to delete rule, delete it and return
        if delete_rule == 1:
            self.controller.delete_vm(self.controller.vms[uid]['mac'], self.controller.vms[uid]['port'])
            return Response(status=200)

        # Establish a connection with the QMP server associated with the VM
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', self.controller.vms[uid]['qmpport']))
        except socket.error:
            return Response(status=400)

        # Send the command to quit the VM
        s.send('{"execute" : "qmp_capabilities"}')
        s.send('{"execute" : "quit"}')
        s.close()

        # Remote the tap interface from local OVS
        proc = subprocess.Popen(['ovs-vsctl', 'del-port',
                                 self.controller.srvname, self.controller.vms[uid]['tap']])
        proc.wait()

        # Delete the tap interface
        proc = subprocess.Popen(['ip', 'link', 'del', '{0}'.format(self.controller.vms[uid]['tap'])])
        proc.wait()

        # Remove the rules associated with this VM from the local OVS
        self.controller.delete_vm(self.controller.vms[uid]['mac'], self.controller.vms[uid]['port'])

        os.waitpid(self.controller.vms[uid]['pid'], 0)

        # Delete the record of this VM
        del(self.controller.vms[uid])

        # Delete the copy of the linux image
        proc = subprocess.Popen(['rm', '-f', '/home/rajas/nfs_files/tiny-core-linux-{0}.img'.format(uid)])
        proc.wait()

        return Response(content_type='application/json',body='{}')

    # Method to handle migrate-vm requests
    @route ('DCnetSrv', '/DCnetSrv/migrate-vm', methods=['PUT'], requirements={})
    def migrate_vm (self, req):

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        if 'uid' not in data.keys():
            return Response(status=400)

        incoming = 0
        if 'incoming' in data.keys():
            incoming = data['incoming']

        # UID of the VM, destination server and destination port must be present in the request
        if incoming == 0:
            if 'dst' not in data.keys() or 'port' not in data.keys():
                return Response(status=400)

        uid = data['uid']

        if incoming == 1:
            vm = self.controller.vms[uid]
            self.controller.create_vm(vm['mac'], vm['port'])
            return Response(status=200)

        dst = data['dst']
        port = data['port']

        if uid not in self.controller.vms.keys():
            return Response(status=400)

        # Establish a connection with the QMP server associated with the VM
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

        # Send a command to migrate the VM
        s.send('{"execute" : "migrate", "arguments" : { "uri" : "tcp:[dc98::9898:9800:%s]:%s" }}' % (dst, port))
        f.readline()

        s.close()

        hub.spawn(self.migrate_thread, vm)

        vm['migration'] = 'progress'

        return
        #line = f.readline()
        #print 'migrate response: ', line

    # Green-thread handling migration of a VM
    def migrate_thread (self, vm):

        # Establish a connection with the QMP server associated with the VM
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect(('127.0.0.1',vm['qmpport']))
        except socket.error:
            return

        f = s.makefile()
        f.readline()

        s.send('{"execute":"qmp_capabilities"}')
        f.readline()

        # Keep checking the status of migration
        while(1):
            s.send('{"execute" : "query-migrate"}')
            line = f.readline()
            resp = json.loads(line)
            if 'return' not in resp.keys():
                continue
            if resp['return']['status'] == 'failed' or resp['return']['status'] == 'completed':
                break

        if resp['return']['status'] == 'completed':

            print 'migrate_thread :: migration stats: ', resp

            # Quit the Qemu instance
            s.send('{"execute" : "quit"}')

            # Remove the tap interface from local OVS
            proc = subprocess.Popen(['ovs-vsctl', 'del-port', self.controller.srvname, vm['tap']])
            proc.wait()

            # Delete the tap interface
            proc = subprocess.Popen(['ip', 'link', 'del', vm['tap']])
            proc.wait()

            # Remove the rules associated with this VM from local OVS
            self.controller.delete_vm(vm['mac'], vm['port'])

            vm['migration'] = 'complete'

            os.waitpid(vm['pid'], 0)

            del(self.controller.vms[vm['uid']])
        else:
            vm['migration'] = 'failed'

        s.close()
