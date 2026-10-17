"""Keep optional Windows metadata discovery out of contained CAD execution."""
import os
import platform


def configure_native_platform():
    if os.name == 'nt':
        # Python 3.13 tries WMI before its PROCESSOR_* environment fallback.
        # WMI can stall in a contained worker. These workers receive the two
        # approved architecture variables; CAD does not require WMI services.
        platform._wmi = None
