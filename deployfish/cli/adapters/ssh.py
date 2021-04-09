from .abstract import (
    GetSSHTargetMixin,
    ClickListObjectsCommandMixin,
    ClickObjectInfoCommandMixin,
    ClickTunnelObjectCommandMixin,
    ClickBaseModelAdapter
)

from deployfish.core.models import SSHTunnel


class ClickSSHTunnelAdapter(
    GetSSHTargetMixin,
    ClickListObjectsCommandMixin,
    ClickObjectInfoCommandMixin,
    ClickTunnelObjectCommandMixin,
    ClickBaseModelAdapter
):

    model = SSHTunnel
    list_result_columns = {
        'Name': 'name',
        'Service': 'service__name',
        'Cluster': 'cluster__name',
        'Local Port': 'local_port',
        'Host': 'host',
        'Host Port': 'host_port'
    }
