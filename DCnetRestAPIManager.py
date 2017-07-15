from ryu.app.wsgi import ControllerBase, route
from webob import Response
import json
import pycurl
import StringIO

class   DCnetRestAPIManager (ControllerBase):

    def __init__(self, req, link, data, **config):
        super(DCnetRestAPIManager, self).__init__(req, link, data, **config)
        self.controller = data['controller']

    @route ('DCnet', '/DCnet/create-vm', methods=['PUT'], requirements=None)
    def create_vm (self, req, **kwargs):
        print 'REST :: create-vm'

        try:
            data = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        if 'server' not in data.keys():
            return Response(status=400)

        server = data['server']

        if 'ip' not in self.controller.servers[server].keys():
            return Response(status=400)

        uid = self.controller.create_vm(server)

        if uid is None:
            return Response(status=400)

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

        if code != 200:
            return Response(status=500)

        body = buff.getvalue()

        self.controller.vms[uid] = json.loads(body)
        print self.controller.vms[uid]

        body = json.dumps(self.controller.vms[uid])

        return Response(content_type='application/json', body=body)

    @route ('DCnet', '/DCnet/delete-vm', methods=['PUT'], requirements={})
    def delete_vm (self, req):

        try:
            data = req.json if req.body else None
        except ValueError:
            return Response(status=400)

        if 'uid' not in data.keys():
            return Response(status=400)

        uid = data['uid']

        if uid not in self.controller.vms.keys():
            return Response(status=400)

        server = self.controller.vms[uid]['server']

        self.controller.delete_vm(uid)

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

        if code != 200:
            return Response(status=500)

        return Response(content_type='application/json', body='{}')
