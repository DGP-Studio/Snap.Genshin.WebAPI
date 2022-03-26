from typing import Optional

from pydantic import BaseModel


class PatchBase(BaseModel):
    Tag: str
    DownloadURL: str


class PluginPatchCreate(PatchBase):
    PatchID: int
    PluginID: int

    class Config:
        orm_mode = True


class PluginBase(BaseModel):
    ID: int
    Name: str
    Repo: str


class PluginCreate(PluginBase):
    pass


class Plugin(PluginBase):
    ID: int
    Name: str
    Repo: str

    class Config:
        orm_mode = True