from django import forms
from tenancy.models import Tenant
from netbox.forms import NetBoxModelForm, NetBoxModelImportForm, NetBoxModelBulkEditForm
from .models import VPNGroup, VPNUser
from django.forms import DateInput
from datetime import datetime


class CustomDateField(forms.DateField):
    input_formats = ['%d.%m.%Y', '%Y-%m-%d', '%b. %d, %Y']  # Added multiple input formats
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', forms.TextInput(attrs={'placeholder': 'dd.mm.yyyy'}))
        super().__init__(*args, **kwargs)
    
    def prepare_value(self, value):
        if isinstance(value, str):
            return value
        if value:
            # Convert date to DD.MM.YYYY format for display in forms
            return value.strftime('%d.%m.%Y')
        return value

    def to_python(self, value):
        try:
            # First try to parse as DD.MM.YYYY
            return datetime.strptime(value, '%d.%m.%Y').date()
        except (ValueError, TypeError):
            try:
                # Then try other formats
                return super().to_python(value)
            except (ValueError, TypeError):
                return None

class VPNGroupForm(NetBoxModelForm):
    tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False
    )
    ttl = CustomDateField(  # New field
        required=False,
        label="TTL",
        help_text="Group lifetime in DD.MM.YYYY format",
    )
    owneraudit = CustomDateField(  # New field
        required=False,
        label="Owner Audit",
        help_text="Owner audit date in DD.MM.YYYY format",
    )
    adminaudit = CustomDateField(  # New field
        required=False,
        label="Admin Audit",
        help_text="Admin audit date in DD.MM.YYYY format",
    )

    class Meta:
        model = VPNGroup
        fields = ['tenant', 'name', 'acl', 'attribute', 'owner', 'purpose', 'ttl', 'owneraudit', 'adminaudit']
        widgets = {
            'acl': forms.Textarea(attrs={'rows': 5}),
            'attribute': forms.Textarea(attrs={'rows': 5}),
            'purpose': forms.Textarea(attrs={'rows': 5}),  # New field
        }
        labels = {
            'ttl': 'TTL',
            'owneraudit': 'Owner Audit',
            'adminaudit': 'Admin Audit',
        }

class VPNUserForm(NetBoxModelForm):
    ttl = CustomDateField(
        required=False,
        label="TTL",
        help_text="Account lifetime in DD.MM.YYYY format",
    )

    class Meta:
        model = VPNUser
        fields = ['username', 'group', 'status', 'fullname', 'password', 'email', 'company', 'ttl']
        widgets = {
            'password': forms.PasswordInput(render_value=True),
        }
        labels = {
            'ttl': 'TTL',
            'fullname': 'Full Name',
        }
        help_texts = {
            'ttl': 'Account lifetime in DD.MM.YYYY format',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.password:
            self.fields['password'].widget.attrs['placeholder'] = '(existing password)'

    def save(self, commit=True):
        user = super().save(commit=False)
        if 'password' in self.changed_data:
            user.password = self.cleaned_data['password']
        if commit:
            user.save()
            self.save_m2m()
        return user

class VPNGroupBulkEditForm(NetBoxModelBulkEditForm):
    model = VPNGroup
    
    tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False
    )
    acl = forms.CharField(required=False, widget=forms.Textarea)
    attribute = forms.CharField(required=False)
    owner = forms.CharField(required=False)
    purpose = forms.CharField(required=False, widget=forms.Textarea)  # New field
    ttl = CustomDateField(  # New field
        required=False,
        label="TTL",
        help_text="Group lifetime in DD.MM.YYYY format"
    )
    owneraudit = CustomDateField(  # New field
        required=False,
        label="Owner Audit",
        help_text="Owner audit date in DD.MM.YYYY format"
    )
    adminaudit = CustomDateField(  # New field
        required=False,
        label="Admin Audit",
        help_text="Admin audit date in DD.MM.YYYY format"
    )

    class Meta:
        model = VPNGroup
        fields = ('tenant', 'acl', 'attribute', 'owner', 'purpose', 'ttl', 'owneraudit', 'adminaudit')
        labels = {
            'ttl': 'TTL',
            'owneraudit': 'Owner Audit',
            'adminaudit': 'Admin Audit',
        }

class VPNUserBulkEditForm(NetBoxModelBulkEditForm):
    model = VPNUser
    
    group = forms.ModelChoiceField(
        queryset=VPNGroup.objects.all(),
        required=False
    )
    fullname = forms.CharField(label="Full Name", required=False)
    status = forms.ChoiceField(choices=VPNUser.STATUS_CHOICES, required=False)
    email = forms.EmailField(required=False)
    company = forms.CharField(required=False)
    ttl = CustomDateField(  # Changed to use our custom field
        required=False,
        label="TTL",
        help_text="Account lifetime in DD.MM.YYYY format"
    )

    class Meta:
        model = VPNUser
        fields = ('group', 'fullname', 'status', 'email', 'company', 'ttl')
        labels = {
            'ttl': 'TTL',
        }
        help_texts = {
            'ttl': 'Account lifetime in DD.MM.YYYY format',
        }

class VPNUserImportForm(NetBoxModelImportForm):
    group = forms.ModelChoiceField(
        queryset=VPNGroup.objects.all(),
        to_field_name='name',
        help_text="Group name",
        error_messages={
            'invalid_choice': "Group with this name does not exist."
        }
    )

    ttl = CustomDateField(  # Changed to use our custom field
        required=False,
        label="TTL",
        help_text="Account lifetime in DD.MM.YYYY format"
    )

    class Meta:
        model = VPNUser
        fields = ('username', 'group', 'fullname', 'status', 'password', 'email', 'company', 'ttl')

# forms.py - update VPNGroupImportForm
class VPNGroupImportForm(NetBoxModelImportForm):
    tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name='name',
        help_text="Tenant name"
    )
    ttl = CustomDateField(  # New field
        required=False,
        label="TTL",
        help_text="Group lifetime in DD.MM.YYYY format"
    )
    owneraudit = CustomDateField(  # New field
        required=False,
        label="Owner Audit",
        help_text="Owner audit date in DD.MM.YYYY format"
    )
    adminaudit = CustomDateField(  # New field
        required=False,
        label="Admin Audit",
        help_text="Admin audit date in DD.MM.YYYY format"
    )

    class Meta:
        model = VPNGroup
        fields = ('name', 'tenant', 'acl', 'attribute', 'owner', 'purpose', 'ttl', 'owneraudit', 'adminaudit')
