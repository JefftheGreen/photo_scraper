#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone as tz
from datetime import datetime as dt
from tumblpy import Tumblpy
from tumblpy.exceptions import TumblpyError
from api_keys import TUMBLR as TUMBLR_KEYS


class Photo(models.Model):

    # The url of the photo post or page.
    post_url = models.URLField(max_length=200, default='')
    # The url of the photo itself.
    photo_url = models.URLField(max_length=200, default='', unique=True)
    # The date the photo was posted
    posted = models.DateTimeField(null=True, default=None)
    # The title of the photo
    title = models.CharField(max_length=200, default='')
    # The photo's descriptive caption
    caption = models.TextField(default='')
    # The number of times the photo was liked by users of the source
    likes = models.PositiveIntegerField(default=0)
    # Any tags assigned to the photo at the source
    tags = models.ManyToManyField('tag')
    # Words from the title and caption, excluding most common ones.
    associated_words = models.ManyToManyField('word', through='WordAssociation')
    # Whether the photo has been deleted by the user. Data is still stored,
    # but not used in analysis or shown
    deleted = models.BooleanField(default=False)
    # A rating between 0 and 5 given by the user
    rating = models.IntegerField(default=0)


class Tag(models.Model):

    tag = models.CharField(max_length=50)
    word = models.ForeignKey('word', default=None)

    def __str__(self):
        return self.tag


class Word(models.Model):

    word = models.CharField(max_length=50)

    def __str__(self):
        return self.word


class WordAssociation(models.Model):

    photo = models.ForeignKey(Photo)
    word = models.ForeignKey(Word)
    strength = models.PositiveIntegerField(default=1)

