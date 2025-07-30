from rest_framework import serializers
from netbox_config_backup.models import ConfigBackup

class ConfigBackupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigBackup
        fields = '__all__'
