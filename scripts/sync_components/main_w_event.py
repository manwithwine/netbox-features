from dcim.models import (
    Device,
    ConsolePort, ConsoleServerPort, PowerPort, ModuleBay, Interface,
    ConsolePortTemplate, ConsoleServerPortTemplate, PowerPortTemplate, ModuleBayTemplate, InterfaceTemplate,
    DeviceType,
)
from extras.scripts import Script
from django.db import transaction
import time


class FixDeviceComponents(Script):
    class Meta:
        name = "Update Device Components via Event Rules"
        description = "Sync device components with device type templates (create/update/delete) when templates change."

    def run(self, data, commit):
        total_start = time.time()
        self.log_info("⚙️ Starting component sync script")

        # NetBox может передать null, если Action data пустое
        data = data or {}

        try:
            device_type = self._get_device_type_from_event_data(data)
            if not device_type:
                self.log_failure(
                    "❌ Could not determine device_type from event data. "
                    "Fix: set Event Rule Action data to {} (not empty)."
                )
                self.log_info(f"🔎 Incoming data was: {data!r}")
                return "No device_type in event data"

            self.log_info(f"🔄 Processing device type: {device_type} (ID: {device_type.id})")

            devices = Device.objects.filter(device_type_id=device_type.id)
            self.log_info(f"📱 Found {devices.count()} devices of type {device_type}")

            totals = {"created": 0, "updated": 0, "deleted": 0, "devices": 0}

            for device in devices:
                device_start = time.time()
                self.log_info(f"\n🔧 Device: {device.name} (ID: {device.id})")

                with transaction.atomic():
                    # Console ports
                    c, u, d = self._sync_simple_components(
                        device=device,
                        model=ConsolePort,
                        templates=ConsolePortTemplate.objects.filter(device_type=device_type),
                        fields=("type", "description"),
                        label="ConsolePort",
                    )
                    totals["created"] += c
                    totals["updated"] += u
                    totals["deleted"] += d

                    # Console server ports
                    c, u, d = self._sync_simple_components(
                        device=device,
                        model=ConsoleServerPort,
                        templates=ConsoleServerPortTemplate.objects.filter(device_type=device_type),
                        fields=("label", "physical_label", "type", "description"),
                        label="ConsoleServerPort",
                    )
                    totals["created"] += c
                    totals["updated"] += u
                    totals["deleted"] += d

                    # Power ports
                    c, u, d = self._sync_simple_components(
                        device=device,
                        model=PowerPort,
                        templates=PowerPortTemplate.objects.filter(device_type=device_type),
                        fields=("type", "description"),
                        label="PowerPort",
                    )
                    totals["created"] += c
                    totals["updated"] += u
                    totals["deleted"] += d

                    # Interfaces (с твоими полями)
                    c, u, d = self._sync_interfaces(device, device_type)
                    totals["created"] += c
                    totals["updated"] += u
                    totals["deleted"] += d

                    # Module bays
                    c, u, d = self._sync_module_bays(device, device_type)
                    totals["created"] += c
                    totals["updated"] += u
                    totals["deleted"] += d

                totals["devices"] += 1
                self.log_success(f"✅ Device done in {time.time() - device_start:.2f}s")

            total_time = time.time() - total_start
            result = (
                f"Done for DeviceType {device_type} (id={device_type.id}). "
                f"Devices: {totals['devices']}/{devices.count()}. "
                f"Created={totals['created']}, Updated={totals['updated']}, Deleted={totals['deleted']}. "
                f"Time={total_time:.2f}s"
            )
            self.log_success(f"\n🏁 {result}")
            return result

        except Exception as e:
            import traceback
            self.log_failure(f"❌ Script failed: {e}")
            self.log_failure(traceback.format_exc())
            raise

    # ---------- event data parsing ----------

    def _get_device_type_from_event_data(self, data):
        dt = None
        if isinstance(data, dict):
            dt = data.get("device_type")
            if dt is None and isinstance(data.get("data"), dict):
                dt = data["data"].get("device_type")

        device_type_id = None
        if isinstance(dt, dict):
            device_type_id = dt.get("id")
        elif isinstance(dt, int):
            device_type_id = dt
        elif isinstance(dt, str) and dt.isdigit():
            device_type_id = int(dt)

        if not device_type_id:
            return None

        return DeviceType.objects.filter(id=device_type_id).first()

    # ---------- generic sync ----------

    def _sync_simple_components(self, device, model, templates, fields, label):
        """
        Синхронизация по name:
          - create отсутствующие
          - update указанные поля
          - delete лишние
        """
        templates_by_name = {t.name: t for t in templates}
        existing_by_name = {o.name: o for o in model.objects.filter(device=device)}

        created = updated = deleted = 0

        for name, tpl in templates_by_name.items():
            obj = existing_by_name.get(name)
            if not obj:
                kwargs = {"device": device, "name": tpl.name}
                for f in fields:
                    if hasattr(tpl, f):
                        kwargs[f] = getattr(tpl, f)
                model.objects.create(**kwargs)
                created += 1
                self.log_info(f"  ➕ Created {label}: {name}")
            else:
                changed = False
                for f in fields:
                    if hasattr(obj, f) and hasattr(tpl, f):
                        new_val = getattr(tpl, f)
                        if getattr(obj, f) != new_val:
                            setattr(obj, f, new_val)
                            changed = True
                if changed:
                    obj.save()
                    updated += 1
                    self.log_info(f"  ✏️ Updated {label}: {name}")

        extra_names = set(existing_by_name.keys()) - set(templates_by_name.keys())
        if extra_names:
            qs = model.objects.filter(device=device, name__in=extra_names)
            cnt = qs.count()
            qs.delete()
            deleted += cnt
            for n in sorted(extra_names):
                self.log_info(f"  🗑️ Deleted {label}: {n}")

        return created, updated, deleted

    # ---------- Interface sync with your fields ----------

    def _sync_interfaces(self, device, device_type):
        templates = InterfaceTemplate.objects.filter(device_type=device_type)
        templates_by_name = {t.name: t for t in templates}
        existing_by_name = {i.name: i for i in Interface.objects.filter(device=device)}

        # Ты перечислил эти поля
        fields = (
            "type",
            "description",
            "bridge",
            "poe_mode",
            "poe_type",
            "wireless_role",
        )

        created = updated = deleted = 0

        for name, tpl in templates_by_name.items():
            obj = existing_by_name.get(name)
            if not obj:
                kwargs = {"device": device, "name": tpl.name}
                # безопасно: добавляем только реально существующие поля
                for f in fields:
                    if hasattr(tpl, f):
                        kwargs[f] = getattr(tpl, f)
                Interface.objects.create(**kwargs)
                created += 1
                self.log_info(f"  ➕ Created Interface: {name}")
            else:
                changed = False
                for f in fields:
                    if hasattr(obj, f) and hasattr(tpl, f):
                        new_val = getattr(tpl, f)
                        if getattr(obj, f) != new_val:
                            setattr(obj, f, new_val)
                            changed = True
                if changed:
                    obj.save()
                    updated += 1
                    self.log_info(f"  ✏️ Updated Interface: {name}")

        extra_names = set(existing_by_name.keys()) - set(templates_by_name.keys())
        if extra_names:
            qs = Interface.objects.filter(device=device, name__in=extra_names)
            cnt = qs.count()
            qs.delete()
            deleted += cnt
            for n in sorted(extra_names):
                self.log_info(f"  🗑️ Deleted Interface: {n}")

        return created, updated, deleted

    # ---------- ModuleBay sync ----------

    def _sync_module_bays(self, device, device_type):
        templates = ModuleBayTemplate.objects.filter(device_type=device_type)
        templates_by_name = {t.name: t for t in templates}
        existing_by_name = {m.name: m for m in ModuleBay.objects.filter(device=device)}

        fields = ("label", "position", "description")

        created = updated = deleted = 0

        for name, tpl in templates_by_name.items():
            obj = existing_by_name.get(name)
            if not obj:
                kwargs = {"device": device, "name": tpl.name}
                for f in fields:
                    if hasattr(tpl, f):
                        kwargs[f] = getattr(tpl, f)
                ModuleBay.objects.create(**kwargs)
                created += 1
                self.log_info(f"  ➕ Created ModuleBay: {name}")
            else:
                changed = False
                for f in fields:
                    if hasattr(obj, f) and hasattr(tpl, f):
                        new_val = getattr(tpl, f)
                        if getattr(obj, f) != new_val:
                            setattr(obj, f, new_val)
                            changed = True
                if changed:
                    obj.save()
                    updated += 1
                    self.log_info(f"  ✏️ Updated ModuleBay: {name}")

        extra_names = set(existing_by_name.keys()) - set(templates_by_name.keys())
        if extra_names:
            qs = ModuleBay.objects.filter(device=device, name__in=extra_names)
            cnt = qs.count()
            qs.delete()
            deleted += cnt
            for n in sorted(extra_names):
                self.log_info(f"  🗑️ Deleted ModuleBay: {n}")

        return created, updated, deleted
