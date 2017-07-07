from ryu.app.wsgi import ControllerBase, route
from webob import Response
import json
import DCnetController

class   DCnetRestAPIManager(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(DCnetRestAPIManager, self).__init__(req, link, data, **config)
        self.controller = data['controller']

    @route('DCnet', '/DCnet/create-vm/', methods=['PUT'], requirements={})
    def rest_create_vm(self, req):
        print 'REST API: create-vm'
        return Response(content_type='application/json', body='{}')
