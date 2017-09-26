from ryu.app.wsgi import ControllerBase, route
from ryu.lib import hub
from webob import Response
import json
import pycurl
import StringIO
import socket

class   DCnetRestAPIManager (ControllerBase):

    def __init__(self, req, link, data, **config):
        super(DCnetRestAPIManager, self).__init__(req, link, data, **config)
        self.controller = data['controller']

    # Method to handle create-vm requests
    @route ('DCnet', '/DCnet/create-vm', methods=['PUT'], requirements=None)
    def create_vm (self, req, **kwargs):
        print 'REST :: create-vm'

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        # The request should contain name of server to host the VM
        if 'server' not in data.keys():
            return Response(status=400)

        server = data['server']

        # If we do not have enough information about the server, fail
        if 'ip' not in self.controller.servers[server].keys():
            return Response(status=400)

        # Create a record of the VM, add rules, etc.
        uid = self.controller.create_vm(server)

        # Return error if record of VM was not created
        if uid is None:
            return Response(status=400)

        # Generate a request to be sent to the server
        c = pycurl.Curl()
        c.setopt(c.URL, "http://{0}:8080/DCnetSrv/create-vm".format(self.controller.servers[server]['ip']))
        c.setopt(c.PUT, True)
        body = json.dumps({ "uid" : uid })
        size = len(body)
        c.setopt(c.READFUNCTION, StringIO.StringIO(body).read)
        c.setopt(c.INFILESIZE, size)
        buff = StringIO.StringIO()
        c.setopt(c.WRITEDATA, buff)
        c.perform()

        code = c.getinfo(c.RESPONSE_CODE)

        # If server returned error, fail
        if code != 200:
            return Response(status=500)

        body = buff.getvalue()

        # Update the VM record with data that server returned
        self.controller.vms[uid] = json.loads(body)
        print self.controller.vms[uid]

        body = json.dumps(self.controller.vms[uid])

        return Response(content_type='application/json', body=body)

    # Method to handle delete-vm requests
    @route ('DCnet', '/DCnet/delete-vm', methods=['PUT'], requirements={})
    def delete_vm (self, req):

        try:
            data = req.json if req.body else None
        except ValueError:
            return Response(status=400)

        # Request must contain UID od VM to delete
        if 'uid' not in data.keys():
            return Response(status=400)

        uid = data['uid']

        # Fail if we do not have a record for such a VM
        if uid not in self.controller.vms.keys():
            return Response(status=400)

        # Get the server which is hosting the VM
        server = self.controller.vms[uid]['server']

        # Remove rules associated with this VMs
        self.controller.delete_vm(uid)

        # Generate a request to be sent to the server
        c = pycurl.Curl()
        c.setopt(c.URL, "http://{0}:8080/DCnetSrv/delete-vm".format(self.controller.servers[server]['ip']))
        c.setopt(c.PUT, True)
        body = json.dumps({ "uid" : uid })
        size = len(body)
        c.setopt(c.READFUNCTION, StringIO.StringIO(body).read)
        c.setopt(c.INFILESIZE, size)
        buff = StringIO.StringIO()
        c.setopt(c.WRITEDATA, buff)
        c.perform()

        code = c.getinfo(c.RESPONSE_CODE)

        # If the server returns error, fail
        if code != 200:
            return Response(status=500)

        return Response(content_type='application/json', body='{}')

    # Method to handle migrate-vm requests
    @route ('DCnet', '/DCnet/migrate-vm', methods=['PUT'], requirements={})
    def migrate_vm (self, req):

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        if 'uid' not in data.keys() or 'dst' not in data.keys():
            return Response(status=400)

        # Request must contain UID of VM and destination server
        uid = data['uid']
        dst = data['dst']

        if uid not in self.controller.vms.keys():
            return Response(status=400)

        vm = self.controller.vms[uid]

        # Get the current server which is hosting the VM
        src = vm['server']

        # Spawn a green-thread to handle migration related connection
        hub.spawn(self.migrate_thread)
        hub.sleep(0)

        # Generate a request for the destination server
        c = pycurl.Curl()
        c.setopt(c.URL, "http://{0}:8080/DCnetSrv/create-vm".format(self.controller.servers[dst]['ip']))
        c.setopt(c.PUT, True)
        body = json.dumps({ "uid" : uid, "incoming" : 1})
        size = len(body)
        c.setopt(c.READFUNCTION, StringIO.StringIO(body).read)
        c.setopt(c.INFILESIZE, size)
        buff = StringIO.StringIO()
        c.setopt(c.WRITEDATA, buff)
        print 'migrate-vm :: sending message to dst first..'
        c.perform()

        code = c.getinfo(c.RESPONSE_CODE)
        print 'migrate-vm :: code', code
        if code != 200:
            return Response(status=500)

        data = json.loads(buff.getvalue())
        print 'migrate-vm :: data from dst', data

        # Get the incoming port on which destination server will accept migration
        incport = data['incport']

        # Generate a request for the current server
        c = pycurl.Curl()
        c.setopt(c.URL, "http://{0}:8080/DCnetSrv/migrate-vm".format(self.controller.servers[src]['ip']))
        c.setopt(c.PUT, True)
        body = json.dumps({ "uid" : uid, "dst" : self.controller.servers[dst]['uid'], "port" : incport})
        print 'data to be sent to src: ', body
        size = len(body)
        c.setopt(c.READFUNCTION, StringIO.StringIO(body).read)
        c.setopt(c.INFILESIZE, size)
        buff = StringIO.StringIO()
        c.setopt(c.WRITEDATA, buff)
        print 'migrate-vm :: sending msg to src now..'
        c.perform()

        code = c.getinfo(c.RESPONSE_CODE)
        print 'migrate-vm :: code', code
        if code != 200:
            return Response(status=500)

        self.controller.vms[uid] = data

	self.controller.create_tmp_vm(uid=uid, src=src, dst=dst)

        #self.controller.delete_vm(uid)
        #self.controller.create_vm(uid=uid, srvname=dst, switch=None)

    # Migration green-thread that handles connecting related to migration
    def migrate_thread (self, vm):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        s.bind(('',22000))

        s.listen(5)

        hub.sleep(0)

        (c, caddr) = s.accept()

        s.close()
