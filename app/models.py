from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Plugin(Base):
    __tablename__ = "Plugin"

    ID = Column(Integer, primary_key=True, index=True)
    Name = Column(String, index=True)
    Repo = Column(String, index=True)
    # Patches = relationship("PluginPatch", back_populates="PatchID")


class PluginPatch(Base):
    __tablename__ = "PluginPatch"

    PatchID = Column(Integer, primary_key=True, index=True)
    PluginID = Column(Integer, ForeignKey("Plugin.ID"))
    Tag = Column(String, index=True)
    DownloadURL = Column(String, index=True)