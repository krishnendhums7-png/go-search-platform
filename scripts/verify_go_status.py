"""
Verify Government Order status using the real PostgreSQL database.

Usage:

    py scripts/verify_go_status.py "G.O.(Rt) No. 24/2026/ITD"
"""

import argparse
import sys
from pathlib import Path

# Add the project root (C:\go-search) to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.metadata_service import MetadataService
from app.services.status_verification_service import (
    StatusVerificationService,
)
from app.storage.relational.session import SessionFactory


def main() -> None:
    """Run Government Order status verification."""

    parser = argparse.ArgumentParser(
        description=(
            "Verify the status of a Kerala Government Order."
        )
    )

    parser.add_argument(
        "go_number",
        help="Government Order number to verify.",
    )

    args = parser.parse_args()

    session = SessionFactory()

    try:
        metadata_service = MetadataService(
            session
        )

        status_service = StatusVerificationService(
            metadata_service
        )

        result = status_service.verify_by_go_number(
            args.go_number
        )

        print("=" * 70)
        print("KERALA GO - MODULE 9")
        print("RECURSIVE STATUS VERIFICATION")
        print("=" * 70)

        print()
        print("Government Order:")
        print(f"  {result.go_number}")

        print()
        print("Document ID:")
        print(f"  {result.document_id}")

        print()
        print("Status:")
        print(f"  {result.status.value}")

        print()
        print("Relationships checked:")
        print(f"  {result.relationships_checked}")

        print()
        print("Cycle detected:")
        print(f"  {result.cycle_detected}")

        print()
        print("Traversal:")

        if result.traversed_go_numbers:
            for index, go_number in enumerate(
                result.traversed_go_numbers,
                start=1,
            ):
                print(
                    f"  {index}. {go_number}"
                )
        else:
            print(
                "  No related Government Orders found."
            )

        print()
        print("=" * 70)
        print("STATUS VERIFICATION COMPLETE")
        print("=" * 70)

    except ValueError as exc:
        print()
        print("ERROR:")
        print(f"  {exc}")

    finally:
        session.close()


if __name__ == "__main__":
    main()