from datetime import datetime

from django_rpc.models import RpcModel


class ClientModel(RpcModel):
    class Rpc:
        app_label = 'rpc_server'
        name = 'ServerModel'
        db = 'rpc'
        fields = ['char_field', 'dt_field']


print(list(ClientModel.objects.all()))

c = ClientModel.objects.create(dt_field=datetime.now())