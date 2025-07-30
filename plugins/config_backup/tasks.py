from dcim.models import Device
from .models import ConfigBackup
from .utilities.backup_utils import backup_device_config
from django.utils.timezone import now
import os
import logging

logger = logging.getLogger("netbox_config_backup")

def collect_scheduled_backups():
    for device in Device.objects.filter(status='active'):
        ip = device.primary_ip or device.oob_ip
        if not ip:
            continue  # Don't log devices with no IP (per your request)
        latest = ConfigBackup.objects.filter(device=device).order_by('-created').first()
        # Only run for devices where latest status is "Backup Enabled" or "Collected"
        if not latest or latest.status not in ['Backup Enabled', 'Collected']:
            continue  # Skip
        username = os.getenv("DEVICE_BACKUP_USER")
        password = os.getenv("DEVICE_BACKUP_PASSWORD")
        config, status = backup_device_config(device, username, password)
        last_backup = latest
        if not last_backup or (config and config != last_backup.config):
            ConfigBackup.objects.create(
                device=device,
                config=config or '',
                last_status=status,
                status='Backup Enabled' if config else f"Failed: {status}",
                last_checked=now(),
                collection_mode='AUTO'
            )
            logger.info(f"✅ {device.name}: Backup saved (AUTO)")
        elif status != "Success":
            logger.error(f"❌ {device.name}: Backup error: {status}")
        # No log if config is the same and success
