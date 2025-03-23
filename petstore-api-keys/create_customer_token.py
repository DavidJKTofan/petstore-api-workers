import time
import enum
import json
import argparse
import os
import sys
from authlib.jose import jwt
from typing import Dict, List, Optional, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from datetime import datetime

class CustomerType(enum.Enum):
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"

class Customer:
    def __init__(
        self,
        username: str,
        customer_type: CustomerType,
        email: str,
        company: Optional[str] = None,
        subscription_tier: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ):
        self.username = username
        self.customer_type = customer_type
        self.email = email
        self.company = company
        self.subscription_tier = subscription_tier
        self.additional_metadata = additional_metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert customer data to dictionary for JWT payload"""
        return {
            "username": self.username,
            "customer_type": self.customer_type.value,
            "email": self.email,
            "company": self.company,
            "subscription_tier": self.subscription_tier,
            **self.additional_metadata
        }

class TokenGenerator:
    def __init__(self, private_key_path: str, issuer: str, audience: str, key_id: str, algorithm: str = "ES256"):
        """Initialize the token generator

        Args:
            private_key_path: Path to the private key file
            issuer: JWT issuer claim
            audience: JWT audience claim
            key_id: Key ID for JWT header
            algorithm: JWT algorithm (default: ES256)
        """
        self.private_key = self._load_private_key(private_key_path)
        self.issuer = issuer
        self.audience = audience
        self.algorithm = algorithm
        self.key_id = key_id
        self.customers: Dict[str, Customer] = {}
    
    def _load_private_key(self, private_key_path: str) -> bytes:
        """Load and validate private key from file
        
        Args:
            private_key_path: Path to the private key file
            
        Returns:
            Private key in PEM format
            
        Raises:
            FileNotFoundError: If private key file doesn't exist
            ValueError: If private key format is invalid
        """
        if not os.path.exists(private_key_path):
            print(f"Error: Private key file not found: {private_key_path}")
            print("Please make sure you've created the key files as described in the README.")
            sys.exit(1)
            
        try:
            # First attempt: Try loading the key directly
            with open(private_key_path, "rb") as key_file:
                private_key = key_file.read()
                
            # Try to parse it as a PEM EC private key to validate
            try:
                # This is just for validation, we'll still use the original PEM
                serialization.load_pem_private_key(
                    private_key, 
                    password=None, 
                    backend=default_backend()
                )
                return private_key
            except ValueError as e:
                print(f"Warning: Initial key validation failed: {e}")
                print("Attempting alternative key loading methods...")
            
            # Second attempt: Try parsing as text and reformatting
            with open(private_key_path, "r") as key_file:
                key_text = key_file.read()
            
            # Check if it's a JSON key from mkjwk.org
            if key_text.strip().startswith('{'):
                try:
                    key_data = json.loads(key_text)
                    if 'd' in key_data:
                        print("Detected JSON format key from mkjwk.org")
                        print("Please use the PEM format key instead (from the 'Private Key' field)")
                        sys.exit(1)
                except json.JSONDecodeError:
                    pass
            
            # If we got here, the key format is not supported
            print("Error: Unsupported private key format.")
            print("Please make sure the private key is in valid PEM format.")
            print("You can generate one at https://mkjwk.org/ (select 'EC' algorithm).")
            print("Use the 'Private Key' field content for your private-key.pem file.")
            sys.exit(1)
            
        except Exception as e:
            print(f"Error loading private key: {e}")
            print("Please check the README for instructions on creating valid keys.")
            sys.exit(1)
    
    def add_customer(self, customer: Customer) -> None:
        """Add a customer to the generator"""
        self.customers[customer.username] = customer
    
    def generate_token(self, username: str, expiration_seconds: int = 3600) -> str:
        """Generate a JWT token for a customer

        Args:
            username: Customer username
            expiration_seconds: Token validity period in seconds (default: 1 hour)
        
        Returns:
            JWT token as string
        
        Raises:
            ValueError: If customer not found
        """
        if username not in self.customers:
            raise ValueError(f"Customer {username} not found")
        
        customer = self.customers[username]
        
        header = {
            "alg": self.algorithm,
            "kid": self.key_id
        }
        
        # Standard JWT claims + customer and customer_type as top-level claims
        payload = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": username,
            "exp": int(time.time()) + expiration_seconds, # expiration time
            "iat": int(time.time()), # issued at
            # Add username and customer_type as top-level claims
            "username": username,
            "customer_type": customer.customer_type.value,
            # Include full customer data, nested values
            "customer": customer.to_dict()
        }
        
        try:
            # Encode the JWT
            token = jwt.encode(header, payload, self.private_key)
            return token.decode("utf-8")
        except Exception as e:
            print(f"Error generating token: {e}")
            print("This may be due to an incompatible private key format.")
            print("Please ensure your private key is a valid EC key for ES256 algorithm.")
            sys.exit(1)
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token (for demo purposes only)
        
        Note: For production, use proper signature validation with public key
        
        Args:
            token: JWT token to validate
            
        Returns:
            Decoded token payload
        """
        try:
            # In a real implementation, you would validate the signature using the public key
            # This is just for demo purposes
            decoded = jwt.decode(token, self.private_key)
            return decoded
        except Exception as e:
            print(f"Error validating token: {e}")
            return {"error": str(e)}

def save_token_to_file(token: str, username: str, customer_type: str, output_dir: str) -> str:
    """Save a token to a file in the specified directory
    
    Args:
        token: The JWT token to save
        username: The customer username
        customer_type: The customer type
        output_dir: The directory to save the token to
        
    Returns:
        The path to the saved token file
    """
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create a filename based on username, customer type, and timestamp
    timestamp = int(time.time())
    # Add human readable date/time
    readable_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{username}_{customer_type}_{readable_date}.jwt"
    file_path = os.path.join(output_dir, filename)
    
    # Write the token to the file
    with open(file_path, "w") as f:
        f.write(token)
    
    return file_path

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate JWT tokens for pet store customers")
    
    # Token generator parameters
    parser.add_argument("--key-path", default="private-key.pem", help="Path to the private key file")
    parser.add_argument("--issuer", default="https://petstore.automatic-demo.com", help="JWT issuer claim")
    parser.add_argument("--audience", default="petstore", help="JWT audience claim")
    parser.add_argument("--key-id", default="petstore-ec256", help="Key ID for JWT header")
    
    # Customer parameters
    parser.add_argument("--username", help="Customer username")
    parser.add_argument("--customer-type", choices=["premium", "standard", "free"], help="Customer type")
    parser.add_argument("--email", help="Customer email")
    parser.add_argument("--company", help="Customer company")
    parser.add_argument("--subscription-tier", help="Customer subscription tier")
    
    # Token parameters
    parser.add_argument("--expiration", type=int, default=3600, help="Token expiration time in seconds")
    parser.add_argument("--additional-metadata", type=str, help="Additional metadata as JSON string")
    
    # Output parameters
    parser.add_argument("--output-dir", default=None, help="Directory to save token files (if not provided, tokens will only be printed)")
    
    return parser.parse_args()

# Usage example
if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    
    try:
        # Initialize token generator with command line arguments or defaults
        token_generator = TokenGenerator(
            private_key_path=args.key_path,
            issuer=args.issuer,
            audience=args.audience,
            key_id=args.key_id
        )
        
        # Check if command line arguments for a single customer were provided
        if args.username and args.customer_type and args.email:
            # Parse customer type
            customer_type_value = args.customer_type.upper()
            if not hasattr(CustomerType, customer_type_value):
                print(f"Invalid customer type: {args.customer_type}")
                exit(1)
            
            customer_type = getattr(CustomerType, customer_type_value)
            
            # Parse additional metadata
            additional_metadata = {}
            if args.additional_metadata:
                try:
                    additional_metadata = json.loads(args.additional_metadata)
                except json.JSONDecodeError:
                    print(f"Invalid JSON for additional metadata: {args.additional_metadata}")
                    exit(1)
            
            # Create customer from command line arguments
            customer = Customer(
                username=args.username,
                customer_type=customer_type,
                email=args.email,
                company=args.company,
                subscription_tier=args.subscription_tier,
                additional_metadata=additional_metadata
            )
            
            # Add customer to generator
            token_generator.add_customer(customer)
            
            # Generate token
            token = token_generator.generate_token(args.username, expiration_seconds=args.expiration)
            print(f"\nGenerated token for {args.username} ({args.customer_type}):")
            print(token)
            
            # Save token to file if output directory is provided
            if args.output_dir:
                file_path = save_token_to_file(token, args.username, args.customer_type, args.output_dir)
                print(f"Token saved to: {file_path}")
            
            # Validate token
            payload = token_generator.validate_token(token)
            print(f"\nValidated token payload for {args.username}:")
            print(payload.get("customer"))
        
        else:
            # Use example customers if no command line arguments were provided
            customers = [
                Customer(
                    username="user1",
                    customer_type=CustomerType.PREMIUM,
                    email="user1@example.com",
                    company="Acme Corp",
                    subscription_tier="enterprise",
                    additional_metadata={"rate_limit": 1000, "api_access_level": "full"}
                ),
                Customer(
                    username="user2",
                    customer_type=CustomerType.STANDARD,
                    email="user2@example.com",
                    company="Beta Inc",
                    subscription_tier="professional",
                    additional_metadata={"rate_limit": 500, "api_access_level": "standard"}
                ),
                Customer(
                    username="user3",
                    customer_type=CustomerType.FREE,
                    email="user3@example.com",
                    additional_metadata={"rate_limit": 100, "api_access_level": "basic"}
                )
            ]
            
            # Add customers to token generator
            for customer in customers:
                token_generator.add_customer(customer)
            
            # Generate tokens for each customer
            for customer in customers:
                token = token_generator.generate_token(customer.username)
                print(f"\nGenerated token for {customer.username} ({customer.customer_type.value}):")
                print(token)
                
                # Save token to file if output directory is provided
                if args.output_dir:
                    file_path = save_token_to_file(
                        token, 
                        customer.username, 
                        customer.customer_type.value, 
                        args.output_dir
                    )
                    print(f"Token saved to: {file_path}")
                
                # Validate token (demo only)
                payload = token_generator.validate_token(token)
                print(f"\nValidated token payload for {customer.username}:")
                print(payload.get("customer"))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 