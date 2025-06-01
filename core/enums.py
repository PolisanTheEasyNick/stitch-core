from enum import Enum

class ActivityType(str, Enum):
    WALKING = "walk"
    SLEEPING = "sleep"
    CYCLING = "cycle"
