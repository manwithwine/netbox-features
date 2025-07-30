from rest_framework.viewsets import ModelViewSet
from netbox_config_backup.models import ConfigBackup
from netbox_config_backup.api.serializers import ConfigBackupSerializer
from netbox.api.viewsets import NetBoxModelViewSet  # IMPORTANT

class ConfigBackupViewSet(NetBoxModelViewSet):  # ✅ use NetBoxModelViewSet
    queryset = ConfigBackup.objects.all()
    serializer_class = ConfigBackupSerializer
