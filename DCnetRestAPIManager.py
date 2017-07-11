from ryu.app.wsgi import ControllerBase, route
from webob import Response

class   DCnetRestAPIManager (ControllerBase):

    def __init__(self, req, link, data, **config):
        super(DCnetRestAPIManager, self).__init__(req, link, data, **config)
        self.controller = data['controller']

    @route ('DCnet', '/DCnet/create-vm', methods=['PUT'], requirements=None)
    def create_vm (self, req, **kwargs):
        print 'REST :: create-vm'
        print req
        return Response('{}')
