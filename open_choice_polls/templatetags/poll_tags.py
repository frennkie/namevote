# -*- coding: utf-8 -*-

from django import template
register = template.Library()


@register.simple_tag
def percentage(question, item):
    if question.total_votes > 0:
        return float(item.votes) / float(question.total_votes) * 100
