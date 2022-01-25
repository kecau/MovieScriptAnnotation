from django.db import models
from django.utils import timezone

# Create your models here.

class user_data(models.Model):
    auth_user_pk = models.IntegerField(null=True)
    created_date = models.DateTimeField(default=timezone.now)
    updated_date = models.DateTimeField(blank=True, null=True)
    user_id = models.CharField(max_length=100)
    user_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    birth = models.CharField(max_length=100)
    gender = models.CharField(max_length=100)

class annotation(models.Model):
    created_date = models.DateTimeField(default=timezone.now)
    updated_date = models.DateTimeField(blank=True, null=True)
    user_id = models.CharField(max_length=100)
    annotation_key = models.IntegerField(null=True)
    movie_name = models.TextField(null=True)
    speaker = models.CharField(max_length=100)
    speech  = models.TextField(null=True)
    listener = models.CharField(max_length=100)