from netbox.plugins import PluginTemplateExtension
from dcim.models import Device

class DeviceConfigBackupExtension(PluginTemplateExtension):
    model = 'dcim.device'

    def buttons(self):
        device = self.context['object']
        return self.render(
            'netbox_config_backup/includes/device_button.html',
            extra_context={
                'device': device
            }
        )

template_extensions = [DeviceConfigBackupExtension]
