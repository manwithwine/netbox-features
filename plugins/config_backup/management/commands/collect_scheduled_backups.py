from django.core.management.base import BaseCommand
from netbox_config_backup.tasks import collect_scheduled_backups
from dotenv import load_dotenv
import logging

load_dotenv('/opt/netbox/netbox/netbox_config_backup.env')

logger = logging.getLogger("netbox_config_backup")

class Command(BaseCommand):
    help = "Collect scheduled config backups for all devices"

    def handle(self, *args, **options):
        logger.info("🚀 Scheduled backup job started (cron/management command)")
        collect_scheduled_backups()
        logger.info("✅ Scheduled backup job finished")
