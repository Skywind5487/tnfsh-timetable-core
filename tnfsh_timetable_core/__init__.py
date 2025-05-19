
class TNFSHTimetableCore:
    def __init__(self):
        pass
    
    def fetch_timetable(self, target: str, refresh: bool = False):
        from tnfsh_timetable_core.timetable.models import TimeTable
        return TimeTable.fetch_cached(target=target, refresh=refresh)

    def fetch_index(self):
        from tnfsh_timetable_core.index.index import Index
        return Index()
