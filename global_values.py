from enum import Enum


class FlagType(Enum):
    UPLOAD = ("UPLOAD",)
    ENCRYPT = ("ENCRYPT",)
    MODE = ("MODE",)
    OVERWRITE = ("OVERWRITE",)
    DELETE_LOCAL = ("DELETE_LOCAL",)
    HANDLE_UNFINISHED = "HANDLE_UNFNISHED"


FLAGS = {
    FlagType.UPLOAD: None,
    FlagType.ENCRYPT: None,
    FlagType.MODE: None,
    FlagType.OVERWRITE: None,
    FlagType.DELETE_LOCAL: None,
    FlagType.HANDLE_UNFINISHED: None,
}


class Mode(Enum):
    STANDARD = "standard"
    DECRYPT = "decrypt"
    CREATE_KEYS = "create-keys"


PREFIX = "__camtransfer__"
