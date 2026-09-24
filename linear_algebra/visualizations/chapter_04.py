"""Visualization recipes for chapter 4."""
from linear_algebra.catalog.runtime_manifest import CHAPTER_4_TOPICS as TOPICS
from .common import recipe_for_entry
RECIPES = tuple(recipe_for_entry(entry) for entry in TOPICS)
