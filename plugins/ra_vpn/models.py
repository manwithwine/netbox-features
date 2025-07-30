from django.db import models
from django.contrib.auth.hashers import make_password
from netbox.models import NetBoxModel
from tenancy.models import Tenant, Contact

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.validators import MaxLengthValidator

import winrm
from dotenv import load_dotenv
import os

load_dotenv('/etc/netbox_ad_sync.env') #HERE U STORE LOGIN AND PASSWORD TO ACCESS ACTIVE DIRECTORY
AD_USERNAME = os.getenv('AD_USERNAME')
AD_PASSWORD = os.getenv('AD_PASSWORD')
AD_SERVER = 'http://X.X.X.X:5985'  # SET UR IP OF AD SERVER

class VPNGroup(NetBoxModel):
    name = models.CharField(max_length=100, unique=True)
    acl = models.TextField("ACL", blank=True)
    attribute = models.CharField(max_length=350, blank=True)
    owner = models.ForeignKey(
        'tenancy.Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owner_vpn_groups'
    )
    deputy = models.ForeignKey(
        'tenancy.Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deputy_for_vpn_groups'
    )
    purpose = models.CharField(max_length=350, blank=True)
    tenant = models.ForeignKey(
        to=Tenant,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='vpn_groups'
    )
    ttl = models.DateField("TTL", blank=True, null=True)
    owneraudit = models.DateField("Owner Audit", blank=True, null=True)
    adminaudit = models.DateField("Admin Audit", blank=True, null=True)

    class Meta:
        ordering = ['tenant__name', 'name']
        verbose_name = 'RA-VPN Group'
        verbose_name_plural = 'RA-VPN Groups'

    def __str__(self):
        return self.name

class VPNUser(NetBoxModel):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
    ]

    username = models.CharField(max_length=100)
    group = models.ForeignKey(to=VPNGroup, on_delete=models.PROTECT, related_name='users')
    fullname = models.CharField("Full Name", max_length=100, blank=True)
    password = models.CharField(max_length=150, blank=True)
    password_hash = models.CharField(max_length=256, blank=True)
    email = models.EmailField(blank=True)
    company = models.CharField(max_length=100, blank=True)
    ttl = models.DateField("TTL", blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    static_ip = models.CharField("Static IP", max_length=15, blank=True)
    description = models.CharField("Description", max_length=300, blank=True)

    class Meta:
        ordering = ['username']
        unique_together = ['username', 'group']
        verbose_name = 'RA-VPN User'
        verbose_name_plural = 'RA-VPN Users'

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        self.password_hash = make_password(self.password) if self.password else ''
        super().save(*args, **kwargs)

# AD CREATE SYNC
@receiver(post_save, sender=VPNUser)
def create_ad_user(sender, instance, created, **kwargs):
    if not created:
        return

    username = instance.username
    password = instance.password
    fullname = instance.fullname or username
    email = instance.email or f"{username}@example.com"
    company = instance.company or "Default"
    ttl = instance.ttl.strftime("%Y-%m-%d") if instance.ttl else ""
    group = instance.group.name
    description = instance.description

    is_external = company.lower() not in ["URCOMPANY NAME"]
    groups = f"vpn-test,{group}" # SET UR DEFAULT GROUP FOR USER (vpn-test as example)
#    if not is_external:
#        groups += ",vpn-ifneeded" # CAN SET ANOTHER GROUP FOR EXTERNAL USERS

    primary_group = "vpn-test" if is_external else "" # REPLACE vpn-test WITH UR PRIMARY GROUP
    remove_domain_users = "true" if is_external else "false"
    ou = group

    ps_script = f"""
        $Username = "{username}"
        $Password = "{password}"
        $FullName = "{fullname}"
        $Email = "{email}"
        $Company = "{company}"
        $OU = "{ou}"
        $Groups = "{groups}"
        $PrimaryGroup = "{primary_group}"
        $RemoveDomainUsers = "{remove_domain_users}"
        $Expires = "{ttl}"
        $Description = "{description}"

        $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force

        try {{
            New-ADUser -Name $FullName -GivenName ($FullName.Split(" ")[0]) -Surname ($FullName.Split(" ")[1]) `
                -SamAccountName $Username -UserPrincipalName "$Username@your_domain.com" -EmailAddress $Email `
                -Company $Company -Description $Description -Path "OU=$OU,OU=your-ou-name,DC=your,DC=domain,DC=com/ru" `    #NEED UR DATA
                -AccountPassword $SecurePassword -Enabled $true -PasswordNeverExpires $true -ChangePasswordAtLogon $false
        }} catch {{
            Write-Output "ERROR creating user: $($_.Exception.Message)"
            exit 1
        }}

        Start-Sleep -Seconds 2

        foreach ($group in $Groups.Split(",")) {{
            try {{ Add-ADGroupMember -Identity $group -Members $Username -ErrorAction Stop }} catch {{ }}
        }}

        if (-not [string]::IsNullOrEmpty($PrimaryGroup)) {{
            try {{
                $user = Get-ADUser -Identity $Username -Properties PrimaryGroupID
                $newGroup = Get-ADGroup -Identity $PrimaryGroup -Properties PrimaryGroupToken
                Set-ADUser -Identity $user -Replace @{{PrimaryGroupID = $newGroup.PrimaryGroupToken}}

                if ($RemoveDomainUsers -eq "true") {{
                    Remove-ADGroupMember -Identity "vpn-test2" -Members $Username -Confirm:$false   #### SET VPN-GROUP WHICH SHOULD BE REMOVED FOR EXTERNAL USER
                }}
            }} catch {{ }}
        }}

        if ($Expires) {{
            try {{ Set-ADAccountExpiration -Identity $Username -DateTime $Expires }} catch {{ }}
        }}
    """

    try:
        session = winrm.Session(AD_SERVER, auth=(AD_USERNAME, AD_PASSWORD), transport='ntlm')
        result = session.run_ps(ps_script)
        if result.status_code != 0:
            print(f"[STDERR]: {result.std_err.decode()}")
        else:
            print(f"[OK]: {result.std_out.decode()}")
    except Exception as e:
        print(f"[EXCEPTION]: AD sync failed: {e}")

# AD UPDATE SYNC
@receiver(pre_save, sender=VPNUser)
def update_ad_user(sender, instance, **kwargs):
    try:
        old = VPNUser.objects.get(pk=instance.pk)
    except VPNUser.DoesNotExist:
        return

    changes = {
        'password': old.password != instance.password,
        'status': old.status != instance.status,
        'ttl': old.ttl != instance.ttl,
        'email': old.email != instance.email,
        'description': old.description != instance.description,
        'group': old.group != instance.group
    }

    if not any(changes.values()):
        return

    ps_script = f"""
        $Username = "{instance.username}"
        $Password = "{instance.password if changes['password'] else ''}"
        $Status = "{instance.status if changes['status'] else ''}"
        $Expires = "{'clear' if instance.ttl is None else instance.ttl.strftime('%Y-%m-%d') if changes['ttl'] else ''}"
        $Email = "{instance.email}"
        $Description = "{instance.description}"
        $NewGroup = "{instance.group.name}"
        $OldGroup = "{old.group.name if changes['group'] else ''}"

        if ($Status -eq "deprecated") {{ Disable-ADAccount -Identity $Username }}
        elseif ($Status -eq "active") {{ Enable-ADAccount -Identity $Username }}

        if ($Password) {{
            $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
            Set-ADAccountPassword -Identity $Username -NewPassword $SecurePassword -Reset
        }}

        if ($Expires) {{
            if ($Expires -eq "clear") {{ Set-ADAccountExpiration -Identity $Username -Clear }}
            else {{
                $expiry = Get-Date "$Expires 23:59:59"
                Set-ADAccountExpiration -Identity $Username -DateTime $expiry
            }}
        }}

        if ($Email) {{ Set-ADUser -Identity $Username -EmailAddress $Email }}
        if ($Description) {{ Set-ADUser -Identity $Username -Description $Description }}

        if ($OldGroup -and $NewGroup -and ($OldGroup -ne $NewGroup)) {{
            $ignore = @("vpn-test1", "vpn-test2", "vpn-test3")                      ##### REPLACE WITH UR VPN-GROUPS
            if ($ignore -notcontains $OldGroup) {{ Remove-ADGroupMember -Identity $OldGroup -Members $Username -Confirm:$false }}
            if ($ignore -notcontains $NewGroup) {{
                Add-ADGroupMember -Identity $NewGroup -Members $Username
                $newOU = "OU=$NewGroup,OU=your-ou-name,DC=your,DC=domain,DC=com/ru"    ##### NEED UR DATA
                Get-ADUser $Username | Move-ADObject -TargetPath $newOU
            }}
        }}
    """

    try:
        session = winrm.Session(AD_SERVER, auth=(AD_USERNAME, AD_PASSWORD), transport='ntlm')
        result = session.run_ps(ps_script)
        if result.status_code != 0:
            print(f"[AD UPDATE ERROR]: {result.std_err.decode()}")
        else:
            print(f"[AD UPDATE OK]: {result.std_out.decode()}")
    except Exception as e:
        print(f"[EXCEPTION]: AD update failed: {e}")

# AD CREATE GROUP STRUCTURE
@receiver(post_save, sender=VPNGroup)
def create_ad_group_structure(sender, instance, created, **kwargs):
    if not created:
        return

    group_name = instance.name

    ps_script = f"""
        $GroupName = "{group_name}"
        $GroupOU = "OU=your-ou-name,DC=your,DC=domain,DC=com/ru"    #NEED UR DATA
        $UserOU = "OU=your-ou-name,DC=your,DC=domain,DC=com/ru"    #NEED UR DATA

        if (-not (Get-ADGroup -Filter "Name -eq '$GroupName'" -SearchBase $GroupOU -ErrorAction SilentlyContinue)) {{
            New-ADGroup -Name $GroupName -SamAccountName $GroupName -GroupScope Global -GroupCategory Security -Path $GroupOU
        }}

        $OUPath = "OU=$GroupName,$UserOU"
        if (-not (Get-ADOrganizationalUnit -Filter "Name -eq '$GroupName'" -SearchBase $UserOU -ErrorAction SilentlyContinue)) {{
            New-ADOrganizationalUnit -Name $GroupName -Path $UserOU
        }}
    """

    try:
        session = winrm.Session(AD_SERVER, auth=(AD_USERNAME, AD_PASSWORD), transport='ntlm')
        result = session.run_ps(ps_script)
        if result.status_code != 0:
            print(f"[AD CREATE GROUP ERROR]: {result.std_err.decode()}")
        else:
            print(f"[AD GROUP SETUP OK]: {result.std_out.decode()}")
    except Exception as e:
        print(f"[EXCEPTION]: AD group structure creation failed: {e}")
