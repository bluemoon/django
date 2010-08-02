from django.db.models.fields import Field
from django.db.models.fields.subclassing import SubfieldBase


class ListField(Field):
    __metaclass__ = SubfieldBase
    
    def __init__(self, field_type):
        self.field_type = field_type
        super(ListField, self).__init__(default=[])
    
    def get_prep_lookup(self, lookup_type, value):
        return self.field_type.get_prep_lookup(lookup_type, value)
    
    def get_db_prep_save(self, value, connection):
        return [
            self.field_type.get_db_prep_save(o, connection=connection)
            for o in value
        ]
    
    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        return self.field_type.get_db_prep_lookup(
            lookup_type, value, connection=connection, prepared=prepared
        )
    
    def to_python(self, value):
        return [
            self.field_type.to_python(v)
            for v in value
        ]


class EmbeddedModel(Field):
    __metaclass__ = SubfieldBase
    
    def __init__(self, to):
        self.to = to
        super(EmbeddedModel, self).__init__()
    
    def get_db_prep_save(self, value, connection):
        data = {}
        for field in self.to._meta.fields:
            data[field.column] = field.get_db_prep_save(getattr(value, field.name), connection=connection)
        return data
    
    def to_python(self, value):
        return self.to(**value)
