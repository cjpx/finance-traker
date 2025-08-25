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
    



# --------------------------
# Financial Supporting Models
# --------------------------

class StockExchange(models.Model):
    name = models.CharField(max_length=100)            # e.g., "New York Stock Exchange"
    code = models.CharField(max_length=10, unique=True) # e.g., "NYSE" or "XNYS"
    country = models.CharField(max_length=50)          # e.g., "USA"
    timezone = models.CharField(max_length=50, null=True)        # e.g., "America/New_York"
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)  
    name = models.CharField(max_length=100)
    exchange = models.ForeignKey(StockExchange, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    unite_price = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.symbol} ({self.exchange.code})"
    


class Commodity(models.Model):
    symbol = models.CharField(max_length=10)  
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.symbol} ({self.name})"

class BrokerageAccount(BaseAccount):
    """Generic brokerage account."""
    balance = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0"))
    #stock_holdings = models.ManyToManyField(Stock, through='StockHolding', related_name='brokerage_accounts')

    def __str__(self):
        return f"{self.account_holder}'s {self.name} (Brokerage) - {self.currency.code}"


class TFSA(BrokerageAccount):
    def __str__(self):
        return f"{self.account_holder} TFSA Account {self.currency.symbol}{self.currency.code}" 


class StockHolding(models.Model):
    account = models.ForeignKey(BrokerageAccount, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0.00"))   # fractional shares
    average_price = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0.00"))  # avg cost/share
    date = models.DateTimeField(auto_now_add=True) 

    class Meta:
        unique_together = ('account', 'stock')  # Ensure each stock is unique per account

    def __str__(self):
        return f"{self.quantity} of {self.stock.name} in {self.account.account_holder}'s TFSA"
    


    def buy(self, quantity, price):
        """Buy stock: increase quantity, update avg price, reduce portfolio balance"""
        total_cost = quantity * price


        # Check available balance
        if self.account.balance < total_cost:
            raise ValueError("Insufficient funds")
        #deduct cash
        self.account.balance -= total_cost
        self.account.save()

        # Weighted average price calculation
        current_total_cost = self.quantity * self.average_price
        new_total_shares = self.quantity + quantity
        new_total_cost = current_total_cost + total_cost

        if new_total_shares > 0:
            self.average_price = new_total_cost / new_total_shares
        #update shares
        self.quantity = new_total_shares
        self.save()

        # record Transaction
        Transaction.objects.create(
            holding = self,
            transaction_type = "BUY",
            quantity = quantity,
            price = price
        )


    def sell(self, quantity, price):
        """Sell stock: decrease quantity, increase portfolio balance"""
        if self.quantity < quantity:
            raise ValueError("You have less share available than you are trying to sell")
        
        total_proceeds = quantity * price

        #reduce shares
        self.quantity -= quantity
        self.save()

        #add cash
        self.account.balance += total_proceeds
        self.account.save()

        #record Transaction
        Transaction.objects.create(
            holding=self,
            transaction_type = "SELL",
            quantity=quantity,
            price=price
        )


class Transaction(models.Model):
    holding = models.ForeignKey(StockHolding, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=[('BUY', 'Buy'), ('SELL', 'Sell')])
    quantity = models.DecimalField(max_digits=12, decimal_places=6)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
        









