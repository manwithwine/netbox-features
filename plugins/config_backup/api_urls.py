from rest_framework.routers import DefaultRouter
from netbox_config_backup.api.views import ConfigBackupViewSet

router = DefaultRouter()
router.register(r'backups', ConfigBackupViewSet)

urlpatterns = router.urls
