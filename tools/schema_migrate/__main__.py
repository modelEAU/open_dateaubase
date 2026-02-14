"""Allow ``python -m tools.schema_migrate`` invocation."""

import sys

from .cli import main

sys.exit(main())
