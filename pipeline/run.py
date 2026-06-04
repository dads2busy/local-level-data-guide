"""Run the full pipeline end to end (acquisition → outputs → validation)."""
from __future__ import annotations

from pipeline import (
    acquire_acs,
    acquire_geographies,
    acquire_ookla,
    combine,
    redistribute_broadband,
    redistribute_income,
    validate,
)


def main() -> None:
    acquire_geographies.main()
    acquire_acs.main()
    acquire_ookla.main()
    redistribute_income.main()
    redistribute_broadband.main()
    combine.main()
    validate.main()
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
