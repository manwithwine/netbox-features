from django.db import models
from netbox.models import ChangeLoggedModel
from dcim.models import Device
from django.utils.timezone import now

class ConfigBackup(ChangeLoggedModel):
    device = models.ForeignKey(
        to=Device,
        on_delete=models.CASCADE,
        related_name='config_backups'
    )
    config = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(auto_now_add=True)
    last_status = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    collection_mode = models.CharField(
        max_length=10,
        choices=[('MANUAL', 'Manual'), ('AUTO', 'Auto')],
        default='MANUAL'
    )
    auto_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created']
        verbose_name = 'Config Backup'
        verbose_name_plural = 'Config Backups'

    def get_absolute_url(self):
        return self.device.get_absolute_url()
