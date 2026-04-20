import json
import random
import string
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class BankDatabase:
    """Database management for bank system"""
    
    def __init__(self, database: str = "bank_data.json"):
        self.database = database
        self.data = self._load_data()
    
    def _load_data(self) -> List[Dict]:
        """Load data from JSON file"""
        if Path(self.database).exists():
            try:
                with open(self.database, "r") as fs:
                    data = json.load(fs)
                    return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                print("⚠️ Database corrupted. Starting fresh.")
                return []
        return []
    
    def save_data(self) -> bool:
        """Save data to JSON file"""
        try:
            with open(self.database, "w") as fs:
                json.dump(self.data, fs, indent=4)
            return True
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False
    
    def add_user(self, user: Dict) -> bool:
        """Add new user"""
        self.data.append(user)
        return self.save_data()
    
    def update_user(self, account_num: str, user_data: Dict) -> bool:
        """Update user data"""
        for user in self.data:
            if user["account_num"] == account_num:
                user.update(user_data)
                return self.save_data()
        return False
    
    def remove_user(self, account_num: str) -> bool:
        """Delete user"""
        self.data = [u for u in self.data if u["account_num"] != account_num]
        return self.save_data()
    
    def find_user(self, account_num: str) -> Optional[Dict]:
        """Find user by account number"""
        for user in self.data:
            if user["account_num"] == account_num:
                return user
        return None
    
    def user_exists(self, account_num: str) -> bool:
        """Check if user exists"""
        return any(u["account_num"] == account_num for u in self.data)


class BankValidator:
    """Validation utilities for bank operations"""
    
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        """Validate user name"""
        if not name or len(name.strip()) < 2:
            return False, "Name must be at least 2 characters"
        if not all(c.isalpha() or c.isspace() for c in name):
            return False, "Name should only contain letters"
        return True, ""
    
    @staticmethod
    def validate_age(age: int) -> Tuple[bool, str]:
        """Validate age"""
        try:
            age = int(age)
            if age < 18:
                return False, "You must be 18 or older"
            if age > 120:
                return False, "Please enter a valid age"
            return True, ""
        except ValueError:
            return False, "Age must be a number"
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, ""
        return False, "Invalid email format"
    
    @staticmethod
    def validate_pin(pin: str) -> Tuple[bool, str]:
        """Validate PIN"""
        if len(pin) != 4 or not pin.isdigit():
            return False, "PIN must be exactly 4 digits"
        return True, ""
    
    @staticmethod
    def validate_amount(amount: float, transaction_type: str = "deposit", 
                       balance: float = 0) -> Tuple[bool, str]:
        """Validate transaction amount"""
        try:
            amount = float(amount)
            
            if amount <= 0:
                return False, "Amount must be greater than 0"
            
            if transaction_type == "deposit":
                if amount > 10000:
                    return False, "Deposit limit is Rs 10,000"
                return True, ""
            
            elif transaction_type == "withdraw":
                if amount > balance:
                    return False, f"Insufficient balance. Available: Rs {balance}"
                return True, ""
        
        except ValueError:
            return False, "Invalid amount"
        
        return False, "Unknown error"


class AdvancedBank:
    """Advanced Bank System with improved backend"""
    
    def __init__(self, database: str = "bank_data.json"):
        self.db = BankDatabase(database)
        self.validator = BankValidator()
        self.current_user = None
    
    def _generate_account_number(self) -> str:
        """Generate unique account number"""
        while True:
            alpha = "".join(random.choices(string.ascii_uppercase, k=3))
            num = "".join(random.choices(string.digits, k=3))
            special = random.choice("!@#$%^&*")
            
            account_num = "".join(random.sample(alpha + num + special, 7))
            
            if not self.db.user_exists(account_num):
                return account_num
    
    def create_account(self, name: str, age: int, email: str, pin: str) -> Tuple[bool, str, Optional[Dict]]:
        """Create new account with validation"""
        
        # Validate all inputs
        is_valid, msg = self.validator.validate_name(name)
        if not is_valid:
            return False, msg, None
        
        is_valid, msg = self.validator.validate_age(age)
        if not is_valid:
            return False, msg, None
        
        is_valid, msg = self.validator.validate_email(email)
        if not is_valid:
            return False, msg, None
        
        is_valid, msg = self.validator.validate_pin(pin)
        if not is_valid:
            return False, msg, None
        
        # Create user object
        user = {
            "name": name.strip(),
            "age": int(age),
            "email": email.strip(),
            "pin": pin,  # In production, use hashing (bcrypt)
            "account_num": self._generate_account_number(),
            "balance": 0.0,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "transactions": []
        }
        
        if self.db.add_user(user):
            return True, "Account created successfully!", user
        
        return False, "Error creating account", None
    
    def login(self, account_num: str, pin: str) -> Tuple[bool, str]:
        """Login user"""
        user = self.db.find_user(account_num)
        
        if not user:
            return False, "Account not found"
        
        if user["pin"] != pin:
            return False, "Incorrect PIN"
        
        self.current_user = user
        user["last_login"] = datetime.now().isoformat()
        self.db.update_user(account_num, user)
        
        return True, f"Welcome back, {user['name']}!"
    
    def logout(self) -> Tuple[bool, str]:
        """Logout current user"""
        if self.current_user:
            self.current_user = None
            return True, "Logged out successfully"
        return False, "No user logged in"
    
    def deposit(self, amount: float) -> Tuple[bool, str, Optional[float]]:
        """Deposit money"""
        if not self.current_user:
            return False, "Please login first", None
        
        is_valid, msg = self.validator.validate_amount(amount, "deposit")
        if not is_valid:
            return False, msg, None
        
        self.current_user["balance"] += amount
        self.current_user["transactions"].append({
            "type": "deposit",
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "balance_after": self.current_user["balance"]
        })
        
        self.db.update_user(self.current_user["account_num"], self.current_user)
        
        return True, f"Deposited Rs {amount}", self.current_user["balance"]
    
    def withdraw(self, amount: float) -> Tuple[bool, str, Optional[float]]:
        """Withdraw money"""
        if not self.current_user:
            return False, "Please login first", None
        
        is_valid, msg = self.validator.validate_amount(
            amount, "withdraw", self.current_user["balance"]
        )
        if not is_valid:
            return False, msg, None
        
        self.current_user["balance"] -= amount
        self.current_user["transactions"].append({
            "type": "withdrawal",
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "balance_after": self.current_user["balance"]
        })
        
        self.db.update_user(self.current_user["account_num"], self.current_user)
        
        return True, f"Withdrawn Rs {amount}", self.current_user["balance"]
    
    def get_balance(self) -> Optional[float]:
        """Get current balance"""
        if self.current_user:
            return self.current_user["balance"]
        return None
    
    def get_user_details(self) -> Optional[Dict]:
        """Get current user details"""
        if self.current_user:
            return {
                "name": self.current_user["name"],
                "age": self.current_user["age"],
                "email": self.current_user["email"],
                "account_num": self.current_user["account_num"],
                "balance": self.current_user["balance"],
                "created_at": self.current_user.get("created_at", "N/A"),
                "last_login": self.current_user.get("last_login", "N/A")
            }
        return None
    
    def update_details(self, name: str = None, age: int = None, 
                      email: str = None) -> Tuple[bool, str]:
        """Update user details"""
        if not self.current_user:
            return False, "Please login first"
        
        updates = {}
        
        if name:
            is_valid, msg = self.validator.validate_name(name)
            if not is_valid:
                return False, msg
            updates["name"] = name.strip()
        
        if age:
            is_valid, msg = self.validator.validate_age(age)
            if not is_valid:
                return False, msg
            updates["age"] = int(age)
        
        if email:
            is_valid, msg = self.validator.validate_email(email)
            if not is_valid:
                return False, msg
            updates["email"] = email.strip()
        
        if updates:
            self.current_user.update(updates)
            self.db.update_user(self.current_user["account_num"], self.current_user)
            return True, "Details updated successfully"
        
        return False, "No changes made"
    
    def delete_account(self, confirmation: bool = False) -> Tuple[bool, str]:
        """Delete account"""
        if not self.current_user:
            return False, "Please login first"
        
        if not confirmation:
            return False, "Please confirm deletion"
        
        account_num = self.current_user["account_num"]
        if self.db.remove_user(account_num):
            self.current_user = None
            return True, "Account deleted successfully"
        
        return False, "Error deleting account"
    
    def get_transactions(self, limit: int = 10) -> List[Dict]:
        """Get transaction history"""
        if not self.current_user:
            return []
        
        transactions = self.current_user.get("transactions", [])
        return sorted(transactions, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    def get_account_summary(self) -> Optional[Dict]:
        """Get account summary"""
        if not self.current_user:
            return None
        
        transactions = self.get_transactions(10)
        total_deposits = sum(t["amount"] for t in transactions if t["type"] == "deposit")
        total_withdrawals = sum(t["amount"] for t in transactions if t["type"] == "withdrawal")
        
        return {
            "name": self.current_user["name"],
            "account_num": self.current_user["account_num"],
            "balance": self.current_user["balance"],
            "total_transactions": len(self.current_user.get("transactions", [])),
            "recent_deposits": total_deposits,
            "recent_withdrawals": total_withdrawals,
            "created_at": self.current_user.get("created_at", "N/A")
        }
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in"""
        return self.current_user is not None