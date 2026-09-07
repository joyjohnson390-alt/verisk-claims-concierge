from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class ClaimStatus(str, enum.Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    WORK_ORDER_ISSUED = "work_order_issued"
    REPAIR_IN_PROGRESS = "repair_in_progress"
    INVOICE_SUBMITTED = "invoice_submitted"
    CLOSED = "closed"


class Claimant(Base):
    __tablename__ = "claimants"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    claims = relationship("Claim", back_populates="claimant")


class Contractor(Base):
    __tablename__ = "contractors"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    company = Column(String)
    license_id = Column(String)
    email = Column(String)
    # Source system — demonstrates identity resolution across PES + AccuLynx
    source_pes_id = Column(String)
    source_acculynx_id = Column(String)
    work_orders = relationship("WorkOrder", back_populates="contractor")


class Adjuster(Base):
    __tablename__ = "adjusters"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    region = Column(String)
    claims = relationship("Claim", back_populates="adjuster")


class Claim(Base):
    __tablename__ = "claims"
    id = Column(String, primary_key=True)
    claimant_id = Column(String, ForeignKey("claimants.id"))
    adjuster_id = Column(String, ForeignKey("adjusters.id"))
    status = Column(String, default=ClaimStatus.OPEN)
    property_address = Column(String)
    loss_date = Column(String)          # ISO date string
    loss_lat = Column(Float)
    loss_lon = Column(Float)
    loss_description = Column(Text)
    estimate_amount = Column(Float)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    # Source system IDs — demonstrates harmonization from PES + AccuLynx
    source_pes_id = Column(String)
    source_acculynx_id = Column(String)

    claimant = relationship("Claimant", back_populates="claims")
    adjuster = relationship("Adjuster", back_populates="claims")
    work_orders = relationship("WorkOrder", back_populates="claim")
    evidence = relationship("Evidence", back_populates="claim")


class WorkOrder(Base):
    __tablename__ = "work_orders"
    id = Column(String, primary_key=True)
    claim_id = Column(String, ForeignKey("claims.id"))
    contractor_id = Column(String, ForeignKey("contractors.id"))
    description = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    notes = Column(Text)

    claim = relationship("Claim", back_populates="work_orders")
    contractor = relationship("Contractor", back_populates="work_orders")
    invoices = relationship("Invoice", back_populates="work_order")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String, primary_key=True)
    work_order_id = Column(String, ForeignKey("work_orders.id"))
    amount = Column(Float)
    status = Column(String, default="pending_review")  # pending_review | approved | rejected
    submitted_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    notes = Column(Text)

    work_order = relationship("WorkOrder", back_populates="invoices")


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True)
    claim_id = Column(String, ForeignKey("claims.id"))
    filename = Column(String)
    description = Column(Text)
    uploaded_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    uploaded_by = Column(String)

    claim = relationship("Claim", back_populates="evidence")
