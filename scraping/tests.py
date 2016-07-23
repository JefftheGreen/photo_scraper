#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.test import TestCase
from django.utils import timezone as tz
from scraping.models import *

BLOG_NAME = ''
BlOG_TITLE = ''
AVATAR_URL = ''
BlOG_DESCRIPTION = ''''''


class EffectTest(TestCase):
    def setUp(self):
        blog = TumblrBlog.from_api(BLOG_NAME)
        blog.save()
        blog.scrape(all=False, max_depth=5)


    def test_blog(self):
        blog = Source.objects.get(name=BLOG_NAME)
        assert blog.url == BLOG_NAME + '.tumblr.com'
        assert blog.name == BlOG_TITLE
        assert blog.last_scraped < tz.now()
        assert blog.description == BlOG_DESCRIPTION
        assert blog.avatar_url == AVATAR_URL

    def test_photos(self):
        #assert len(Photo.objects.all()) == 100
        assert Tag.objects.all().exists()
        assert Word.objects.all().exists()
