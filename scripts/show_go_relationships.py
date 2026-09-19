"""
Display Government Order relationships from PostgreSQL.

Usage:

    py scripts/show_go_relationships.py "G.O.(Rt) No. 24/2026/ITD"
"""

import sys
from pathlib import Path

# --------------------------------------------------------------
# Add project root to Python import path.
# --------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.metadata_service import MetadataService
from app.storage.relational.session import SessionFactory


def main() -> None:
    """Display incoming and outgoing relationships."""

    if len(sys.argv) < 2:
        print(
            'Usage: py scripts/show_go_relationships.py '
            '"G.O.(Rt) No. 24/2026/ITD"'
        )
        return

    go_number = sys.argv[1].strip()

    session = SessionFactory()

    try:
        metadata_service = MetadataService(
            session
        )

        government_order = (
            metadata_service.find_by_go_number(
                go_number
            )
        )

        if government_order is None:
            print()
            print(
                f"Government Order not found: "
                f"{go_number}"
            )
            return

        print("=" * 70)
        print("KERALA GO - RELATIONSHIP GRAPH")
        print("=" * 70)

        print()
        print(
            f"Government Order: "
            f"{government_order.go_number}"
        )

        print(
            f"Database ID: "
            f"{government_order.id}"
        )

        print(
            f"Document ID: "
            f"{government_order.document_id}"
        )

        # ==============================================================
        # INCOMING RELATIONSHIPS
        # ==============================================================

        print()
        print("INCOMING RELATIONSHIPS")
        print("-" * 70)

        incoming = (
            metadata_service
            .get_incoming_relationships(
                government_order.id
            )
        )

        if not incoming:
            print("  None")
        else:
            for relationship in incoming:

                source = (
                    metadata_service.get_by_id(
                        relationship.source_go_id
                    )
                )

                if source is None:
                    source_number = (
                        str(
                            relationship.source_go_id
                        )
                    )
                else:
                    source_number = (
                        source.go_number
                    )

                print(
                    f"  {source_number}"
                )

                print(
                    f"    Relationship: "
                    f"{relationship.relationship_type}"
                )

                print(
                    f"    Matched phrase: "
                    f"{relationship.matched_phrase}"
                )

                if relationship.page_number is not None:
                    print(
                        f"    Page: "
                        f"{relationship.page_number}"
                    )

                print()

        # ==============================================================
        # OUTGOING RELATIONSHIPS
        # ==============================================================

        print()
        print("OUTGOING RELATIONSHIPS")
        print("-" * 70)

        outgoing = (
            metadata_service
            .get_outgoing_relationships(
                government_order.id
            )
        )

        if not outgoing:
            print("  None")
        else:
            for relationship in outgoing:

                target = (
                    metadata_service.get_by_id(
                        relationship.target_go_id
                    )
                )

                if target is None:
                    target_number = (
                        str(
                            relationship.target_go_id
                        )
                    )
                else:
                    target_number = (
                        target.go_number
                    )

                print(
                    f"  {government_order.go_number}"
                    f" --"
                    f"{relationship.relationship_type}"
                    f"--> "
                    f"{target_number}"
                )

                print(
                    f"    Matched phrase: "
                    f"{relationship.matched_phrase}"
                )

                if relationship.page_number is not None:
                    print(
                        f"    Page: "
                        f"{relationship.page_number}"
                    )

                print()

        print("=" * 70)

    finally:
        session.close()


if __name__ == "__main__":
    main()