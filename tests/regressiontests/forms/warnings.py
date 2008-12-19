tests = """
>>> from django import forms
>>> class PriceForm(forms.Form):
...     price = forms.IntegerField()
...     
...     def clean_price(self, warn):
...         p = self.cleaned_data['price']
...         if p < 10:
...             warn(u"That's an awfully low price")
...         if p == 7:
...             warn(u"7 is a pretty strange price")
...         return p

>>> form = PriceForm({'price': 5})
>>> form.is_valid()
True
>>> form.is_valid(True)
False
>>> form.warnings
{'price': [u"That's an awfully low price"]}
>>> form = PriceForm({'price': 7})
>>> form.is_valid()
True
>>> form.warnings
{'price': [u"That's an awfully low price", u'7 is a pretty strange price']}
>>> print form.as_p()
<ul class="warninglist"><li>That&#39;s an awfully low price</li><li>7 is a pretty strange price</li></ul>
<p><label for="id_price">Price:</label> <input type="text" name="price" value="7" id="id_price" /></p>
"""
