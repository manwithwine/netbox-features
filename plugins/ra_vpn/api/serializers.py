from netbox.api.serializers import NetBoxModelSerializer
from ra_vpn.models import VPNGroup, VPNUser

class VPNGroupSerializer(NetBoxModelSerializer):
    class Meta:
        model = VPNGroup
        fields = (
            'id', 'url', 'name', 'acl', 'attribute', 'owner', 'deputy', 'purpose',
            'ttl', 'owneraudit', 'adminaudit', 'tenant', 'created', 'last_updated',
        )

class VPNUserSerializer(NetBoxModelSerializer):
    class Meta:
        model = VPNUser
        fields = (
            'id', 'url', 'username', 'group', 'fullname', 'password',
            'email', 'company', 'ttl', 'status', 'created', 'last_updated',
        )
