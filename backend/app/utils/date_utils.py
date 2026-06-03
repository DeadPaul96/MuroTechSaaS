from datetime import datetime

def _parse_date(value, end_of_day=False):
    """Convierte fechas en string a datetime con múltiples formatos admitidos."""
    if not value:
        return None
    if isinstance(value, datetime):
        if end_of_day:
            return value.replace(hour=23, minute=59, second=59, microsecond=999999)
        return value
    try:
        parsed = datetime.fromisoformat(value.replace('Z', ''))
        if end_of_day:
            return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed
    except ValueError:
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
            try:
                parsed = datetime.strptime(value.replace('Z', ''), fmt)
                if end_of_day:
                    return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
                return parsed
            except ValueError:
                continue
    return None
