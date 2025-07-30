from netbox.views import generic
from netbox.views.generic import BulkImportView
from .models import VPNGroup, VPNUser
from .tables import VPNGroupTable, VPNUserTable
from .forms import VPNGroupForm, VPNUserForm
from .forms import VPNGroupBulkEditForm, VPNUserBulkEditForm, VPNUserImportForm, VPNGroupImportForm
from django.urls import reverse
from . import filters 


################ GROUP #################################
class VPNGroupListView(generic.ObjectListView):
    queryset = VPNGroup.objects.all()
    table = VPNGroupTable
    filterset = filters.VPNGroupFilterSet
    template_name = 'ra_vpn/group_list.html'

    def get_extra_context(self, request):
        return {
            "import_url": "plugins:ra_vpn:vpngroup_import"
        }

class VPNGroupView(generic.ObjectView):
    queryset = VPNGroup.objects.all()
    template_name = 'ra_vpn/group.html'

    def get_extra_context(self, request, instance):
        return {
            'users': instance.users.all()
        }

class VPNGroupDeleteView(generic.ObjectDeleteView):
    queryset = VPNGroup.objects.all()
    template_name = 'ra_vpn/group_delete.html'

class VPNGroupEditView(generic.ObjectEditView):
    queryset = VPNGroup.objects.all()
    model = VPNGroup
    form = VPNGroupForm
    template_name = 'ra_vpn/group_edit.html'

    def get_return_url(self, request, obj):
        return reverse('plugins:ra_vpn:vpngroup_list')

class VPNGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = VPNGroup.objects.all()
    table = VPNGroupTable
    filterset = filters.VPNGroupFilterSet

    def get_return_url(self, request):
        return reverse('plugins:ra_vpn:vpngroup_list')

class VPNGroupBulkEditView(generic.BulkEditView):
    queryset = VPNGroup.objects.all()
    filterset = filters.VPNGroupFilterSet
    table = VPNGroupTable
    form = VPNGroupBulkEditForm

    def get_return_url(self, request):
        return reverse('plugins:ra_vpn:vpngroup_list')

######################### USER ################################
class VPNUserListView(generic.ObjectListView):
    queryset = VPNUser.objects.all()
    table = VPNUserTable
    filterset = filters.VPNUserFilterSet
    template_name = 'ra_vpn/user_list.html'

    def get_extra_context(self, request):
        return {
            "import_url": "plugins:ra_vpn:vpnuser_import"
        }

class VPNUserView(generic.ObjectView):
    queryset = VPNUser.objects.all()
    template_name = 'ra_vpn/user.html'

class VPNUserEditView(generic.ObjectEditView):
    queryset = VPNUser.objects.all()
    model = VPNUser
    form = VPNUserForm
    template_name = 'ra_vpn/user_edit.html'

    def get_return_url(self, request, obj):
        return reverse('plugins:ra_vpn:vpnuser_list')

class VPNUserDeleteView(generic.ObjectDeleteView):
    queryset = VPNUser.objects.all()

class VPNUserBulkDeleteView(generic.BulkDeleteView):
    queryset = VPNUser.objects.all()
    table = VPNUserTable
    filterset = filters.VPNUserFilterSet

    def get_return_url(self, request):
        return reverse('plugins:ra_vpn:vpnuser_list')

class VPNUserBulkEditView(generic.BulkEditView):
    queryset = VPNUser.objects.all()
    filterset = filters.VPNUserFilterSet
    table = VPNUserTable
    form = VPNUserBulkEditForm

    def get_return_url(self, request):
        return reverse('plugins:ra_vpn:vpnuser_list')

##########  IMPORT  ###################################
class VPNGroupImportView(BulkImportView):
    queryset = VPNGroup.objects.all()
    model_form = VPNGroupImportForm
    default_return_url = 'plugins:ra_vpn:vpngroup_list'

class VPNUserImportView(BulkImportView):
    queryset = VPNUser.objects.all()
    model_form = VPNUserImportForm
    default_return_url = 'plugins:ra_vpn:vpnuser_list'
