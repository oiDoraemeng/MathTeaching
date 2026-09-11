"""Visualization recipes for chapter 4."""
from linear_algebra.catalog.chapter_04 import TOPICS
from .common import recipe_for_entry
RECIPES = tuple(recipe_for_entry(entry) for entry in TOPICS)
