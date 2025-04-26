from typing import TypedDict, Literal


class Camera(TypedDict):
    name: str
    url: str


Level = Literal["info", "error", "warning", "critical"]
