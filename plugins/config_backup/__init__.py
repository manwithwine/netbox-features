from netbox.plugins import PluginConfig
from .signals import update_device_backup_status

class NetBoxConfigBackupConfig(PluginConfig):
    name = 'netbox_config_backup'
    verbose_name = 'Config Backup'
    description = 'Configuration backup and diff tool'
    version = '1.0'
    author = 'Mansur Kasumov'
    base_url = 'config-backup'
    required_settings = []
    default_settings = {}
    
    api_urlpatterns = 'netbox_config_backup.api_urls'

    def ready(self):
        super().ready()
#        from .signals import update_device_backup_status

config = NetBoxConfigBackupConfig
