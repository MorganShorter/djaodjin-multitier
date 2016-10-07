# Copyright (c) 2015, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Models for the multi-tier application.
"""

import string

from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils._os import safe_join
from django.utils.translation import ugettext_lazy as _

from . import settings
from .utils import get_site_model


def domain_name_validator(value):
    """
    Validates that the given value contains no whitespaces to prevent common
    typos.
    """
    if not value:
        return
    checks = ((s in value) for s in string.whitespace)
    if any(checks):
        raise ValidationError(
            _("The domain name cannot contain any spaces or tabs."),
            code='invalid',
        )

class Site(models.Model):

    domain = models.CharField(null=True, blank=True, max_length=100,
        help_text='fully qualified domain name at which the site is available',
        validators=[domain_name_validator, RegexValidator(
            r'[a-z0-9][a-z0-9\-]*(\.[a-z0-9\-])+',
            "Enter a valid 'domain', ex: example.com", 'invalid')])
    slug = models.SlugField(unique=True,
        help_text="unique identifier for the site")
    subdomain = models.SlugField(
        # Not unique since it will always be '' for base.
        help_text="subdomain of the platform on which the site is available")
    db_name = models.SlugField(null=True,
       help_text='name of database to connect to for the site')
    db_host = models.CharField(max_length=255, null=True,
       help_text='host to connect to to access the database')
    db_port = models.IntegerField(null=True,
       help_text='port to connect to to access the database')
    theme = models.SlugField(null=True,
       help_text='alternative search name for finding templates')
    base = models.ForeignKey('multitier.Site', null=True,
       help_text='The site is a derivative of this parent.')
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, related_name='sites', null=True)
    is_active = models.BooleanField(default=False)
    is_path_prefix = models.BooleanField(default=False)
    tag = models.CharField(null=True, max_length=255)

    class Meta:
        swappable = 'MULTITIER_SITE_MODEL'

    def __unicode__(self): #pylint: disable=super-on-old-class
        return unicode(self.slug)

    def as_base(self):
        """
        Returns either the base site or ``self`` if no base exists.
        """
        if self.base_id:
            return self.base
        return self

    def as_subdomain(self):
        if self.subdomain:
            return self.subdomain
        return self.slug

    @property
    def is_alias(self):
        #pylint:disable=no-member
        return self.base_id and self.subdomain == self.base.slug

    @property
    def printable_name(self):
        if self.subdomain:
            return self.subdomain
        return self.slug

    def get_templates(self):
        """
        Returns a list of candidate themes.
        """
        if self.theme:
            result = [self.theme, self.slug]
        else:
            result = [self.slug]
        if self.subdomain:
            result += [self.subdomain]
        return result

    def get_template_dirs(self):
        """
        Returns a list of candidate search paths for templates.
        """
        return [safe_join(theme_dir, theme, 'templates')
                for theme_dir in settings.THEMES_DIRS
                    for theme in self.get_templates()]


def get_site_or_none(subdomain):
    """
    Returns a ``Site`` instance based on its subdomain while prefering
    ``Site`` with an explicit domain.
    If no Site could be found, then returns ``None``.
    """
    return get_site_model().objects.filter(
        subdomain=subdomain).order_by('-domain', '-pk').first()
