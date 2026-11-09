from datetime import datetime, timezone 
 
_frozen = None 
 
def now(): 
    return _frozen if _frozen else datetime.now(timezone.utc) 
