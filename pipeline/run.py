"""Run the full pipeline end to end (acquisition → outputs → validation)."""
from __future__ import annotations

from pipeline import (
    acquire_acs,
    acquire_geographies,
    acquire_ookla,
    acquire_parcels,
    combine,
    compare_methods,
    redistribute_broadband,
    redistribute_income,
    redistribute_income_parcels,
    validate,
)


def main() -> None:
    acquire_geographies.main()
    acquire_acs.main()
    acquire_ookla.main()
    acquire_parcels.main()
    redistribute_income.main()
    redistribute_broadband.main()
    combine.main()
    redistribute_income_parcels.main()
    compare_methods.main()
    validate.main()
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
