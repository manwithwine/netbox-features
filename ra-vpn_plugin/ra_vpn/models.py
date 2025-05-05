from django.db import models
from django.contrib.auth.hashers import make_password
from netbox.models import NetBoxModel
from tenancy.models import Tenant

class VPNGroup(NetBoxModel):
    name = models.CharField(max_length=100, unique=True)
    acl = models.TextField("ACL", blank=True)
    attribute = models.CharField(max_length=350, blank=True)
    owner = models.CharField(max_length=100, blank=True)
    purpose = models.CharField(max_length=350, blank=True)
    tenant = models.ForeignKey(
        to=Tenant,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='vpn_groups'
    )
    ttl = models.DateField(  # New field
        "TTL",
        blank=True,
        null=True,
        help_text="Group lifetime in DD.MM.YYYY format"
    )
    owneraudit = models.DateField(  # New field
        "Owner Audit",
        blank=True,
        null=True,
        help_text="Owner audit date in DD.MM.YYYY format"
    )
    adminaudit = models.DateField(  # New field
        "Admin Audit",
        blank=True,
        null=True,
        help_text="Admin audit date in DD.MM.YYYY format"
    )

    class Meta:
        ordering = ['tenant__name', 'name']
        verbose_name = 'RA-VPN Group'
        verbose_name_plural = 'RA-VPN Groups'
        
    @property
    def formatted_ttl(self):
        if self.ttl:
            return self.ttl.strftime('%b. %d, %Y')
        return None

    @property
    def formatted_owneraudit(self):
        if self.owneraudit:
            return self.owneraudit.strftime('%b. %d, %Y')
        return None

    @property
    def formatted_adminaudit(self):
        if self.adminaudit:
            return self.adminaudit.strftime('%b. %d, %Y')
        return None

    def __str__(self):
        return self.name

class VPNUser(NetBoxModel):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
    ]

    username = models.CharField(max_length=100)
    group = models.ForeignKey(
        to=VPNGroup,
        on_delete=models.PROTECT,
        related_name='users'
    )
    fullname = models.CharField("Full Name", max_length=100, blank=True)
    password = models.CharField(max_length=150, blank=True)
    password_hash = models.CharField(max_length=256, blank=True)
    email = models.EmailField(blank=True)
    company = models.CharField(max_length=100, blank=True)
    ttl = models.DateField(
        "TTL",
        blank=True,
        null=True,
        help_text="Account lifetime in DD.MM.YYYY format"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active'
    )

    class Meta:
        ordering = ['username']
        unique_together = ['username', 'group']
        verbose_name = 'RA-VPN User'
        verbose_name_plural = 'RA-VPN Users'

    @property
    def formatted_ttl(self):
        if self.ttl:
            return self.ttl.strftime('%b. %d, %Y')
        return None

    def save(self, *args, **kwargs):
        if self.password:
            self.password_hash = make_password(self.password)
        else:
            self.password_hash = ''
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
