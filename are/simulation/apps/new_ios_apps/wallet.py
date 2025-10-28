# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from are.simulation.apps.app import App
from are.simulation.tool_utils import OperationType, app_tool, data_tool
from are.simulation.types import event_registered
from are.simulation.utils import get_state_dict, type_check, uuid_hex


class CardType(Enum):
    CREDIT = "Credit Card"
    DEBIT = "Debit Card"
    PREPAID = "Prepaid Card"


class PassType(Enum):
    BOARDING_PASS = "Boarding Pass"
    EVENT_TICKET = "Event Ticket"
    LOYALTY_CARD = "Loyalty Card"
    COUPON = "Coupon"
    GIFT_CARD = "Gift Card"


class TransactionType(Enum):
    PURCHASE = "Purchase"
    REFUND = "Refund"
    PAYMENT = "Payment"
    TRANSFER = "Transfer"


@dataclass
class Card:
    """Represents a payment card in the wallet."""

    card_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    card_type: CardType = CardType.CREDIT
    card_holder_name: str = "Card Holder"
    last_four_digits: str = "0000"
    issuer: str = "Bank"
    is_default: bool = False
    expiry_date: str | None = None  # MM/YY format
    spending_limit: float | None = None

    def __str__(self):
        info = f"💳 {self.card_type.value}\nIssuer: {self.issuer}\nEnding in: {self.last_four_digits}"

        if self.expiry_date:
            info += f"\nExpires: {self.expiry_date}"
        if self.is_default:
            info += "\n✓ Default Card"
        if self.spending_limit:
            info += f"\nSpending Limit: ${self.spending_limit:.2f}"

        return info


@dataclass
class Pass:
    """Represents a pass (boarding pass, ticket, etc.)."""

    pass_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pass_type: PassType = PassType.BOARDING_PASS
    title: str = "Pass"
    description: str = ""
    barcode: str | None = None
    valid_from: float | None = None
    valid_until: float | None = None
    location: str | None = None
    is_used: bool = False

    def __str__(self):
        info = f"🎫 {self.title}\nType: {self.pass_type.value}"

        if self.description:
            info += f"\nDescription: {self.description}"
        if self.location:
            info += f"\nLocation: {self.location}"
        if self.valid_until:
            info += f"\nValid Until: {time.ctime(self.valid_until)}"
        if self.is_used:
            info += "\n✓ Used"

        return info


@dataclass
class Transaction:
    """Represents a financial transaction."""

    transaction_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    transaction_type: TransactionType = TransactionType.PURCHASE
    amount: float = 0.0
    merchant: str = "Merchant"
    category: str = "Other"
    card_id: str | None = None
    timestamp: float = field(default_factory=time.time)
    description: str = ""

    def __str__(self):
        sign = "-" if self.transaction_type in [TransactionType.PURCHASE, TransactionType.PAYMENT] else "+"
        info = f"{sign}${abs(self.amount):.2f} - {self.merchant}\nType: {self.transaction_type.value}"
        info += f"\nCategory: {self.category}\nDate: {time.ctime(self.timestamp)}"

        if self.description:
            info += f"\nDescription: {self.description}"

        return info


@dataclass
class WalletApp(App):
    """
    Wallet and payment management application.

    Manages payment cards, passes, transactions, and spending.
    Provides secure payment capabilities and financial tracking.

    Key Features:
        - Payment Cards: Store and manage credit/debit cards
        - Passes: Store boarding passes, tickets, loyalty cards
        - Transactions: Track spending and payment history
        - Spending Limits: Set card spending limits
        - Default Card: Set preferred payment method
        - Pass Management: Organize event tickets and travel documents

    Notes:
        - Cards can have spending limits for budget control
        - Passes expire and can be marked as used
        - Transactions are logged automatically
    """

    name: str | None = None
    cards: dict[str, Card] = field(default_factory=dict)
    passes: dict[str, Pass] = field(default_factory=dict)
    transactions: dict[str, Transaction] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__(self.name)

    def get_state(self) -> dict[str, Any]:
        return get_state_dict(self, ["cards", "passes", "transactions"])

    def load_state(self, state_dict: dict[str, Any]):
        self.cards = {k: Card(**v) for k, v in state_dict.get("cards", {}).items()}
        self.passes = {k: Pass(**v) for k, v in state_dict.get("passes", {}).items()}
        self.transactions = {k: Transaction(**v) for k, v in state_dict.get("transactions", {}).items()}

    def reset(self):
        super().reset()
        self.cards = {}
        self.passes = {}
        self.transactions = {}

    # Card Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_card(
        self,
        card_type: str,
        card_holder_name: str,
        last_four_digits: str,
        issuer: str,
        expiry_date: str | None = None,
        spending_limit: float | None = None,
    ) -> str:
        """
        Add a payment card to the wallet.

        :param card_type: Type of card. Options: Credit Card, Debit Card, Prepaid Card
        :param card_holder_name: Name on the card
        :param last_four_digits: Last 4 digits of card number
        :param issuer: Card issuer/bank name
        :param expiry_date: Expiry date in MM/YY format
        :param spending_limit: Optional spending limit for this card
        :returns: card_id of the added card
        """
        card_type_enum = CardType[card_type.upper().replace(" ", "_")]

        card = Card(
            card_id=uuid_hex(self.rng),
            card_type=card_type_enum,
            card_holder_name=card_holder_name,
            last_four_digits=last_four_digits,
            issuer=issuer,
            expiry_date=expiry_date,
            spending_limit=spending_limit,
            is_default=len(self.cards) == 0,  # First card becomes default
        )

        self.cards[card.card_id] = card
        return card.card_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_default_card(self, card_id: str) -> str:
        """
        Set a card as the default payment method.

        :param card_id: ID of the card to set as default
        :returns: Success or error message
        """
        if card_id not in self.cards:
            return f"Card with ID {card_id} not found."

        # Remove default from all cards
        for card in self.cards.values():
            card.is_default = False

        # Set new default
        self.cards[card_id].is_default = True

        return f"✓ Card ending in {self.cards[card_id].last_four_digits} set as default."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def set_spending_limit(self, card_id: str, limit: float) -> str:
        """
        Set spending limit for a card.

        :param card_id: ID of the card
        :param limit: Spending limit amount
        :returns: Success or error message
        """
        if card_id not in self.cards:
            return f"Card with ID {card_id} not found."

        self.cards[card_id].spending_limit = limit
        return f"✓ Spending limit set to ${limit:.2f} for card ending in {self.cards[card_id].last_four_digits}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_card(self, card_id: str) -> str:
        """
        Remove a card from the wallet.

        :param card_id: ID of the card to remove
        :returns: Success or error message
        """
        if card_id not in self.cards:
            return f"Card with ID {card_id} not found."

        card_info = f"card ending in {self.cards[card_id].last_four_digits}"
        del self.cards[card_id]

        return f"✓ Removed {card_info}."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_cards(self) -> str:
        """
        List all payment cards.

        :returns: String representation of all cards
        """
        if not self.cards:
            return "No cards in wallet."

        result = f"Payment Cards ({len(self.cards)}):\n\n"
        for card in self.cards.values():
            result += str(card) + "\n" + "-" * 40 + "\n"

        return result

    # Pass Management

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def add_pass(
        self,
        pass_type: str,
        title: str,
        description: str = "",
        location: str | None = None,
        valid_until: str | None = None,
    ) -> str:
        """
        Add a pass (boarding pass, ticket, etc.) to the wallet.

        :param pass_type: Type of pass. Options: Boarding Pass, Event Ticket, Loyalty Card, Coupon, Gift Card
        :param title: Pass title
        :param description: Pass description
        :param location: Location (venue, airport, etc.)
        :param valid_until: Expiry date/time in format "YYYY-MM-DD HH:MM:SS"
        :returns: pass_id of the added pass
        """
        pass_type_enum = PassType[pass_type.upper().replace(" ", "_")]

        valid_until_timestamp = None
        if valid_until:
            from datetime import datetime, timezone

            dt = datetime.strptime(valid_until, "%Y-%m-%d %H:%M:%S")
            valid_until_timestamp = dt.replace(tzinfo=timezone.utc).timestamp()

        pass_obj = Pass(
            pass_id=uuid_hex(self.rng),
            pass_type=pass_type_enum,
            title=title,
            description=description,
            location=location,
            valid_from=self.time_manager.time(),
            valid_until=valid_until_timestamp,
        )

        self.passes[pass_obj.pass_id] = pass_obj
        return pass_obj.pass_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def mark_pass_as_used(self, pass_id: str) -> str:
        """
        Mark a pass as used.

        :param pass_id: ID of the pass
        :returns: Success or error message
        """
        if pass_id not in self.passes:
            return f"Pass with ID {pass_id} not found."

        self.passes[pass_id].is_used = True
        return f"✓ Pass '{self.passes[pass_id].title}' marked as used."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def remove_pass(self, pass_id: str) -> str:
        """
        Remove a pass from the wallet.

        :param pass_id: ID of the pass to remove
        :returns: Success or error message
        """
        if pass_id not in self.passes:
            return f"Pass with ID {pass_id} not found."

        pass_title = self.passes[pass_id].title
        del self.passes[pass_id]

        return f"✓ Removed pass '{pass_title}'."

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def list_passes(self, pass_type: str | None = None, active_only: bool = True) -> str:
        """
        List all passes in the wallet.

        :param pass_type: Filter by pass type
        :param active_only: Only show active (not used and not expired) passes
        :returns: String representation of passes
        """
        filtered_passes = list(self.passes.values())

        if pass_type:
            pass_type_enum = PassType[pass_type.upper().replace(" ", "_")]
            filtered_passes = [p for p in filtered_passes if p.pass_type == pass_type_enum]

        if active_only:
            current_time = self.time_manager.time()
            filtered_passes = [
                p
                for p in filtered_passes
                if not p.is_used and (p.valid_until is None or p.valid_until > current_time)
            ]

        if not filtered_passes:
            return "No passes found."

        result = f"Passes ({len(filtered_passes)}):\n\n"
        for pass_obj in filtered_passes:
            result += str(pass_obj) + "\n" + "-" * 40 + "\n"

        return result

    # Transactions

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.WRITE)
    def log_transaction(
        self,
        transaction_type: str,
        amount: float,
        merchant: str,
        category: str = "Other",
        card_id: str | None = None,
        description: str = "",
    ) -> str:
        """
        Log a financial transaction.

        :param transaction_type: Type of transaction. Options: Purchase, Refund, Payment, Transfer
        :param amount: Transaction amount (positive value)
        :param merchant: Merchant/recipient name
        :param category: Transaction category (e.g., Food, Transportation, Entertainment)
        :param card_id: ID of card used (if applicable)
        :param description: Optional description
        :returns: transaction_id of the logged transaction
        """
        transaction_type_enum = TransactionType[transaction_type.upper()]

        # Check spending limit if card is specified
        if card_id and card_id in self.cards:
            card = self.cards[card_id]
            if card.spending_limit and transaction_type_enum == TransactionType.PURCHASE:
                # Calculate current spending for this card
                card_transactions = [t for t in self.transactions.values() if t.card_id == card_id and t.transaction_type == TransactionType.PURCHASE]
                current_spending = sum(t.amount for t in card_transactions)

                if current_spending + amount > card.spending_limit:
                    return f"⚠️ Transaction declined: Would exceed spending limit of ${card.spending_limit:.2f} for card ending in {card.last_four_digits}."

        transaction = Transaction(
            transaction_id=uuid_hex(self.rng),
            transaction_type=transaction_type_enum,
            amount=amount,
            merchant=merchant,
            category=category,
            card_id=card_id,
            timestamp=self.time_manager.time(),
            description=description,
        )

        self.transactions[transaction.transaction_id] = transaction
        return transaction.transaction_id

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_transaction_history(self, limit: int = 20, category: str | None = None) -> str:
        """
        Get recent transaction history.

        :param limit: Maximum number of transactions to return
        :param category: Filter by category
        :returns: String representation of transactions
        """
        filtered_transactions = list(self.transactions.values())

        if category:
            filtered_transactions = [t for t in filtered_transactions if t.category.lower() == category.lower()]

        # Sort by timestamp (most recent first)
        filtered_transactions.sort(key=lambda t: t.timestamp, reverse=True)
        filtered_transactions = filtered_transactions[:limit]

        if not filtered_transactions:
            return "No transactions found."

        result = f"Recent Transactions ({len(filtered_transactions)}):\n\n"
        for transaction in filtered_transactions:
            result += str(transaction) + "\n" + "-" * 40 + "\n"

        return result

    @type_check
    @app_tool()
    @data_tool()
    @event_registered(operation_type=OperationType.READ)
    def get_spending_summary(self) -> str:
        """
        Get spending summary and statistics.

        :returns: Spending summary
        """
        purchases = [t for t in self.transactions.values() if t.transaction_type == TransactionType.PURCHASE]
        total_spending = sum(t.amount for t in purchases)

        # Category breakdown
        category_spending = {}
        for transaction in purchases:
            category_spending[transaction.category] = category_spending.get(transaction.category, 0) + transaction.amount

        result = "=== SPENDING SUMMARY ===\n\n"
        result += f"Total Spending: ${total_spending:.2f}\n"
        result += f"Total Transactions: {len(purchases)}\n\n"

        if category_spending:
            result += "Spending by Category:\n"
            for category, amount in sorted(category_spending.items(), key=lambda x: x[1], reverse=True):
                result += f"  - {category}: ${amount:.2f}\n"

        return result
