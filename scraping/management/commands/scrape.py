#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
import re
from scraping.models import *
from datetime import datetime as dt
from django.utils import timezone as tz

class Command(BaseCommand):
    help = "Scrapes sources for content"

    def add_arguments(self, parser):
        parser.add_argument('-s', '--source', nargs="+", type=str)
        parser.add_argument('-r', '--reset', action='store_true')
        depth = parser.add_mutually_exclusive_group()
        depth.add_argument('-d', '--depth', type=int)
        depth.add_argument('-a', '--all', action='store_true')

    def handle(self, *args, **options):
        print(options)
        if options['source']:
            urls = [self.url_match(n)
                    for n in options['source']
                    if self.url_match(n) is not None]
            print(urls)
            sources_query = (Source.objects.filter(url__in=urls) |
                             Source.objects.filter(name__in=options['source']))
        else:
            sources_query = Source.objects.all()
        for source in sources_query:
            if options['reset']:
                print('Resetting scrape data for {}'.format(source.name))
                source.tz.make_aware(dt.fromtimestamp(0))
            print('Scraping posts from {}'.format(source.name))
            source.scrape(all=options['all'], max_depth=options['depth'])

    def url_match(self, string):
        tumblr_regex = '(http\:\/\/)?(?P<url>[A-Za-z0-9\-]+\.tumblr\.com).*'
        tumblr_url_match = re.fullmatch(tumblr_regex, string)
        if tumblr_url_match:
            return tumblr_url_match.group('url')
