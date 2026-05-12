from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class DeviceCertificate(Base):
    """
    X.509 certificates issued to devices for mTLS authentication.
    Tracks certificate lifecycle: issuance, expiry, and revocation.
    """
    __tablename__ = "device_certificates"

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String(20), ForeignKey("devices.serial_number"), nullable=False, index=True)

    # Certificate data (PEM-encoded)
    certificate_pem = Column(Text, nullable=False)

    # Lifecycle tracking
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Revocation tracking
    revoked_at = Column(DateTime(timezone=True))
    revocation_reason = Column(String(100))

    def __repr__(self):
        return f"<DeviceCertificate(serial_number='{self.serial_number}', expires_at='{self.expires_at}')>"

    @property
    def is_active(self):
        """Check if certificate is currently valid (not expired, not revoked)"""
        from datetime import datetime, timezone as tz
        now = datetime.now(tz.utc)
        return (
            self.revoked_at is None
            and self.expires_at > now
        )
