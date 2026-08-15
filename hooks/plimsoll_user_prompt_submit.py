#!/usr/bin/env python3
"""UserPromptSubmit launcher. Finds the package relative to itself.

The plugin is unpacked wherever the plugin cache puts it, so nothing may be
assumed about the working directory or PYTHONPATH. Two lines of bootstrap
here is the price of an install that is not machine-specific.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plimsoll.hook import main

if __name__ == "__main__":
    sys.exit(main())
