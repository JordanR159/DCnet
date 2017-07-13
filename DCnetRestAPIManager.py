from ryu.app.wsgi import ControllerBase, route
from webob import Response
import json

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

        uid = self.controller.create_vm(server)

        if uid is None:
            return Response(status=400)

        body = json.dumps({ "code" : 0, "uid" : uid })

        return Response(content_type='application/json', body=body)
