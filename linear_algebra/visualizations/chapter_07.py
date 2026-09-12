from linear_algebra.catalog.chapter_07 import TOPICS
from .common import recipe_for_entry
from dataclasses import replace
RECIPES = tuple(replace(recipe_for_entry(entry), scene='3d') if entry.id == 'ch07.gram-schmidt' else recipe_for_entry(entry) for entry in TOPICS)
