from sqlalchemy.orm import Session

from . import models, schemas


def getPluginName(db: Session, pluginID: int):
    return db.query(models.Plugin).filter(models.Plugin.ID == pluginID).first()

