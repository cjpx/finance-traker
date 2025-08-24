from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal

# Create your models here.

# --------------------------
# Core Supporting Models
# --------------------------

class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)  # e.g. USD, CAD, BTC
    name = models.CharField(max_length=50)               # e.g. US Dollar
    symbol = models.CharField(max_length=5, blank=True)  # e.g. $

    def __str__(self):
        return f"{self.code} ({self.symbol})"
    

class BaseAccount(models.Model):
    name = models.CharField(max_length=100)
    account_holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    is_tax_advantage = models.BooleanField(default=False)
    can_withdraw_anytime = models.BooleanField(default=True)
    is_associate_with_gov = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True




class CheckingAccount(BaseAccount):
    balance = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    #interest_rate = models.DecimalField(max_digits=7, decimal_places=6, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.account_holder}'s {self.name} @ {self.currency.symbol}{self.balance} {self.currency.code}"
    


class SavingsAccount(BaseAccount):
    balance = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0"))
    interest_rate = models.DecimalField(max_digits=7, decimal_places=6, default=Decimal('0.010'))

    def __str__(self):
        return f"{self.account_holder}'s {self.name} @ {self.currency.symbol}{self.balance} {self.currency.code}"

class CreditAccount(BaseAccount):
    credit_limit = models.DecimalField(max_digits=20, decimal_places=4)
    balance = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0"))  # amount owed
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # annual %
    due_date = models.DateField(null=True, blank=True)

    def available_credit(self):
        return self.credit_limit - self.balance
    
    def is_over_limit(self):
        return self.balance > self.credit_limit
    
    def __str__(self):
        return f"{self.account_holder}'s {self.name} @ {self.currency.symbol}{self.balance} {self.currency.code}"
    

