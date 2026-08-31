"""Visualization recipes for chapter 3, kept in lecture order."""

from linear_algebra.catalog.chapter_03 import TOPICS

from .common import VisualizationRecipe, recipe_for_entry

RECIPES: tuple[VisualizationRecipe, ...] = tuple(recipe_for_entry(entry) for entry in TOPICS)
