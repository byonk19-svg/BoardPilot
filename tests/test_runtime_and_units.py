from woodwork.runtime import classify_runtime_failure
from woodwork.exports.dimensions import format_dual

def test_blocked_native_kernel_explains_supported_fallback():
    result = classify_runtime_failure('ImportError: DLL load failed while importing OCP', platform='win32')
    assert result['code'] == 'NATIVE_KERNEL_LOAD_REFUSED'
    assert 'WSL' in result['guidance']
    assert 'turn off' not in result['guidance'].lower()

def test_dual_units_convert_actual_measurement_and_mark_approximation():
    assert format_dual('25.4') == '1 in (25.4 mm)'
    assert format_dual('726').startswith('approx. ')
    assert '(726 mm)' in format_dual('726')
