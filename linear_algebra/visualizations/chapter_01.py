"""Visualization recipes for chapter 1, kept in lecture order."""

from linear_algebra.catalog.chapter_01 import TOPICS

from .common import VisualizationRecipe, recipe_for_entry

RECIPES: tuple[VisualizationRecipe, ...] = tuple(recipe_for_entry(entry) for entry in TOPICS)
