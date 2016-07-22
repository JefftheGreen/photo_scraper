#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone as tz
from datetime import datetime as dt
from tumblpy import Tumblpy
from scraping import models.photos
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

    # Scrape blog using tumblr api (tumblpy), creating photos
    #   all (bool):
    #       if True, get all posts since last scraping. if False, only scrape
    #       to a maximum depth
    #   max_depth (int):
    #       the maximum number of times to pull from the tumblr api. (20 posts
    #       are pulled at a time.) if all is True, this is irrelevant.
    def scrape(self, all=True, max_depth=10):
        # No maximum depth if scraping all posts
        max_depth = float('inf') if all else max_depth
        # Create the tumblpy agent
        agent = Tumblpy(TUMBLR_KEYS['consumer'], TUMBLR_KEYS['secret'])
        offset = 0
        posts = []
        # Pull 20 posts a max number of times equal to max_depth
        while offset < max_depth:
            # Get 20 posts
            new_posts = agent.get('posts', self.url,
                              params={'offset': offset * 20,
                                      'limit': 20,
                                      'notes_info': True})
            new_posts = new_posts['posts']
            # No posts found; stop scraping
            if not new_posts:
                break
            for post in new_posts:
                # if any of the new posts is from before last scraping, stop
                time = tz.make_aware(dt.fromtimestamp(post['timestamp']))
                if time < self.last_scraped:
                    offset = max_depth
                    break
            posts += new_posts
            offset += 1
        self.last_scraped = tz.now()
        # Create photos from posts
        for post in posts:
            photos = models.photos.Photo.from_tumblr_api(post, self)
            for photo_data in photos:
                photo = photo_data['photo']
                raw_tags = photo_data['raw tags']
                photo.save()
                photo.tags_from_ary(raw_tags)
