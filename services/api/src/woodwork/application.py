"""Compose deterministic geometry with installed construction rules."""
from copy import deepcopy
from woodwork.domain import compile_project, validate_spec, resolved_hash, hash_json, canonical_json


def apply_manufacturing_plan(resolved, plan, recipe_fingerprint):
    """Group interchangeable blanks using their complete planned local operations."""
    groups={}
    for definition in resolved['part_definitions']:
        patterns={canonical_json(plan.get(i,[])) for i in definition['member_instance_ids']}
        if len(patterns)!=1:
            raise ValueError('One maintained manufacturing definition requires one operation pattern.')
        operations=deepcopy(plan.get(definition['member_instance_ids'][0],[]))
        definition['planned_recipe_operations']=operations
        attributes=definition['manufacturing_attributes']
        attributes.update(planned_recipe_operations=operations,recipe_fingerprint=recipe_fingerprint)
        fingerprint=hash_json(attributes)
        definition.update(manufacturing_fingerprint=fingerprint,manufacturing_sha256=fingerprint)
        group=groups.get(fingerprint)
        if group is None:
            group=deepcopy(definition)
            group.update(group_id=fingerprint,definition_ids=[definition['definition_id']])
            groups[fingerprint]=group
        else:
            group['quantity']+=definition['quantity']
            group['member_instance_ids'].extend(definition['member_instance_ids'])
            group['definition_ids'].append(definition['definition_id'])
    resolved['cut_groups']=list(groups.values())
    return resolved


def installed_recipes():
    from woodwork.recipes import installed_catalog
    return installed_catalog()


def compile_design(value,*,recipe_catalog=None):
    spec=validate_spec(value)
    if spec.construction.recipe is None:
        return compile_project(spec)
    catalog=installed_recipes() if recipe_catalog is None else recipe_catalog
    resolved=compile_project(spec,recipe_catalog=catalog)
    from woodwork.recipes import resolve_recipe, manufacturing_plan
    result=resolve_recipe(resolved['spec'],resolved,catalog=catalog)
    status=result['status'].removeprefix('recipe_')
    resolved['construction_recipe']=result
    resolved['construction_status']='recipe_'+status
    resolved['construction'].update(status=resolved['construction_status'],findings=result.get('findings',[]),technical_completeness=status=='complete',physical_review='not_recorded')
    resolved['construction']['fingerprint']=result.get('fingerprint')
    apply_manufacturing_plan(resolved,manufacturing_plan(resolved['spec'],resolved,result),result.get('fingerprint'))
    resolved['resolved_sha256']=resolved_hash(resolved)
    return resolved
