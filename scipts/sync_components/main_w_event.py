from dcim.models import (
    Device, ConsolePort, PowerPort, ModuleBay, Interface,
    ConsolePortTemplate, PowerPortTemplate, ModuleBayTemplate, InterfaceTemplate,
    DeviceType
)
from extras.scripts import Script
from django.db import transaction
from django.core.cache import cache
import time


class FixDeviceComponents(Script):
    class Meta:
        name = "Update Device Components via Event Rules"
        description = "Creates missing components when device type changes via Event Rules. Do not delete components."

    def run(self, data, commit):
        total_start = time.time()
        self.log_info("⚙️ Starting component fix script")

        try:
            # Extract device type ID from Event Rule data
            if isinstance(data.get('device_type'), dict):
                device_type_id = data['device_type']['id']
            elif isinstance(data.get('device_type'), (int, str)):
                device_type_id = int(data['device_type'])
            else:
                raise ValueError("Could not determine device type ID from input data")

            # Get all devices of this type
            devices = Device.objects.filter(device_type_id=device_type_id)
            self.log_info(f"Found {devices.count()} devices of type ID {device_type_id}")

            processed_count = 0
            for device in devices:
                device_start = time.time()
                self.log_info(f"\n🔧 Processing device: {device.name} (ID: {device.id})")

                with transaction.atomic():
                    # Process all component types
                    counts = {
                        'console': self._process_component(
                            device, ConsolePort, ConsolePortTemplate, "console ports"
                        ),
                        'power': self._process_component(
                            device, PowerPort, PowerPortTemplate, "power ports"
                        ),
                        'module': self._process_module_bays(device),
                        'interfaces': self._process_interfaces(device)
                    }

                    if commit:
                        self._force_update_counts(device)
                        self._verify_counts(device, counts)
                        processed_count += 1

                device_time = time.time() - device_start
                self.log_success(f"✅ Completed in {device_time:.2f}s")

            total_time = time.time() - total_start
            self.log_success(f"\n🏁 Script completed in {total_time:.2f} seconds")
            self.log_success(f"📊 Successfully processed {processed_count}/{devices.count()} devices")

        except Exception as e:
            self.log_failure(f"❌ Script failed: {str(e)}")
            raise

    def _process_component(self, device, model, template_model, component_name):
        """Create missing components based on templates"""
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
        """Create missing interfaces"""
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
        return created

    def _process_module_bays(self, device):
        """Create missing module bays"""
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
        """Update device component counts"""
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
        device.interface_count = Interface.objects.filter(device=device).count()
        device.save()
        device.refresh_from_db()

    def _verify_counts(self, device, created_counts):
        """Verify component counts"""
        actual_counts = {
            'console': ConsolePort.objects.filter(device=device).count(),
            'power': PowerPort.objects.filter(device=device).count(),
            'module': ModuleBay.objects.filter(device=device).count(),
            'interfaces': Interface.objects.filter(device=device).count()
        }

        self.log_success("\n📊 Count Verification:")
        self.log_success(f"Console Ports: Created {created_counts['console']} | Total: {actual_counts['console']}")
        self.log_success(f"Power Ports: Created {created_counts['power']} | Total: {actual_counts['power']}")
        self.log_success(f"Module Bays: Created {created_counts['module']} | Total: {actual_counts['module']}")