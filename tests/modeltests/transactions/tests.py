import sys

from django.db import transaction
from django.test import TransactionTestCase

from models import Reporter


class TransactionsTestCase(TransactionTestCase):
    def test_context_manager(self):
        tran = transaction.autocommit()
        tran.__enter__()
        try:
            Reporter.objects.create(first_name="Bob", last_name="Woodward",
                email="bob.woodward@deepthroat.net")
        finally:
            tran.__exit__(*sys.exc_info())
        
        self.assertEqual(Reporter.objects.count(), 1)
