#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone as tz
from datetime import datetime as dt
from tumblpy import Tumblpy
from tumblpy.exceptions import TumblpyError
from api_keys import TUMBLR as TUMBLR_KEYS


class Source(models.Model):

    # The human-readable name of the source
    name = models.CharField(max_length=200, default='')
    # The url of the source. E.g. the blog url for a tumblr blog
    url = models.URLField(default='', max_length=200, unique=True)
    # Datetime last scraped. Defaults to epoch so that all photos will be
    # scraped.
    last_scraped = models.DateTimeField(default=tz.make_aware(
        dt.fromtimestamp(0)))
    # The human-readable description of the source.
    description = models.TextField(default='')


class TumblrBlog(Source):

    # The 512 px url of the avatar
    avatar_url = models.URLField(default='', max_length=200)

    # Returns an instance based on information pulled from the Tumblr API
    # (tumblpy). Does not save to database.
    #   name (str):
    #       the name of the blog (i.e. the part before '.tumblr.com') OR the url
    #       of the blog (including '.tumblr.com').
    @classmethod
    def from_api(cls, name):
        # Create tumblpy agent
        agent = Tumblpy(TUMBLR_KEYS['consumer'], TUMBLR_KEYS['secret'])
        try:
            # Get blog info
            info = agent.get('info', name)['blog']
            # Get avatar
            avatar = agent.get('avatar', name, params={'size': 512})
        except TumblpyError:
            raise TumblpyError('Could not connect to {}'.format(name +
                                                                '.tumblr.com'))
        # Create TumblrBlog
        instance = cls()
        # Assign fields
        instance.url = info['url']
        instance.name = info['title']
        instance.description = info['description']
        instance.avatar_url = avatar['url']
        # Return without saving to db
        return instance
