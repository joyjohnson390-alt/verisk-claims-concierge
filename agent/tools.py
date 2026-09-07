import time

import httpx

from db.database import SessionLocal
from db import models


def get_claim(claim_id: str, user_id: str, persona: str) -> dict:
    db = SessionLocal()
    try:
        claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
        if claim is None:
            return {"error": "Claim not found"}

        if persona == "claimant":
            if claim.claimant_id != user_id:
                return {"error": "Access denied"}
        elif persona == "contractor":
            wo_match = (
                db.query(models.WorkOrder)
                .filter(
                    models.WorkOrder.claim_id == claim_id,
                    models.WorkOrder.contractor_id == user_id,
                )
                .first()
            )
            if wo_match is None:
                return {"error": "Access denied"}
        elif persona == "adjuster":
            if claim.adjuster_id != user_id:
                return {"error": "Access denied"}
        else:
            return {"error": "Access denied"}

        claimant = db.query(models.Claimant).filter(models.Claimant.id == claim.claimant_id).first()
        adjuster = db.query(models.Adjuster).filter(models.Adjuster.id == claim.adjuster_id).first()
        work_orders = db.query(models.WorkOrder).filter(models.WorkOrder.claim_id == claim_id).all()
        evidence_records = db.query(models.Evidence).filter(models.Evidence.claim_id == claim_id).all()

        return {
            "claim_id": claim.id,
            "status": claim.status,
            "property_address": claim.property_address,
            "loss_date": claim.loss_date,
            "loss_lat": claim.loss_lat,
            "loss_lon": claim.loss_lon,
            "loss_description": claim.loss_description,
            "estimate_amount": claim.estimate_amount,
            "source_pes_id": claim.source_pes_id,
            "source_acculynx_id": claim.source_acculynx_id,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at,
            "claimant_id": claimant.id if claimant else None,
            "claimant_name": claimant.name if claimant else None,
            "claimant_email": claimant.email if claimant else None,
            "claimant_phone": claimant.phone if claimant else None,
            "adjuster_id": adjuster.id if adjuster else None,
            "adjuster_name": adjuster.name if adjuster else None,
            "work_orders": [
                {
                    "work_order_id": wo.id,
                    "contractor_id": wo.contractor_id,
                    "status": wo.status,
                    "description": wo.description,
                    "notes": wo.notes,
                    "created_at": wo.created_at,
                    "updated_at": wo.updated_at,
                }
                for wo in work_orders
            ],
            "evidence": [
                {
                    "evidence_id": ev.id,
                    "filename": ev.filename,
                    "description": ev.description,
                    "uploaded_by": ev.uploaded_by,
                    "uploaded_at": ev.uploaded_at,
                }
                for ev in evidence_records
            ],
        }
    except Exception as exc:
        return {"error": str(exc)}
    finally:
        db.close()


def get_weather(lat: float, lon: float, date: str) -> dict:
    url = f"http://localhost:8001/weather/{lat}/{lon}/{date}"
    try:
        response = httpx.get(url, timeout=3.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"error": "Weather service unavailable", "available": False}


def get_estimate(claim_id: str) -> dict:
    url = f"http://localhost:8002/estimates/{claim_id}"
    try:
        response = httpx.get(url, timeout=5.0)
        if response.status_code == 404:
            return {"error": "Not found in AccuLynx"}
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError:
        return {"error": "AccuLynx unavailable"}
    except Exception:
        return {"error": "AccuLynx unavailable"}


def write_work_order(
    claim_id: str,
    contractor_id: str,
    description: str,
    notes: str = "",
) -> dict:
    db = SessionLocal()
    try:
        wo_id = f"WO-{claim_id}-{int(time.time())}"
        wo = models.WorkOrder(
            id=wo_id,
            claim_id=claim_id,
            contractor_id=contractor_id,
            description=description,
            notes=notes,
            status="pending",
        )
        db.add(wo)
        db.commit()
        return {"success": True, "work_order_id": wo_id}
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


def write_invoice(work_order_id: str, amount: float, notes: str = "") -> dict:
    db = SessionLocal()
    try:
        inv_id = f"INV-{work_order_id}-{int(time.time())}"
        invoice = models.Invoice(
            id=inv_id,
            work_order_id=work_order_id,
            amount=amount,
            notes=notes,
            status="pending_review",
        )
        db.add(invoice)
        db.commit()
        return {"success": True, "invoice_id": inv_id}
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


def write_evidence(claim_id: str, filename: str, description: str, uploaded_by: str) -> dict:
    db = SessionLocal()
    try:
        ev_id = f"EVD-{claim_id}-{int(time.time())}"
        ev = models.Evidence(
            id=ev_id,
            claim_id=claim_id,
            filename=filename,
            description=description,
            uploaded_by=uploaded_by,
        )
        db.add(ev)
        db.commit()
        return {"success": True, "evidence_id": ev_id}
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


def update_work_order_status(work_order_id: str, status: str, notes: str = "") -> dict:
    db = SessionLocal()
    try:
        wo = db.query(models.WorkOrder).filter(models.WorkOrder.id == work_order_id).first()
        if wo is None:
            return {"success": False, "error": f"Work order {work_order_id} not found"}
        wo.status = status
        if notes:
            wo.notes = notes
        db.commit()
        return {"success": True}
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


def list_adjuster_claims(adjuster_id: str) -> list:
    db = SessionLocal()
    try:
        claims = db.query(models.Claim).filter(models.Claim.adjuster_id == adjuster_id).all()
        return [
            {
                "claim_id": c.id,
                "status": c.status,
                "property_address": c.property_address,
                "loss_date": c.loss_date,
                "loss_description": c.loss_description,
                "estimate_amount": c.estimate_amount,
                "claimant_id": c.claimant_id,
                "source_pes_id": c.source_pes_id,
                "source_acculynx_id": c.source_acculynx_id,
            }
            for c in claims
        ]
    except Exception:
        return []
    finally:
        db.close()
