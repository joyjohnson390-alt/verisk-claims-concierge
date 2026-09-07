"""
Seed the SQLite database with realistic mock Verisk data.
Demonstrates identity resolution: contractors have both PES and AccuLynx source IDs.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import init_db, SessionLocal
from db.models import Claimant, Contractor, Adjuster, Claim, WorkOrder, Invoice, Evidence


def seed():
    init_db()
    db = SessionLocal()

    # Clear existing data
    for model in [Evidence, Invoice, WorkOrder, Claim, Claimant, Contractor, Adjuster]:
        db.query(model).delete()
    db.commit()

    # --- Adjusters ---
    adjusters = [
        Adjuster(id="ADJ-001", name="Maria Santos", email="m.santos@verisk-claims.com", region="Southeast"),
        Adjuster(id="ADJ-002", name="David Kim", email="d.kim@verisk-claims.com", region="Gulf Coast"),
    ]
    db.add_all(adjusters)

    # --- Contractors ---
    # Note: Both source IDs present — demonstrates harmonization from PES + AccuLynx
    contractors = [
        Contractor(
            id="CON-001",
            name="Jake Morales",
            company="Morales Roofing & Restoration",
            license_id="FL-ROO-8821",
            email="jake@moralesroofing.com",
            source_pes_id="PES-C-4491",
            source_acculynx_id="ALX-7734",
        ),
        Contractor(
            id="CON-002",
            name="Priya Patel",
            company="Patel General Contractors",
            license_id="FL-GC-2205",
            email="priya@patelgc.com",
            source_pes_id="PES-C-5502",
            source_acculynx_id="ALX-8819",
        ),
    ]
    db.add_all(contractors)

    # --- Claimants ---
    claimants = [
        Claimant(id="CLM-001", name="Robert Chen", email="rchen@email.com", phone="850-555-0142"),
        Claimant(id="CLM-002", name="Angela Torres", email="atorres@email.com", phone="850-555-0287"),
        Claimant(id="CLM-003", name="Marcus Johnson", email="mjohnson@email.com", phone="850-555-0391"),
    ]
    db.add_all(claimants)
    db.commit()

    # --- Claims ---
    # Coordinates are real Gulf Coast locations for the weather API to query
    claims = [
        Claim(
            id="CLM-2024-0891",
            claimant_id="CLM-001",
            adjuster_id="ADJ-001",
            status="work_order_issued",
            property_address="1142 Palmetto Drive, Pensacola, FL 32501",
            loss_date="2024-09-26",
            loss_lat=30.4213,
            loss_lon=-87.2169,
            loss_description="Hurricane Helene — severe roof damage and water intrusion. Approx 40% of shingles missing. Interior ceiling damage in 3 rooms.",
            estimate_amount=28500.00,
            source_pes_id="PES-2024-0891",
            source_acculynx_id="ALX-EST-3341",
        ),
        Claim(
            id="CLM-2024-1023",
            claimant_id="CLM-002",
            adjuster_id="ADJ-001",
            status="in_review",
            property_address="87 Magnolia Court, Mobile, AL 36604",
            loss_date="2024-10-01",
            loss_lat=30.6954,
            loss_lon=-88.0399,
            loss_description="Severe storm — hail damage to roof and siding. Multiple windows cracked. HVAC unit damaged.",
            estimate_amount=None,  # Still being assessed
            source_pes_id="PES-2024-1023",
            source_acculynx_id=None,  # Not yet in AccuLynx — demonstrates partial match scenario
        ),
        Claim(
            id="CLM-2024-1187",
            claimant_id="CLM-003",
            adjuster_id="ADJ-002",
            status="repair_in_progress",
            property_address="334 Bayou Vista Blvd, Biloxi, MS 39530",
            loss_date="2024-10-05",
            loss_lat=30.3960,
            loss_lon=-88.8853,
            loss_description="Tornado — structural damage to back wall, garage destroyed, fence down.",
            estimate_amount=67200.00,
            source_pes_id="PES-2024-1187",
            source_acculynx_id="ALX-EST-3489",
        ),
    ]
    db.add_all(claims)
    db.commit()

    # --- Work Orders ---
    work_orders = [
        WorkOrder(
            id="WO-2024-0891-A",
            claim_id="CLM-2024-0891",
            contractor_id="CON-001",
            description="Emergency roof tarp and stabilization, then full shingle replacement and interior ceiling repair.",
            status="in_progress",
            notes="Tarp complete 2024-09-28. Full repair scheduled week of 2024-10-14.",
        ),
        WorkOrder(
            id="WO-2024-1187-A",
            claim_id="CLM-2024-1187",
            contractor_id="CON-002",
            description="Structural wall repair, garage demolition and rebuild, fence replacement.",
            status="in_progress",
            notes="Wall repair in progress. Garage rebuild starts 2024-10-21.",
        ),
    ]
    db.add_all(work_orders)

    # --- Evidence ---
    evidence = [
        Evidence(
            id="EVD-001",
            claim_id="CLM-2024-0891",
            filename="roof_damage_front.jpg",
            description="Aerial photo showing missing shingles across front roof section",
            uploaded_by="CLM-001",
        ),
        Evidence(
            id="EVD-002",
            claim_id="CLM-2024-0891",
            filename="interior_ceiling_bedroom.jpg",
            description="Water staining and collapse in master bedroom ceiling",
            uploaded_by="CLM-001",
        ),
        Evidence(
            id="EVD-003",
            claim_id="CLM-2024-1187",
            filename="back_wall_collapse.jpg",
            description="Structural wall damage from tornado impact",
            uploaded_by="CLM-003",
        ),
    ]
    db.add_all(evidence)

    db.commit()
    db.close()
    print("✓ Database seeded: 3 claims, 2 contractors, 2 adjusters, 3 claimants, 2 work orders, 3 evidence items")


if __name__ == "__main__":
    seed()
