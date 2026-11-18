# seed-django-kit

Wiederverwendbares Demo-Seeding-Framework (`manage.py seed_demo`) mit Auto-Discovery von `<app>/seeders.py`.

## Installation
```bash
pip install --no-user --upgrade --no-cache-dir git+https://github.com/bzaiser/seed-django-kit.git@main
```

```python
# myapp/seeders.py
from seed_kit.registry import register_seeder

def seed_items(count=10):
    ...

def reset_items():
    Item.objects.all().delete()

register_seeder("items", seed_items, order=10, reset_fn=reset_items)
```

```bash
python manage.py seed_demo --reset --count 25
```
