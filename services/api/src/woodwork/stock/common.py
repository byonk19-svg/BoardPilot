"""Exact rectangle records shared by layout generation and independent replay."""
from dataclasses import dataclass
from fractions import Fraction
import re

from woodwork.domain import exact_decimal, finding


class StockError(ValueError):
    def __init__(self,findings):
        self.findings=findings
        self.code=findings[0]['code']
        super().__init__(findings[0]['message'])


def require(condition,message,code='STOCK_PLAN_INVALID',field='stock_plan',**details):
    if not condition:raise StockError([finding(code,message,field,**details)])


def mm(value):
    require(isinstance(value,str) and re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]{0,5}[1-9])?',value),'Use canonical nonnegative millimeters.')
    return Fraction(value)


@dataclass(frozen=True)
class Rectangle:
    x:Fraction
    y:Fraction
    length:Fraction
    width:Fraction

    @property
    def area(self):return self.length*self.width
    def record(self):return dict(zip(('x_mm','y_mm','length_mm','width_mm'),map(exact_decimal,(self.x,self.y,self.length,self.width)),strict=True))
    @classmethod
    def read(cls,record):return cls(*(mm(record[key]) for key in ('x_mm','y_mm','length_mm','width_mm')))


def split_rectangle(rect,axis,start,kerf):
    """Pure partition arithmetic. The validator separately checks active tree state."""
    if axis=='x':
        return Rectangle(rect.x,rect.y,start-rect.x,rect.width),Rectangle(start,rect.y,kerf,rect.width),Rectangle(start+kerf,rect.y,rect.x+rect.length-start-kerf,rect.width)
    if axis=='y':
        return Rectangle(rect.x,rect.y,rect.length,start-rect.y),Rectangle(rect.x,start,rect.length,kerf),Rectangle(rect.x,start+kerf,rect.length,rect.y+rect.width-start-kerf)
    require(False,'Unknown cut axis.')


def part_input(part):
    identifier=part.get('id',part.get('instance_id'))
    require(isinstance(identifier,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,99}',identifier),'Invalid physical part identity.')
    length,width=mm(part['length_mm']),mm(part['width_mm'])
    require(length>0 and width>0,'Part blanks must be positive.')
    grain=part.get('grain_axis','length')
    require(grain in ('L','length','none'),'Unknown part grain policy.')
    return {'id':identifier,'length':length,'width':width,'grain':grain,'material_id':part.get('material_id','test'),'thickness_mm':part.get('thickness_mm')}


def expanded_parts(resolved):
    definitions={p['definition_id']:p for p in resolved['part_definitions']}
    return [{'id':instance['instance_id'],'material_id':definitions[instance['definition_id']]['material_id'],
             **definitions[instance['definition_id']]['rough_mm'],'grain_axis':definitions[instance['definition_id']]['grain_axis']}
            for instance in resolved['part_instances']]
