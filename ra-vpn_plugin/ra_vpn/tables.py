import django_tables2 as tables
from django_tables2 import columns
from .models import VPNGroup, VPNUser
from netbox.tables import NetBoxTable, ToggleColumn, ActionsColumn

# Added custom DateColumn for consistent date formatting
class DateColumn(tables.Column):
    def render(self, value):
        if value:
            return value.strftime('%b. %d, %Y')
        return value

class VPNGroupTable(NetBoxTable):
    pk = ToggleColumn()
    tenant = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    owner = tables.Column()
    ttl = DateColumn(verbose_name="TTL")  # New field
    owneraudit = DateColumn(verbose_name="Owner Audit")  # New field
    adminaudit = DateColumn(verbose_name="Admin Audit")  # New field
    actions = ActionsColumn(
        actions=('edit', 'delete'),
    )
    
    class Meta(NetBoxTable.Meta):
        model = VPNGroup
        fields = ('name', 'tenant', 'owner', 'purpose', 'ttl', 'owneraudit', 'adminaudit', 'actions')
        default_columns = ('name', 'tenant', 'owner', 'purpose', 'ttl', 'owneraudit', 'adminaudit', 'actions')

class VPNUserTable(NetBoxTable):
    pk = ToggleColumn()
    username = tables.Column(linkify=True)
    group = tables.Column(linkify=True)
    status = tables.Column()
    # Changed to use our DateColumn for consistent formatting
    ttl = DateColumn(verbose_name="TTL")
    actions = ActionsColumn(
        actions=('edit', 'delete')
    )
    
    class Meta(NetBoxTable.Meta):
        model = VPNUser
        fields = ('username', 'group', 'status', 'fullname', 'email', 'company', 'ttl', 'actions')
        default_columns = ('username', 'group', 'status', 'fullname', 'email', 'company', 'ttl', 'actions')
