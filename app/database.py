from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

with open("./config/config.json", "r") as json_f:
    config = json.load(json_f)["mysql"]

SQLALCHEMY_DATABASE = "mysql+pymysql://%s:%s@%s/%s?charset=utf8mb4"
engine = create_engine(
    SQLALCHEMY_DATABASE % (config["userName"], config["password"], config["ip"], config["dbName"])
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


