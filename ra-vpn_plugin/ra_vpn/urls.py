from django.urls import path
from . import views

urlpatterns = [
    # GROUP - All names now use 'vpngroup_' prefix
    path('groups/', views.VPNGroupListView.as_view(), name='vpngroup_list'),
    path('groups/add/', views.VPNGroupEditView.as_view(), name='vpngroup_add'),
    path('groups/import/', views.VPNGroupImportView.as_view(), name='vpngroup_import'),
    path('groups/<int:pk>/', views.VPNGroupView.as_view(), name='vpngroup'),
    path('groups/<int:pk>/edit/', views.VPNGroupEditView.as_view(), name='vpngroup_edit'),
    path('groups/<int:pk>/delete/', views.VPNGroupDeleteView.as_view(), name='vpngroup_delete'),
    path('groups/delete/', views.VPNGroupBulkDeleteView.as_view(), name='vpngroup_bulk_delete'),
    path('groups/edit/', views.VPNGroupBulkEditView.as_view(), name='vpngroup_bulk_edit'),

    # USER - All names now use 'vpnuser_' prefix
    path('users/', views.VPNUserListView.as_view(), name='vpnuser_list'),
    path('users/add/', views.VPNUserEditView.as_view(), name='vpnuser_add'),
    path('users/import/', views.VPNUserImportView.as_view(), name='vpnuser_import'),
    path('users/<int:pk>/', views.VPNUserView.as_view(), name='vpnuser'),
    path('users/<int:pk>/edit/', views.VPNUserEditView.as_view(), name='vpnuser_edit'),
    path('users/<int:pk>/delete/', views.VPNUserDeleteView.as_view(), name='vpnuser_delete'),
    path('users/delete/', views.VPNUserBulkDeleteView.as_view(), name='vpnuser_bulk_delete'),
    path('users/edit/', views.VPNUserBulkEditView.as_view(), name='vpnuser_bulk_edit'),
]
