from django.db import models

# Create your models here.

class Metric(models.Model):
    application_name = models.CharField(max_length=50)
    response_time = models.FloatField()          
    request_count = models.IntegerField(default=0)  
    error_count = models.IntegerField(default=0)    
    timestamp = models.DateTimeField(auto_now_add=True)  

    def __str__(self):
        return f"{self.application_name} - {self.response_time} second"
