"""Presentation conversions never feed rounded values back into the ledger."""
from fractions import Fraction
import re


def format_dual(value_mm: str, denominator: int = 64) -> str:
    inches = Fraction(value_mm) / Fraction('25.4')
    numerator = round(inches * denominator)
    rounded = Fraction(numerator, denominator)
    whole, remainder = divmod(rounded.numerator, rounded.denominator)
    fraction = f'{remainder}/{rounded.denominator}' if remainder else ''
    inch_text = f'{whole} {fraction}'.strip() if whole else (fraction or '0')
    prefix = '' if rounded == inches else 'approx. '
    return f'{prefix}{inch_text} in ({value_mm} mm)'


def schedule_formatting(spec: dict) -> dict:
    """The application schedule policy; native CAD sheets remain metric."""
    return {'units': spec['documents']['schedule_units'],
            'fraction_denominator': spec['display']['fraction_denominator']}


def format_schedule(value_mm: str, policy: dict) -> str:
    if policy['units'] == 'mm':
        return f'{value_mm} mm'
    if policy['units'] != 'dual' or policy['fraction_denominator'] not in (16, 32, 64):
        raise ValueError('Unsupported schedule formatting policy.')
    return format_dual(value_mm, policy['fraction_denominator'])


def saved_schedule_formatting(inputs: dict, spec: dict, kind: str) -> dict:
    """Read the saved renderer contract, including its historical dual-64 policy."""
    from woodwork.cad_adapter.verifier import require

    require(kind in ('documents', 'stock'), 'Unknown schedule renderer kind')
    field = 'documents_version' if kind == 'documents' else 'stock_export_version'
    for _ in range(20):
        require(isinstance(inputs, dict), 'Malformed schedule formatting provenance')
        if field in inputs:
            break
        inputs = inputs.get('source_inputs', inputs.get('geometry_inputs', {}))
    require(field in inputs, 'Missing schedule renderer version')
    legacy = ('1.0.0',) if kind == 'documents' else ('1.0.0', '1.0.1')
    if inputs[field] in legacy:
        # These renderers always emitted dual units with 64ths, regardless of
        # the preferences saved in their source spec. Check their actual output.
        return {'units': 'dual', 'fraction_denominator': 64}
    require(inputs[field] == '1.1.0', 'Unsupported schedule renderer version')
    expected = schedule_formatting(spec)
    require(inputs.get('schedule_formatting') == expected, 'Schedule formatting differs from immutable revision')
    if kind == 'documents':
        renderers = inputs.get('renderer_sha256')
        require(isinstance(renderers, dict), 'Schedule formatter provenance missing')
        digest = renderers.get('dimensions')
    else:
        digest = inputs.get('dimension_formatter_sha256')
    require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest) is not None,
            'Schedule formatter provenance missing')
    return expected
