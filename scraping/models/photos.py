#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone as tz
from datetime import datetime as dt
from scraping.models import Source
from collections import defaultdict
from nltk import pos_tag
import re


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
    # Ngrams from the title and caption
    ngrams = models.ManyToManyField('ngram')

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
            # Remove characters other than letters and spaces and make lowercase
            raw_tag = re.sub(r'[^a-zA-Z ]+', '', raw_tag).lower()
            # If the tag exists, get it
            if Tag.objects.filter(tag_str=raw_tag).exists():
                tag = Tag.objects.get(tag_str=raw_tag)
            # If it doesn't, make it
            else:
                tag = Tag(tag_str=raw_tag)
                tag.save()
                tag.make_words()
            self.tags.add(tag)

    def get_words(self):
        # TODO: Make it skip most common words
        words = defaultdict(lambda: 0)
        # Split caption and label parts of speech with NLTK
        for word_str, tag in pos_tag(self.caption.split(), tagset='universal'):
            # Only use adjectives, adverbs, nouns, verbs, and unknown
            if tag in ['ADJ', 'ADV', 'NOUN', 'VERB', 'X']:
                # Remove HTMl tags
                word_str = re.sub('<[^>]*>', '', word_str)
                # Remove non-letter characters
                word_str = re.sub('[^a-zA-Z]+', '', word_str).lower()
                # Increment count of word
                words[word_str] += 1
        for tag in self.tags.all():
            for word in tag.words.all():
                words[word.word_str] += 1
        for word_str, strength in words.items():
            # If word exists, get it
            if Word.objects.filter(word_str=word_str).exists():
                word = Word.objects.get(word_str=word_str)
            # If it doesn't, make it
            else:
                word = Word(word_str=word_str)
                word.save()
            # If word association exists, get it and change strength
            if WordAssociation.objects.filter(word=word, photo=self).exists():
                association = WordAssociation.objects.get(word=word, photo=self)
                association.strength = strength
                association.save()
            # If it does, make it with appropriate strength
            else:
                association = WordAssociation(word=word, photo=self,
                                              strength=strength)
                association.save()

    def make_ngrams(self, max_size=3):
        # Ngrams are just words if they're not at least two words long
        if max_size < 2:
            raise AttributeError('max_size must be >= 2')
        # Make sure we actually have words for this photo
        self.get_words()
        # Make ngrams from each tag
        for tag in self.tags.all():
            self.make_ngrams_from_str(tag.tag_str, max_size)
        # Remove HTML characters from caption
        clean_caption = re.sub(r'<[^>]*>', '', self.caption)
        # Remove characters that aren't letters or spaces and make lower case
        clean_caption = re.sub(r'[^a-zA-Z ]+', '', clean_caption).lower()
        self.make_ngrams_from_str(clean_caption, max_size)

    def make_ngrams_from_str(self, str, max_size):
        split_str = str.split()
        # No point making an ngram from a single word
        if len(split_str) > 1:
            # Start with smallest ngrams, length 2
            size = 2
            # Stop once we're at the maximum size or the number of words in the
            # string.
            while size <= max_size and size <= len(split_str):
                # The ngram is the whole string
                if size == len(split_str):
                    # TODO: Make it find Ngram if already exists
                    ngram = Ngram.from_str(str)
                    self.ngrams.add(ngram)
                else:
                    # Move down the string one word at a time, stopping when
                    # the ngram would go past the end of the string
                    for i in range(0, len(split_str) - size + 1):
                        words = split_str[i:i + size]
                        # Turn words back into string
                        words = ' '.join(words)
                        ngram = Ngram.from_str(words)
                        self.ngrams.add(ngram)
                size += 1


class Tag(models.Model):

    tag_str = models.CharField(max_length=50, unique=True)
    words = models.ManyToManyField('word')

    def __str__(self):
        return self.tag_str

    def make_words(self):
        if self.words.all().count() == 0:
            for tag_word in self.tag_str.split(' '):
                if Word.objects.filter(word_str=tag_word).exists():
                    word = Word.objects.get(word_str=tag_word)
                else:
                    word = Word(word_str=tag_word)
                    word.save()
                self.words.add(word)


class Word(models.Model):

    word_str = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.word_str


class Ngram(models.Model):

    words = models.ManyToManyField(Word, through='NgramAssociation')
    expression = models.CharField(max_length=500, default='')

    def __str__(self):
        return self.expression

    @classmethod
    def from_str(cls, str):
        # Make the ngram
        ngram = cls()
        ngram.save()
        split_str = str.split()
        # Every word position in string. Using range because we need the order
        for w in range(0, len(split_str)):
            # Get word if it exists
            if Word.objects.filter(word_str=split_str[w]).exists():
                word = Word.objects.get(word_str=split_str[w])
            # Make it if it doesn't
            else:
                word = Word(word_str=split_str[w])
                word.save()
            # Make association
            association = NgramAssociation(word=word, ngram=ngram, order=w)
            association.save()
        # Update the expression of the ngram
        ngram.update_expression()
        return ngram

    def update_expression(self):
        # Each word in order separated by spaces
        self.expression = ' '.join([str(a.word) for a in
                                    NgramAssociation.objects.filter(
                                        ngram=self)])
        self.save()


class WordAssociation(models.Model):

    photo = models.ForeignKey(Photo)
    word = models.ForeignKey(Word)
    strength = models.PositiveIntegerField(default=1)


class NgramAssociation(models.Model):

    class Meta:
        ordering = ['order']

    word = models.ForeignKey(Word)
    ngram = models.ForeignKey(Ngram)
    order = models.IntegerField()