from django.urls import path
from . import views

app_name = 'netbox_config_backup'  # ✅ This is REQUIRED for namespacing

urlpatterns = [
    path('devices/<int:device_id>/backups/', views.DeviceConfigBackupView.as_view(), name='device_config_backups'),
    path('devices/<int:device_id>/collect/', views.collect_backup, name='collect_backup'),
    path('devices/<int:device_id>/enable/', views.enable_backup, name='enable_backup'),
    path('devices/<int:device_id>/disable/', views.disable_backup, name='disable_backup'),
    path('devices/<int:device_id>/delete/', views.delete_backups, name='delete_backups'),
    path('devices/<int:device_id>/config/<int:backup_id>/', views.view_config, name='view_config'),
    path('compare/', views.ConfigDiffView.as_view(), name='config_diff'),
]
