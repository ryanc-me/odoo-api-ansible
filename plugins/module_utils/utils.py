def check_ids(ids):
    """Ensure ids is a list of integers"""
    ids = ids[:]
    if not isinstance(ids, list):
        ids = [ids]
    for i, val in enumerate(ids):
        if not isinstance(val, int):
            ids[i] = int(val)
    return ids
