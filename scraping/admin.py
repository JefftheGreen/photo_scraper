#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.contrib import admin
from scraping.models import *

admin.site.register([Source, TumblrBlog, Photo, Tag, Word, WordAssociation])
