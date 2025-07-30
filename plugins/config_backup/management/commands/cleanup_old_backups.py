import os
from django.core.management.base import BaseCommand
from dcim.models import Device
from netbox_config_backup.models import ConfigBackup
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleanup old config backups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test without actually deleting anything'
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=3,
            help='Number of recent backups to keep per device'
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=15,
            help='Minimum number of backups before cleanup triggers'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        keep_count = options['keep']
        threshold = options['threshold']
        total_deleted = 0
        
        for device in Device.objects.all():
            backups = ConfigBackup.objects.filter(device=device).order_by('-created')
            backup_count = backups.count()
            
            if backup_count <= threshold:
                continue
                
            keep_ids = list(backups.values_list('id', flat=True)[:keep_count])  
            to_delete = backups.exclude(id__in=keep_ids)
            
            logger.info(f"Device {device}: {backup_count} backups found, keeping {keep_count}")
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {to_delete.count()} backups")
                continue
                
            # Actual deletion
            deleted_count, _ = to_delete.delete()
            total_deleted += deleted_count
            logger.info(f"Deleted {deleted_count} backups for {device}")

        logger.info(f"TOTAL DELETED: {total_deleted} backups")
        return f"Cleanup complete. Deleted {total_deleted} backups."
