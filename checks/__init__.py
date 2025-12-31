"""
CIS VMware ESXi 8 Benchmark Checks Modules
"""

from .base import (
    check_2_4_for_host, fix_2_4_for_host,
    check_2_10_for_host, fix_2_10_for_host
)

from .management import (
    check_3_3_for_host, fix_3_3_for_host,
    check_3_7_for_host, fix_3_7_for_host,
    check_3_8_for_host, fix_3_8_for_host,
    check_3_9_for_host, fix_3_9_for_host,
    check_3_12_for_host, fix_3_12_for_host,
    check_3_13_for_host, fix_3_13_for_host
)

from .logging import (
    check_4_2_for_host, fix_4_2_for_host
)

from .network import (
    check_5_6_for_host, fix_5_6_for_host,
    check_5_7_for_host, fix_5_7_for_host,
    check_5_8_for_host, fix_5_8_for_host,
    check_5_9_and_5_10_for_host, fix_5_9_and_5_10_for_host
)

from .virtual_machine import (
    check_7_6_for_host, fix_7_6_for_host,
    check_7_21_for_host, fix_7_21_for_host,
    check_7_22_for_host, fix_7_22_for_host,
    check_7_24_for_host, fix_7_24_for_host,
    check_7_26_for_host, fix_7_26_for_host,
    check_7_27_for_host, fix_7_27_for_host
)

