#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone as tz
from datetime import datetime as dt
from scraping.models import Source


class Photo(models.Model):

    # The source the photo came from
    source = models.ForeignKey(Source, null=True)
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

    # Returns instances based on information pulled from the Tumblr API
    # (tumblpy). Does not save to database.
    #   post (str):
    #       the post, a dictionary derived from tumblpy.
    #       Must have notes info.
    #       Via e.g. t.get('posts',
    #                      'blogname',
    #                      params={'notes_info': True})['posts'][0]
    #   source (Source):
    #       the source the post is derived from. must have been saved to the db.
    # Returns an array of dictionaries. Each dict is of the form
    # {'photo': Photo, 'raw tags': tags} where tags is an array of strings.
    # Tags must be created and saved after saving the Photo instance to the db.
    @classmethod
    def from_tumblr_api(cls, post, source):
        photos = []
        if post['type'] != 'photo':
            return photos
        post_url = post['post_url']
        posted = tz.make_aware(dt.fromtimestamp(post['timestamp']))
        post_caption = post['caption']
        tags = post['tags']
        likes = len([n for n in post['notes'] if n['type'] == 'like'])
        for photo in post['photos']:
            # Create Photo
            instance = cls()
            # Set instance variables
            instance.post_url = post_url
            instance.photo_url = photo['original_size']['url']
            instance.posted = posted
            # Single photos don't have individual captions, use post caption
            if photo['caption'] != '':
                instance.caption = photo['caption']
            else:
                instance.caption = post_caption
            instance.likes = likes
            instance.source = source
            photos.append({'photo': instance, 'raw tags': tags})
        return photos

    # Creates, saves, and assigns Tag instances to self.tags
    def tags_from_ary(self, tags):
        for raw_tag in tags:
            if Tag.objects.filter(tag=raw_tag).exists():
                tag = Tag.objects.get(tag=raw_tag)
            else:
                tag = Tag(tag=raw_tag)
                tag.save()
                tag.make_word()
            self.tags.add(tag)


class Tag(models.Model):

    tag = models.CharField(max_length=50, unique=True)
    word = models.OneToOneField('word', default=None)

    def __str__(self):
        return self.tag

    def make_word(self):
        if self.word:
            pass
        else:
            word = Word(word=self.tag)
            word.save()
            self.word = word
            self.save()


class Word(models.Model):

    word = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.word


class WordAssociation(models.Model):

    photo = models.ForeignKey(Photo)
    word = models.ForeignKey(Word)
    strength = models.PositiveIntegerField(default=1)

