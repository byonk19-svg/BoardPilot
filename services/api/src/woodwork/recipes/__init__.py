from .catalog import RECIPE_ID, RECIPE_VERSION, installed_catalog, public_catalog
from .graph import build_recipe_graph as legacy_build, resolve_recipe as legacy_resolve, validate_recipe_graph as legacy_validate
from .planning import manufacturing_plan as legacy_plan
from .beginner_catalog import BEGINNER_ID


def build_recipe_graph(entry,spec,resolved):
    if entry['recipe_id']==BEGINNER_ID:
        from .beginner import build_recipe_graph as build
        return build(entry,spec,resolved)
    return legacy_build(entry,spec,resolved)


def resolve_recipe(spec,resolved,**options):
    selection=spec['construction']['recipe']
    if selection and selection['id']==BEGINNER_ID:
        from .beginner import resolve_recipe as resolve
        return resolve(spec,resolved,**options)
    return legacy_resolve(spec,resolved,**options)


def validate_recipe_graph(graph,resolved,**options):
    selection = resolved['spec']['construction']['recipe']
    if (selection and selection['id'] == BEGINNER_ID) or graph.get('recipe_id') == BEGINNER_ID:
        from .beginner import validate_recipe_graph as validate
        return validate(graph,resolved,**options)
    return legacy_validate(graph,resolved,**options)


def manufacturing_plan(spec,resolved,recipe):
    if recipe.get('recipe_id')==BEGINNER_ID:
        from .beginner import manufacturing_plan as plan
        return plan(spec,resolved,recipe)
    return legacy_plan(spec,resolved,recipe)

__all__ = ["RECIPE_ID", "RECIPE_VERSION", "installed_catalog", "public_catalog", "build_recipe_graph", "resolve_recipe", "validate_recipe_graph", "manufacturing_plan"]
