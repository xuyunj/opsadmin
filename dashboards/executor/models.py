from django.db import models


class Task(models.Model):
    route_key = models.CharField(max_length=30)
    json_data = models.CharField(max_length=500)
    run_level = models.IntegerField(default=1)
    
    