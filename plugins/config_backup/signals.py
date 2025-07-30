from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

@receiver(post_save)
@receiver(post_delete)
def update_device_backup_status(sender, **kwargs):
    # Only handle ConfigBackup model
    if sender.__name__ != 'ConfigBackup':
        return
        
    try:
        from dcim.models import Device
        from .models import ConfigBackup
        
        instance = kwargs.get('instance')
        if not instance:
            return
            
        device = instance.device
        latest_backup = ConfigBackup.objects.filter(device=device).order_by('-created').first()
        
        # Default status changed to "Disabled" instead of "No Backups"
        status = "Disabled"
        if latest_backup:
            if latest_backup.status == "Backup Enabled":
                status = "Auto Enabled"
            elif latest_backup.status == "Backup Disabled":
                status = "Disabled"  # Explicitly keep as Disabled
            elif latest_backup.status == "Collected":
                status = "Manual"
        
        if device.custom_field_data.get('backup_status') != status:
            device.custom_field_data['backup_status'] = status
            device.save()
            logger.debug(f"Updated backup_status for device {device} to {status}")
            
    except Exception as e:
        logger.error(f"Error updating backup status: {str(e)}")
