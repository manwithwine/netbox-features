from rest_framework.routers import DefaultRouter
from .views import VPNGroupViewSet, VPNUserViewSet

router = DefaultRouter()
router.register(r'groups', VPNGroupViewSet)
router.register(r'users',  VPNUserViewSet)

urlpatterns = router.urls
