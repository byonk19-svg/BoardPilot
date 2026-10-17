"""Declared-price sheet and pack arithmetic; missing prices remain unknown."""
from decimal import Decimal,localcontext
from fractions import Fraction
import re

from .common import mm,require


def price_value(value):
    require(isinstance(value,str) and re.fullmatch(r'(?:0|[1-9][0-9]*)\.[0-9]{2}',value),'Use an explicit canonical USD price with two decimal places.')
    return Fraction(Decimal(value))


def money(value):
    """Exact rational HALF_EVEN to integer cents, independent of Decimal precision."""
    scaled=Fraction(value)*100;sign=-1 if scaled<0 else 1;scaled=abs(scaled)
    whole,remainder=divmod(scaled.numerator,scaled.denominator)
    if remainder*2>scaled.denominator or (remainder*2==scaled.denominator and whole%2):whole+=1
    with localcontext() as context:
        context.prec=max(80,int(whole.bit_length()*.30103)+100)
        return format(Decimal(sign*whole).scaleb(-2),'.2f')


def hardware_purchase(required_count,pack_size,pack_price_usd):
    require(type(required_count) is int and required_count>=0 and type(pack_size) is int and pack_size>0,'Hardware counts require nonnegative units and a positive explicit pack size.')
    count=(required_count+pack_size-1)//pack_size
    return {'required_count':required_count,'pack_size':pack_size,'packs_purchased':count,'supplied_count':count*pack_size,
            'pack_price_usd':pack_price_usd,'purchase_cost_usd':None if pack_price_usd is None else money(price_value(pack_price_usd)*count)}


def calculate_costs(plan,spec,resolved):
    stocks={s['stock_id']:s for s in spec['manufacturing']['stock_sheets']}
    definitions={p['definition_id']:p for p in resolved['part_definitions']}
    finished={instance['instance_id']:definitions[instance['definition_id']]['finished_mm'] for instance in resolved['part_instances']}
    rows=[];known=Fraction(0);unknown=[]
    for count in plan['stock_counts']:
        stock=stocks[count['stock_id']];price=stock['unit_price'];quantity=count['sheet_count']
        instances=[leaf['instance_id'] for sheet in plan['sheets'] if sheet['stock_id']==stock['stock_id'] for leaf in sheet['leaf_regions'] if leaf['kind']=='part']
        face_area=sum((mm(finished[identifier]['length_mm'])*mm(finished[identifier]['width_mm']) for identifier in instances),Fraction(0))
        original_area=mm(stock['length_mm'])*mm(stock['width_mm'])
        if price is None:purchased=consumed=None;unknown.append(stock['stock_id'])
        else:
            unit=price_value(price);purchased=money(unit*quantity);consumed=money(unit*face_area/original_area);known+=unit*quantity
        rows.append({'stock_id':stock['stock_id'],'material_id':stock['material_id'],'sheets_purchased':quantity,'unit_price_usd':price,'purchased_cost_usd':purchased,'consumed_finished_value_usd':consumed})
    complete=plan['status']=='complete' and not unknown
    return {'scope':'sheet_purchase','currency':'USD','rows':rows,'known_sheet_subtotal_usd':money(known),
            'sheet_purchase_subtotal_usd':money(known) if complete else None,'sheet_prices_complete':not unknown,'estimate_complete':complete,
            'unknown_price_stock_ids':unknown,'project_total_usd':None,'excluded_items':['hardware','finish','tax','shipping','tools'],
            'consumed_allocation_method':'finished_face_area / original_sheet_face_area','rounding':'HALF_EVEN to USD cents'}
