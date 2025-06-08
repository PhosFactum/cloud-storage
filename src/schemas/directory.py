from pydantic import BaseModel


class ListDirResponse(BaseModel):
    directories: list[str]
    files: list[str]
