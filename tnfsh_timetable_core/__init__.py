
class TNFSHTimetableCore:
    def __init__(self):
        pass
    
    def get_timetable(self):
        from tnfsh_timetable_core.timetable.models import ClassTable
        return ClassTable()

    def get_index(self):
        from tnfsh_timetable_core.index.index import Index
        return Index()
