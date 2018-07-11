# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# dummy models to be used during tests

class ModelA(models.Model):
    name = models.CharField(max_length=8)

class ModelB(models.Model):
    name = models.CharField(max_length=8)

class ModelC(models.Model):
    name = models.CharField(max_length=8)

class ModelD(models.Model):
    name = models.CharField(max_length=8)

class ModelE(models.Model):
    name = models.CharField(max_length=8)

class ModelF(models.Model):
    name = models.CharField(max_length=8)

class ModelG(models.Model):
    name = models.CharField(max_length=8)