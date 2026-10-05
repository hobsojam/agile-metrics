"""Tests for CSV item import (spec 007).

No I/O to mock - CSV parsing and bucketing are pure string/data-in,
model-out logic.
"""

from __future__ import annotations

SAMPLE_CSV = """id,type,title,start_date,end_date
1,story,First item,2026-08-01,2026-08-05
2,story,Second item,2026-08-03,2026-08-12
3,bug,Third item,2026-08-10,2026-08-19
4,story,Fourth item,2026-08-15,2026-08-26
5,bug,Fifth item,2026-09-01,2026-09-02
6,story,Sixth item,2026-09-10,2026-09-16
7,story,Still open,2026-09-20,
"""
