"""Visualization recipes for chapter five."""
from linear_algebra.catalog.chapter_05 import TOPICS
from .common import recipe_for_entry
RECIPES = tuple(recipe_for_entry(entry) for entry in TOPICS)
