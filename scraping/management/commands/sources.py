#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
import re
from scraping.models import *
from datetime import datetime as dt
from django.utils import timezone as tz
from tumblpy import Tumblpy
from api_keys import *
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
    help = "Scrapes sources for content"

    def add_arguments(self, parser):
        parser.add_argument('-a', '--add', nargs="+", type=str)
        parser.add_argument('-r', '--remove', nargs="*", type=str)
        parser.add_argument('-i', '--info', nargs="*", type=str)

    def handle(self, *args, **options):
        if options['add']:
            self.add(options['add'])
        if options['info'] is not None:
            self.info(options['info'])
        if options['remove'] is not None:
            self.remove(options['remove'])

    def add(self, sources):
        for source_string in sources:
            source_url = self.get_url(source_string)
            if source_url:
                tumblr_blog = source_url['type'].from_api(source_url['url'])
                try:
                    tumblr_blog.save()
                    print('Added Tumblr blog {}'.format(tumblr_blog.name))
                except IntegrityError:
                    try:
                        source = Source.objects.get(url=source_url['url'])
                        print('{} has already been added.'.format(
                           source.name))
                    except ObjectDoesNotExist:
                        raise

    def remove(self, sources):
        if sources:
            for source_string in sources:
                source_url = self.get_url(source_string)['url']
                if source_url:
                    if TumblrBlog.objects.filter(url=source_url).exists():
                        blog = TumblrBlog.objects.get(url=source_url)
        else:
            [self.delete_blog(b) for b in TumblrBlog.objects.all()]

    def delete_blog(self, blog):
        name = blog.name
        confirm = input("Delete {}? (yes/no)\n\t".format(name))
        if confirm == 'yes':
            blog.delete()
            print('Deleted Tumblr blog {}\n'.format(name))

    def info(self, sources):
        if sources:
            for source_string in sources:
                source_url = self.get_url(source_string)['url']
                if source_url:
                    if TumblrBlog.objects.filter(url=source_url).exists():
                        blog = TumblrBlog.objects.get(url=source_url)
                        self.print_info(blog)
        else:
            [self.print_info(b) for b in TumblrBlog.objects.all()]

    def print_info(self, blog):
        print('\nName:\t\t', blog.name, '\nURL:\t\t', blog.url,
              '\nLast scraped:\t', blog.last_scraped,
              '\nDescription:\t', blog.description, '\nPhotos:\t\t',
              Photo.objects.filter(source=blog).count(), '\n')

    def get_url(self, string):
        # Check if it matches a tumblr url pattern
        tumblr_url_regex = '(?P<url>(http\:\/\/)?[A-Za-z0-9\-]+\.tumblr\.com).*'
        tumblr_url_match = re.fullmatch(tumblr_url_regex, string)
        if tumblr_url_match:
            return {'type': TumblrBlog, 'url': tumblr_url_match}
        # Check if it matches a tumblr name pattern
        tumblr_name_regex = '[A-Za-z0-9\-]+'
        tumblr_name_match = re.fullmatch(tumblr_name_regex, string).string
        # Check if a tumblr blog with that name exists
        if tumblr_name_match:
            tumblr_agent = Tumblpy(TUMBLR['consumer'], TUMBLR['secret'])
            try:
                tumblr_agent.get('info', tumblr_name_match)
                # tumblpy didn't throw an exception, so blog exists
                return {'type': TumblrBlog,
                        'url': 'http://' + tumblr_name_match + '.tumblr.com/'}
            except TumblpyError:
                # tumblpy did throw an exception, so blog doesn't exist.
                pass



