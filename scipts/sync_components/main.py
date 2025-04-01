from dcim.models import (
    Device, ConsolePort, PowerPort, ModuleBay, Interface,
    ConsolePortTemplate, PowerPortTemplate, ModuleBayTemplate, InterfaceTemplate,
    DeviceType, Manufacturer
)
from extras.scripts import Script, ObjectVar, MultiObjectVar
from django.db import transaction
from django.core.cache import cache
import time


class FixDeviceComponents(Script):
    class Meta:
        name = "Fix Device Components"
        description = "Creates missing components and fixes counts"

    manufacturer = ObjectVar(
        model=Manufacturer,
        required=False,
        label="Filter by Manufacturer (optional)"
    )

    device_type = ObjectVar(
        model=DeviceType,
        query_params={'manufacturer_id': '$manufacturer'},
        required=False,
        label="Filter by Device Type (optional)"
    )

    devices = MultiObjectVar(
        model=Device,
        query_params={'device_type_id': '$device_type'},
        required=True,
        label="Devices to process"
    )

    def run(self, data, commit):
        total_start = time.time()
        self.log_info("⚙️ Selection Summary:")
        if data.get('manufacturer'):
            self.log_info(f"• Manufacturer: {data['manufacturer']}")
        if data.get('device_type'):
            self.log_info(f"• Device Type: {data['device_type']}")
        self.log_info(f"• Selected Devices: {len(data['devices'])}")

        for device in data['devices']:
            device_start = time.time()
            self.log_info(f"\n🔧 Processing device: {device.name} (ID: {device.id})")

            try:
                with transaction.atomic():
                    counts = {
                        'console': self._process_component(
                            device, ConsolePort, ConsolePortTemplate, "console ports"
                        ),
                        'power': self._process_component(
                            device, PowerPort, PowerPortTemplate, "power ports"
                        ),
                        'module': self._process_module_bays(device),
                        'interfaces': self._process_interfaces(device)  # Silent processing
                    }

                    if commit:
                        self._force_update_counts(device)
                        self._verify_counts(device, counts)

            except Exception as e:
                self.log_failure(f"❌ Failed processing {device.name}: {str(e)}")
                continue

            device_time = time.time() - device_start
            self.log_success(f"✅ Completed in {device_time:.2f}s")

        total_time = time.time() - total_start
        self.log_success(f"\n🏁 Script completed in {total_time:.2f} seconds")

    def _process_component(self, device, model, template_model, component_name):
        """Process visible components with logging"""
        existing = set(model.objects.filter(device=device).values_list('name', flat=True))
        templates = template_model.objects.filter(device_type=device.device_type)

        created = 0
        for template in templates:
            if template.name not in existing:
                model.objects.create(
                    device=device,
                    name=template.name,
                    type=template.type,
                    description=template.description
                )
                created += 1
                self.log_info(f"➕ Created {component_name}: {template.name}")
        return created

    def _process_interfaces(self, device):
        """Silently process interfaces without logging"""
        existing = set(Interface.objects.filter(device=device).values_list('name', flat=True))
        templates = InterfaceTemplate.objects.filter(device_type=device.device_type)

        created = 0
        for template in templates:
            if template.name not in existing:
                Interface.objects.create(
                    device=device,
                    name=template.name,
                    type=template.type,
                    mgmt_only=template.mgmt_only,
                    description=template.description
                )
                created += 1
        return created  # Return count but don't log

    def _process_module_bays(self, device):
        existing = set(ModuleBay.objects.filter(device=device).values_list('name', flat=True))
        templates = ModuleBayTemplate.objects.filter(device_type=device.device_type)

        created = 0
        for template in templates:
            if template.name not in existing:
                ModuleBay.objects.create(
                    device=device,
                    name=template.name,
                    label=template.label,
                    position=template.position
                )
                created += 1
                self.log_info(f"➕ Created module bay: {template.name}")
        return created

    def _force_update_counts(self, device):
        """Update all relevant counts including interfaces"""
        cache_keys = [
            f'device_{device.id}_components',
            f'device_{device.id}_counts',
            'device_component_counts',
            'device_full_components'
        ]
        for key in cache_keys:
            cache.delete(key)

        device.console_port_count = ConsolePort.objects.filter(device=device).count()
        device.power_port_count = PowerPort.objects.filter(device=device).count()
        device.module_bay_count = ModuleBay.objects.filter(device=device).count()
        device.interface_count = Interface.objects.filter(device=device).count()  # New
        device.save()
        device.refresh_from_db()

    def _verify_counts(self, device, created_counts):
        """Verify counts including interfaces (but don't show interface logs)"""
        actual_counts = {
            'console': ConsolePort.objects.filter(device=device).count(),
            'power': PowerPort.objects.filter(device=device).count(),
            'module': ModuleBay.objects.filter(device=device).count(),
            'interfaces': Interface.objects.filter(device=device).count()  # Silent
        }

        self.log_success("\n📊 Count Verification:")
        self.log_success(f"Console Ports: Created {created_counts['console']} | Total: {actual_counts['console']}")
        self.log_success(f"Power Ports: Created {created_counts['power']} | Total: {actual_counts['power']}")
        self.log_success(f"Module Bays: Created {created_counts['module']} | Total: {actual_counts['module']}")
        # Interfaces intentionally omitted from logs

        if (actual_counts['console'] != device.console_port_count or
                actual_counts['power'] != device.power_port_count):
            self.log_warning("⚠ Count mismatch detected! Running cache rebuild...")
            from django.core.management import call_command
            call_command('calculate_cached_counts')
            device.refresh_from_db()