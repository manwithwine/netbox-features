from netbox.api.viewsets import NetBoxModelViewSet
from ra_vpn.models import VPNGroup, VPNUser
from .serializers import VPNGroupSerializer, VPNUserSerializer

class VPNGroupViewSet(NetBoxModelViewSet):
    queryset = VPNGroup.objects.all()
    serializer_class = VPNGroupSerializer
    filterset_fields = ['name', 'tenant', 'owner', 'deputy', 'purpose', 'ttl', 'owneraudit', 'adminaudit']

class VPNUserViewSet(NetBoxModelViewSet):
    queryset = VPNUser.objects.all()
    serializer_class = VPNUserSerializer
    filterset_fields = ['username', 'group__name', 'status', 'ttl']
