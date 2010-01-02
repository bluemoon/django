


class ChangeList(object):
    def __init__(self, request, base_queryset, list_display, list_filter,
        search_fields, list_select_related, list_per_page):
        self.request = request
        self.model = base_queryset.model
        self.base_queryset = base_queryset
        self.list_display = list_display
        self.list_filter = list_filter
        self.search_fields = search_fields
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page
    
    @cached_attribute
    def queryset(self):
        qs = self.apply_filters(self.base_queryset)
        qs = self.apply_search(qs)
        qs = qs.order_by(*self.get_order_by())
        
        if not qs.query.select_related:
            if self.list_select_related:
                qs = qs.select_related()
            else:
                for field in self.list_display:
                    try:
                        f = self.model._meta.get_field_by_name(f)[0]
                        if isinstance(f.rel, ManyToOneRel):
                            qs = qs.select_related()
                            break
                    except FieldDoesNotExist:
                        pass
        page = self.get_page_num()
        paginator = Paginator(qs, self.list_per_page)
        try:
            page = paginator.page(page)
        except (EmptyPage, InvalidPage):
            page = paginator.page(0)
        return page.object_list
    
    def apply_filters(self, qs):
        pass
    
    def apply_search(self, qs):
        pass
    
    def get_order_by(self):
        pass
    
    @cached_attribute
    def full_count(self):
        if self.queryset().query.where:
            return self.base_queryset.all()
        return self.queryset().count()
    
    @cached_attribute
    def count(self):
        return self.queryset().count()
