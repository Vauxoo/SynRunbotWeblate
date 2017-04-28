# SynRunbotWeblate
This script synchronize the runbot and weblate

### The file synchronize.cfg is the configuration of the script

##### The secction [odoo]
```ini
[odoo]  # The information of the runbot installation
url = http://demo.odoo.com
db = openerp_test
username = admin
password = admin
```

##### The secction [docker]
```ini
[docker]  # The name of the container of weblate (This section is optional)
name = weblatedocker_weblate_1
```
