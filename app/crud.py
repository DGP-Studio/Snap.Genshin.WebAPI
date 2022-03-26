from sqlalchemy.orm import Session

from . import models, schemas


def getPluginID(db: Session, pluginName: str):
    return db.query(models.Plugin).filter(models.Plugin.Name == pluginName).first()

