"""Write docs/diagnostic-state.schema.json from the code that produces the state.

    python tools/write_state_schema.py

The schema is the contract Backend and the clients read; tests fail when the
file and app/services/pipeline/diagnostic_state.py disagree.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.pipeline.diagnostic_state import json_schema  # noqa: E402

target = ROOT / "docs" / "diagnostic-state.schema.json"
target.write_text(json.dumps(json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {target.relative_to(ROOT)}")
