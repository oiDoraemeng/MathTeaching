"""Visualization recipes for chapter five."""
from linear_algebra.catalog.runtime_manifest import CHAPTER_5_TOPICS as TOPICS
from .common import recipe_for_entry
RECIPES = tuple(recipe_for_entry(entry) for entry in TOPICS)
