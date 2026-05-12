from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DeviceSerial(Base):
    """
    Auto-increment serial number tracker for each device type.
    Ensures sequential serial numbers: W00001, W00002, S00001, etc.
    """
    __tablename__ = "device_serials"

    id = Column(Integer, primary_key=True, index=True)
    device_type = Column(String(20), unique=True, nullable=False)  # 'watch', 'scanner'
    last_sequence = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<DeviceSerial(device_type='{self.device_type}', last_sequence={self.last_sequence})>"
