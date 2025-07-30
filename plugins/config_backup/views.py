import os
import difflib
from django.views.generic import ListView, TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.timezone import now
from django.contrib import messages
from dcim.models import Device
from .models import ConfigBackup
from .utilities.backup_utils import backup_device_config
from itertools import zip_longest

class DeviceConfigBackupView(ListView):
    model = ConfigBackup
    template_name = 'netbox_config_backup/configbackup.html'
    context_object_name = 'backups'

    def get_queryset(self):
        return ConfigBackup.objects.filter(device_id=self.kwargs['device_id']).order_by('-created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['device'] = get_object_or_404(Device, pk=self.kwargs['device_id'])
        context['latest'] = ConfigBackup.objects.filter(device=context['device']).order_by('-created').first()
        return context

def collect_backup(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    ip = device.primary_ip or device.oob_ip
    if not ip:
        return redirect(reverse('plugins:netbox_config_backup:device_config_backups', kwargs={'device_id': device.id}))

    username = os.getenv("DEVICE_BACKUP_USER")
    password = os.getenv("DEVICE_BACKUP_PASSWORD")

    config, status = backup_device_config(device, username, password)

    ConfigBackup.objects.create(
        device=device,
        config=config or '',
        last_status=status,
        status='Collected' if config else f"Failed: {status}",
        last_checked=now(),
        collection_mode='MANUAL'
    )
    return redirect(reverse('plugins:netbox_config_backup:device_config_backups', kwargs={'device_id': device.id}))

def enable_backup(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    ip = device.primary_ip or device.oob_ip
    if not ip:
        return redirect(reverse('plugins:netbox_config_backup:device_config_backups', kwargs={'device_id': device.id}))

    username = os.getenv("DEVICE_BACKUP_USER")
    password = os.getenv("DEVICE_BACKUP_PASSWORD")

    # Get existing config (don't collect new one yet)
    latest = ConfigBackup.objects.filter(device=device).order_by('-created').first()
    
    if latest and latest.status in ['Collected', 'Backup Enabled']:
        # Update existing record to auto mode
        latest.status = 'Backup Enabled'
        latest.last_status = 'Auto backup enabled'
        latest.collection_mode = 'AUTO'
        latest.last_checked = now()
        latest.save()
    else:
        # Only collect new config if no suitable existing record
        config, status = backup_device_config(device, username, password)
        ConfigBackup.objects.create(
            device=device,
            config=config or '',
            last_status=status,
            status='Backup Enabled',
            last_checked=now(),
            collection_mode='AUTO'
        )

    return redirect(reverse('plugins:netbox_config_backup:device_config_backups', kwargs={'device_id': device.id}))

def disable_backup(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    
    ConfigBackup.objects.create(
        device=device,
        config='',
        last_status=f'Disabled by user {request.user.username}',
        status='Backup Disabled',
        last_checked=now(),
        collection_mode='MANUAL'
    )
    
    return redirect(reverse('plugins:netbox_config_backup:device_config_backups', 
                         kwargs={'device_id': device.id}))

def delete_backups(request, device_id):
    if request.method == 'POST':
        selected_backups = request.POST.getlist('selected')
        if selected_backups:
            # Update status before deleting
            ConfigBackup.objects.filter(id__in=selected_backups).update(
                last_status=f'Deleted by user {request.user.username}'
            )
            ConfigBackup.objects.filter(id__in=selected_backups).delete()
            messages.success(request, f"Deleted {len(selected_backups)} backup(s)")
        else:
            messages.warning(request, "No backups selected for deletion")
    return redirect(reverse('plugins:netbox_config_backup:device_config_backups', 
                         kwargs={'device_id': device_id}))

def view_config(request, device_id, backup_id):
    device = get_object_or_404(Device, id=device_id)
    backup = get_object_or_404(ConfigBackup, id=backup_id, device=device)
    return render(request, 'netbox_config_backup/view_config.html', {
        'device': device,
        'backup': backup
    })

class ConfigDiffView(TemplateView):
    template_name = 'netbox_config_backup/configdiff.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids = self.request.GET.getlist('selected')
        if len(ids) != 2:
            context['error'] = "Select exactly 2 configs to compare"
            return context

        config1 = get_object_or_404(ConfigBackup, pk=ids[0])
        config2 = get_object_or_404(ConfigBackup, pk=ids[1])

        lines1 = config1.config.strip().splitlines()
        lines2 = config2.config.strip().splitlines()

        sm = difflib.SequenceMatcher(None, lines1, lines2)
        diff_blocks = []
        left_line = 1
        right_line = 1

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            max_lines = max(i2 - i1, j2 - j1)
            for idx in range(max_lines):
                l = lines1[i1+idx] if i1+idx < i2 else ""
                r = lines2[j1+idx] if j1+idx < j2 else ""
                diff_blocks.append({
                    "left": l,
                    "right": r,
                    "tag": tag,
                    "left_no": left_line if l else "",
                    "right_no": right_line if r else ""
                })
                if l:
                    left_line += 1
                if r:
                    right_line += 1

        context['config1'] = config1
        context['config2'] = config2
        context['diff_blocks'] = diff_blocks
        return context
