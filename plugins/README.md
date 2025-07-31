# Plugins

Tested for Netbox 4.2.4

## Немного теории

### Зачем нужны?
Позволяют настраивать NetBox под конкретные нужды, автоматизировать сетевые процессы и повысить удобство использования.\
Теперь базовое описание, как это все работает.

### Структура плагина.
1.**__init__.py**— "Паспорт" плагина

Этот файл сообщает NetBox:
- Как называется плагин 
- Какая у него версия 
- Кто автор 
- Где искать остальные файлы

**Пример:**
```
from netbox.plugins import PluginConfig

class MyPluginConfig(PluginConfig):
    name = 'netbox_myplugin'  # Техническое имя (без пробелов)
    verbose_name = 'Мой плагин'  # Человекочитаемое название
    description = 'Плагин для чего-то полезного'  # Описание
    version = '1.0'  # Версия
    author = 'Ваше имя'  # Автор
    base_url = 'myplugin'  # Часть URL (например, `netbox.mycompany.com/plugins/myplugin/`)

config = MyPluginConfig  # NetBox ищет именно эту переменную!
```
**Примечание:** начиная с версии 3.5 используется модуль netbox.plugins, на старых версиях extras.plugins

**Зачем нужен?**\
Без него NetBox не распознает папку как плагин.

2. **models.py** -  "База данных" плагина

Здесь вы описываете, какие данные будет хранить плагин.

**Пример:**

```
from django.db import models
from netbox.models import NetBoxModel

class DeviceBackup(NetBoxModel):  # Модель для хранения бэкапов устройств
    device = models.ForeignKey('dcim.Device', on_delete=models.CASCADE)  # Связь с устройством
    config = models.TextField()  # Текст конфигурации
    date = models.DateTimeField(auto_now_add=True)  # Дата создания
    
    def __str__(self):
        return f"Backup for {self.device.name}"
```

**Зачем нужен?**\
Определяет таблицы в базе данных (например,netbox_config_backup хранит бэкапы).\
После изменения этого файла нужно запускать миграции (об этом ниже).

3. **migrations** — "История изменений базы данных"

Когда вы меняете models.py, NetBox создаёт файлы миграций — это инструкции, как обновить базу.

**Как работают миграции?**
- Вы меняете models.py (например, добавили новое поле). 
- Запускаете:
```
python3 /opt/netbox/netbox/manage.py makemigrations
```
→ NetBox создаёт файл в migrations/0002_add_new_field.py.

- Применяете изменения:
```
python3 /opt/netbox/netbox/manage.py migrate
```
→ Теперь в базе появилось новое поле.

**⚠️ Важно:**\
Не удаляйте старые миграции — без них не получится развернуть плагин с нуля.

Если что-то сломалось — можно откатиться:
```
python3 /opt/netbox/netbox/manage.py migrate netbox_myplugin 0001
```

4. **templates** — "HTML-страницы плагина"

Здесь лежат шаблоны страниц. Например:
```
templates/
└── netbox_myplugin/
    ├── device_backup.html  # Страница просмотра бэкапа
    └── list.html          # Список всех бэкапов
```

**Как работает?**\
NetBox использует Django-шаблоны.\
Можно вставлять данные из views.py (например, {{ backup.config }}).

**Пример device_backup.html:**

```
{% extends 'base.html' %}  <!-- Наследуемся от стандартного дизайна NetBox -->

{% block content %}
<h1>Бэкап устройства {{ object.device.name }}</h1>
<pre>{{ object.config }}</pre>
{% endblock %}
```



5. **views.py** — "Логика страниц"

Определяет, что будет отображаться при переходе по URL.

**Пример:**
```
from django.views.generic import DetailView
from .models import DeviceBackup

class BackupView(DetailView):
    model = DeviceBackup  # Используем нашу модель
    template_name = 'netbox_myplugin/device_backup.html'  # Шаблон из templates/
```


**Зачем нужен?**
- Решает, какие данные передать в шаблон. 
- Обрабатывает действия пользователя (например, кнопка "Скачать бэкап").

6. **urls.py** — "Маршруты (ссылки) плагина"

Говорит NetBox, по каким адресам доступен плагин.

**Пример:**
```
from django.urls import path
from .views import BackupView

urlpatterns = [
    path('backups/<int:pk>/', BackupView.as_view(), name='device_backup'),
]
```
→ Теперь страница будет доступна по адресу:
https://netbox.example.com/plugins/myplugin/backups/1/

7. api — "REST API для интеграций"

Нужен, если вы хотите:
- Работать с плагином через API (например, из скриптов). 
- Интегрировать его с другими системами.

1) api/serializers.py — "Переводчик между Python и JSON"
Позволяет преобразовать данные из базы в API-ответ.

**Пример:**
```
from rest_framework import serializers
from .models import DeviceBackup

class BackupSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceBackup
        fields = ['id', 'device', 'config', 'date']  # Какие поля отдавать в API
```

2) api/views.py— "Логика API"

Определяет, какие данные можно получить через API.
``` 
from rest_framework import viewsets
from .models import DeviceBackup
from .serializers import BackupSerializer

class BackupViewSet(viewsets.ModelViewSet):
    queryset = DeviceBackup.objects.all()
    serializer_class = BackupSerializer
```

3) api/urls.py — "Маршруты API"
``` 
from rest_framework import routers
from .views import BackupViewSet

router = routers.DefaultRouter()
router.register('backups', BackupViewSet)

urlpatterns = router.urls
```
→ Теперь API доступно по адресу:
https://netbox.example.com/api/plugins/myplugin/backups/

8. **tables.py** и **filters.py** — "Списки и фильтры"

**tables.py** — настраивает отображение таблиц (например, список бэкапов).

**filters.py** — добавляет фильтры (например, поиск по имени устройства).

**Пример tables.py:**
``` 
import django_tables2 as tables
from .models import DeviceBackup

class BackupTable(tables.Table):
    device = tables.Column(linkify=True)  # Делает имя устройства кликабельным
    
    class Meta:
        model = DeviceBackup
        fields = ['device', 'date']  # Какие столбцы показывать
```

9. forms.py — "Формы для редактирования"

Определяет поля, которые видит пользователь при создании/редактировании записи.

**Пример:**
``` 
from django import forms
from .models import DeviceBackup

class BackupForm(forms.ModelForm):
    class Meta:
        model = DeviceBackup
        fields = ['device', 'config']  # Какие поля можно редактировать
```

**Дополнение:**

1) **signals.py** — "Реакция на события в NetBox"

Раньше этот файл использовался для автоматического выполнения кода при событиях (например, когда создаётся устройство или меняется IP-адрес).\
Но сейчас (в новых версиях NetBox) сигналы работают нестабильно, и разработчики рекомендуют другие способы.

**Как заменить signals.py?**

**Вариант 1:** Использовать netbox-rq (фоновые задачи)\
Если нужно выполнить что-то после изменения данных (например, при создании устройства сделать бэкап):

- Создайте задачу в tasks.py:
``` 
from django_rq import job

@job  # Делает функцию фоновой задачей
def backup_device_config(device_id):
    device = Device.objects.get(id=device_id)
    # ... код создания бэкапа ...
```
- Вызывайте её из кода (например, в views.py):
``` 
from .tasks import backup_device_config
backup_device_config.delay(device.id)  # Запуск в фоне
```

**Вариант 2:** Использовать хуки (Webhooks)\
NetBox может отправлять HTTP-запросы при событиях (например, на ваш скрипт).\
**Настройка:**
```aiignore
Администрирование → Webhooks → Добавить новый.

Указать URL вашего сервиса, который будет обрабатывать событие.
```

**Вариант 3:** Планировщик (Cron)\
Если действие должно выполняться по расписанию (например, раз в день):\

- Добавьте команду в management/commands/ (см. ниже). 
- Настройте Cron на сервере - crontab -e:
``` 
# Каждый день в 3:00
0 3 * * * /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py my_plugin_command
```
- Проверить текущую настройку: **_crontab -l_**

2) **management/commands/** — CLI-команды для плагина

Позволяет создавать свои команды, которые можно запускать через manage.py.

**Пример:** команда для очистки старых бэкапов

- Создайте файл:
management/commands/cleanup_old_backups.py

```
from django.core.management.base import BaseCommand
from netbox_config_backup.models import ConfigBackup

class Command(BaseCommand):
    help = 'Удаляет бэкапы старше 30 дней'

    def handle(self, *args, **options):
        from datetime import datetime, timedelta
        old_backups = ConfigBackup.objects.filter(
            last_updated__lt=datetime.now() - timedelta(days=30)
        )
        count = old_backups.count()
        old_backups.delete()
        self.stdout.write(f"Удалено {count} старых бэкапов")
```

- Теперь можно запускать:
```
python3 /opt/netbox/netbox/manage.py cleanup_old_backups
```


**Где использовать?**
- Очистка старых данных (как в примере выше). 
- Синхронизация с внешними системами (например, Active Directory). 
- Массовое обновление данных (если нельзя сделать через API).

3) **setup.py** — Упаковка плагина в Python-пакет

Нужен только если вы хотите:

- Выложить плагин в PyPI (чтобы его можно было установить через pip). 
- Распространять плагин как отдельный пакет.

**Пример:**

from setuptools import setup, find_packages

```
setup(
    name="netbox-config-backup",
    version="1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],  # Зависимости (например, requests)
)
```

**Когда е нужен setup.py?**
- Если плагин используется только локально в вашем NetBox. 
- Вы не планируете публиковать его в PyPI.

4) **MANIFEST.in** — Включение дополнительных файлов в пакет

Если используете setup.py, этот файл указывает, какие не-Python файлы добавить в пакет (шаблоны, CSS, JS).

**Пример:**
```
include netbox_config_backup/templates/*.html
include netbox_config_backup/static/*
```
**Когда не нужен MANIFEST.in?**

- Если не используете setup.py. 
- Все файлы уже включены автоматически.

## Как добавить плагин в NetBox?

1) Положите папку плагина в /opt/netbox/netbox/plugins/.

2) Откройте /opt/netbox/netbox/netbox/configuration.py и добавьте:

PLUGINS = ['netbox_myplugin']  # Имя из __init__.py

3) Примените миграции:
```
python3 /opt/netbox/netbox/manage.py makemigrations
python3 /opt/netbox/netbox/manage.py migrate
```
4) Перезапустите NetBox:
```
systemctl restart netbox netbox-rq
```



По итогу получится следующая структура директории:
```
netbox_myplugin/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── migrations/
│   └── __init__.py
├── templates/
│   └── netbox_myplugin/
├── models.py
├── views.py
├── urls.py
├── filters.py
├── forms.py
└── tables.py
```

### Разница между сервисами netbox и netbox-rq.

netbox:
- Основной сервис NetBox (веб-сервер)
- Обрабатывает HTTP-запросы, отображает интерфейс 
- Отвечает за основную функциональность

netbox-rq:
- Сервис для обработки фоновых задач (на основе Redis Queue)
- Выполняет длительные операции (например, сбор бэкапов конфигураций)
- Обрабатывает задачи, которые не должны блокировать веб-интерфейс

**Используется для:**
- Планируемых задач (cron-like)
- Асинхронного выполнения длительных операций 
- Обработки webhook-ов




P.S. вся инфа выше - просто мой небольшой опыт написания плагинов, используя ИИ.\
Как совет могу предложить: смотреть готовые плагины, которые можно найти в инете \
Рекомендую использовать DeepSeek, вместо ChatGPT. DeepSeek справлялся намного лучше, даже если сравнивать с ChatGPT+.