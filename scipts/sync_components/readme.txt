В NetBox v4.2.4 обнаружили следующую проблему:
Eсли есть существующий Device привязанный к Device Type.
Далее если мы добавим в Device Type, например, Interface, Power port или Console Port, или Module Bay, то у этого Device информация не обновится автоматически.
Как оказалось, это дефолтное поведение.

Interface можно подтянуть с помощью плагина, который можно найти на просторах интернета. Однако отсуствует плагин, который позволял бы подтягивать Console, Power и etc.
Для решения данной проблемы обнаружил следующий скрипт:
https://github.com/netbox-community/customizations/blob/master/scripts/add_device_type_components.py

К сожалению, для версии 4.2.4 данный скрипт не отрабатывал корректно. Тем не менее спасибо автору, ведь было от чего отталкиваться.

В следствие, было решено написать свой собственный скрипт (main.py), который решал бы данную проблему.

Небольшой гайд по запуску данного скрипта (перед началом рекомендуется снять Snapshot, чтобы в случае проблемы откатиться!!!):
1. Убедиться, что у Вас в целом есть возможность запускать скрипты через Web: Customization > Scripts > Add.
   Если добавить скрипт не удается, это означает, что у Вас отсутствует сервис rqworker.
   Необходимо создать его на Вашем сервере.

   Команды для Ubuntu/Debian:
   - sudo nano /etc/systemd/system/netbox-rqworker.service
     Далее добавляем следущий текст:
```
[Unit]
Description=NetBox RQ Workerz
After=network.target

[Service]
User=netbox
Group=netbox
WorkingDirectory=/opt/netbox/netbox
ExecStart=/opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker default
Restart=always
RestartSec=30
Environment=PYTHONPATH=/opt/netbox/netbox

[Install]
WantedBy=multi-user.target
```
    Далее:
    - sudo systemctl daemon-reload
    - sudo systemctl enable netbox-rqworker.service
    - sudo systemctl start netbox-rqworker.service
    - sudo systemctl status netbox-rqworker.service

    При успешном выполнении вывод:
```
● netbox-rqworker.service - NetBox RQ Worker
     Loaded: loaded (/etc/systemd/system/netbox-rqworker.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2025-04-01 12:02:16 MSK; 1h 18min ago
   Main PID: 156249 (python)
      Tasks: 3 (limit: 9393)
     Memory: 196.9M
        CPU: 49.787s
     CGroup: /system.slice/netbox-rqworker.service
             ├─156249 /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker default
             └─156314 /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py rqworker default
```
2. Также необходимо убедиться, что в /opt/netbox/netbox/netbox/configuration.py снят комментарий со следующих строк:
```
# The file path where custom scripts will be stored. A trailing slash is not needed. Note that the default value of
# this setting is derived from the installed location.
SCRIPTS_ROOT = '/opt/netbox/netbox/scripts'
SCRIPTS_COMMIT_DEFAULT = True
```

3. Теперь мы наконец-то можешь добавить скрипт через Web:
   - Customization > Scripts > Add
   - Выбираем файл main.py

4. Теперь можно запускать скрипт.
   - Выбираем Вендора (Manufacture) по необходимости
   - ВЫбираем Device Type
   - Выбираем из выпадающего списка необходимые Вам Device (можно сразу несколько)
   - Для первого раза, можно не ставить галку в Commit Changes - по логу сможете увидеть, что будет добавлено на выбранные Device.
     В конце база данных откатит изменения.
     В дальнейшем, чтобы изменения принялись, необходимо ставить эту галку.

5. Запускаем скрипт, ожидаем, смотрим на финальный лог.

6. Заходим в Device, чтобы убедиться, что все компоненты соответствуют его Device Type.

На случай, если произойдет баг, при котором кол-во Console Ports, Power Ports не совпадает или вовсе уходит в отрицательное число:
- cd /opt/netbpx/netbox
- source /opt/netbox/venv/bin/activate
- python3 manage.py calculate_cached_counts (сбрасывает кэш)
- python3 manage.py reindex (пересчитывает созданные компоненты)

Обновляем страничку и видим, что информация корректна.

UPDATE 03.04.2025

Однако не совсем удобно запускать скрипт каждый раз вручную.

Самым простым способом автоматизации оказался способ с помощью Event Rules. Но данный способ требует изменения скрипта.

Порядок действий:
1. Добавляем новый скрипт через Web - main_w_event.py
2. Operations > Event Rules > Add
    - Имя
    - Object Types: печатаем Template и выбираем:
        DCIM | console port template
        DCIM | console server port template
        DCIM | interface template
        DCIM | power port template
        DCIM | module bay template
    - Event Types:
        Object created
        Object updated
        Object deleted
    - Type - Script
    - Script - Fix Device Components (main_w_event)
    - Action data:
         	{
                "commit": true
            }
    - Save

 Готово! Теперь скрипт будет автоматически срабатывать при указанных ивентах.