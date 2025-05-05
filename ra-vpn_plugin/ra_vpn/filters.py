import django_filters
from netbox.filtersets import NetBoxModelFilterSet
from tenancy.models import Tenant
from .models import VPNGroup, VPNUser
from django.db.models import Q
from utilities.filters import TreeNodeMultipleChoiceFilter, MultiValueCharFilter, MultiValueMACAddressFilter
from extras.filtersets import LocalConfigContextFilterSet
from extras.models import ConfigTemplate

class VPNGroupFilterSet(NetBoxModelFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label='Search',
    )

    tenant = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        to_field_name='slug'
    )

    class Meta:
        model = VPNGroup
        fields = ['tenant', 'name', 'acl', 'attribute', 'purpose', 'ttl', 'owneraudit', 'adminaudit']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |
            Q(acl__icontains=value) |
            Q(attribute__icontains=value) |
            Q(purpose__icontains=value) |  # New field
            Q(owner__icontains=value)
        )


class VPNUserFilterSet(NetBoxModelFilterSet):
    q = django_filters.CharFilter(
        method='search',
        label='Search',
    )

    group = django_filters.ModelMultipleChoiceFilter(
        field_name='group__name',
        queryset=VPNGroup.objects.all(),
        to_field_name='name'
    )

    class Meta:
        model = VPNUser
        fields = ['username', 'group', 'status', 'fullname', 'email', 'company', 'ttl']

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(username__icontains=value) |
	    Q(status__icontains=value) |
            Q(fullname__icontains=value) |
            Q(email__icontains=value) |
            Q(company__icontains=value)
        )
