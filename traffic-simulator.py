import httpx
import random
import time
import json
import logging
from datetime import datetime, timedelta
import argparse
from typing import Dict, List, Any, Optional, Tuple
import string
from concurrent.futures import ThreadPoolExecutor
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("petstore_simulator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class PetstoreTrafficSimulator:
    """Simulates real-life traffic to the Petstore API using HTTP/2"""
    
    def __init__(self, base_url: str, api_key: str, min_pets: int = 10, min_users: int = 5, min_orders: int = 3):
        """
        Initialize the simulator
        
        Args:
            base_url: Base URL of the Petstore API
            api_key: API key for authentication
            min_pets: Minimum number of pets to maintain
            min_users: Minimum number of users to maintain
            min_orders: Minimum number of orders to maintain
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.min_pets = min_pets
        self.min_users = min_users
        self.min_orders = min_orders
        
        # List of common user agents to rotate through
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ]
        
        # Create an HTTP/2 enabled client
        self.session = httpx.Client(http2=True)
        self.session.headers.update({"api-key-petstore": api_key, "Content-Type": "application/json"})
        
        # Track entity IDs we've created
        self.pet_ids = []
        self.user_ids = []
        self.order_ids = []
        
        # Track usernames for user operations
        self.usernames = []
        
        # Pet attributes for random generation
        self.pet_names = ["Buddy", "Max", "Bella", "Luna", "Charlie", "Lucy", "Cooper", "Daisy", 
                          "Rocky", "Sadie", "Duke", "Molly", "Bear", "Maggie", "Tucker", "Sophie"]
        self.pet_statuses = ["available", "pending", "sold"]
        self.pet_categories = [
            {"id": 1, "name": "Dogs"},
            {"id": 2, "name": "Cats"},
            {"id": 3, "name": "Birds"},
            {"id": 4, "name": "Fish"},
            {"id": 5, "name": "Reptiles"}
        ]
        self.pet_tags = [
            {"id": 1, "name": "friendly"},
            {"id": 2, "name": "trained"},
            {"id": 3, "name": "playful"},
            {"id": 4, "name": "colorful"},
            {"id": 5, "name": "exotic"},
            {"id": 6, "name": "rare"},
            {"id": 7, "name": "puppy"},
            {"id": 8, "name": "kitten"},
            {"id": 9, "name": "senior"},
            {"id": 10, "name": "quiet"}
        ]
        
        # Order statuses
        self.order_statuses = ["placed", "approved", "delivered"]
        
        # Default timeout for all requests (in seconds)
        self.timeout = 10
        
        # Add protected ranges for base data
        self.protected_pet_ids = set(range(1, 6))  # Protect pets 1-5
        self.protected_user_ids = set(range(1, 6))  # Protect users 1-5
        self.protected_order_ids = set(range(1, 6))  # Protect orders 1-5
        
        # Initialize the system state
        self.initialize()
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent from the list"""
        return random.choice(self.user_agents)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[httpx.Response]:
        """
        Make an HTTP request with error handling and random user agent
        
        Args:
            method: HTTP method (get, post, put, delete)
            endpoint: API endpoint (will be appended to base_url)
            **kwargs: Additional arguments to pass to the request
            
        Returns:
            Response object if successful, None otherwise
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Ensure headers are properly set for all requests
        headers = kwargs.get('headers', {})
        headers.update({
            "User-Agent": self._get_random_user_agent(),
            "Accept": "application/json",
            "api-key-petstore": self.api_key,  # Ensure API key is always included
            "Content-Type": "application/json"
        })
        kwargs['headers'] = headers
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
            
        try:
            logger.debug(f"Making {method.upper()} request to {url}")
            logger.debug(f"Headers: {headers}")
            
            response = getattr(self.session, method.lower())(url, **kwargs)
            
            # Log the actual response for debugging
            logger.debug(f"{method.upper()} {url} - Status: {response.status_code}")
            if response.content:  # Only try to log content if it exists
                try:
                    logger.debug(f"Response content: {response.json()}")
                except:
                    logger.debug(f"Response content: {response.text}")
            
            # For DELETE requests, accept both 200 and 204 status codes
            if method.lower() == 'delete' and response.status_code in [200, 204]:
                return response
            
            response.raise_for_status()
            return response
        
        except httpx.TimeoutException:
            logger.error(f"Request timeout: {method} {url}")
            return None
        except httpx.ConnectError:
            logger.error(f"Connection error: {method} {url}")
            return None
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else "unknown"
            response_text = e.response.text if hasattr(e, 'response') and e.response.text else "No response body"
            logger.error(f"HTTP error {status_code}: {method} {url} - Response: {response_text}")
            
            # For 404 errors, we may need to clean up our tracking lists
            if hasattr(e, 'response') and e.response.status_code == 404:
                if 'pet' in endpoint and any(str(pet_id) in endpoint for pet_id in self.pet_ids):
                    # Extract pet_id from endpoint
                    for pet_id in self.pet_ids[:]:  # Create a copy of the list to iterate
                        if str(pet_id) in endpoint:
                            self.pet_ids.remove(pet_id)
                            logger.info(f"Removed non-existent pet ID {pet_id} from tracking")
                            break
                elif 'user' in endpoint and any(username in endpoint for username in self.usernames):
                    # Extract username from endpoint
                    for username in self.usernames:
                        if username in endpoint:
                            if username in self.usernames:
                                self.usernames.remove(username)
                            break
                elif 'order' in endpoint and any(str(order_id) in endpoint for order_id in self.order_ids):
                    # Extract order_id from endpoint
                    for order_id in self.order_ids:
                        if str(order_id) in endpoint:
                            if order_id in self.order_ids:
                                self.order_ids.remove(order_id)
                            break
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {method} {url} - {str(e)}")
            return None
    
    def initialize(self):
        """Initialize system state by ensuring minimum data is present"""
        logger.info("Initializing system state...")
        
        # Get current entity counts
        self.refresh_state()
        
        # Create minimum entities if needed
        self.ensure_minimum_entities()
        logger.info("Initialization complete")
    
    def refresh_state(self):
        """Refresh our understanding of what's in the database by checking counts through API"""
        # Get inventory which includes pet counts by status
        inventory_response = self._make_request("get", "/store/inventory")
        if inventory_response:
            inventory = inventory_response.json()
            # Total pets is sum of all status counts
            total_pets = sum(count for status, count in inventory.items() if isinstance(count, int))
            logger.info(f"Found {total_pets} total pets in inventory")
            
            # Get actual pet IDs for our tracking
            for status in self.pet_statuses:
                response = self._make_request("get", f"/pet/findByStatus?status={status}")
                if response:
                    pets = response.json()
                    # Extract pet IDs if not already in our list
                    for pet in pets:
                        if "id" in pet and pet["id"] not in self.pet_ids:
                            self.pet_ids.append(pet["id"])
        
        # For users and orders, we'll do minimal checks just to see if we need to create more
        # Try a few sequential IDs for orders
        order_found = False
        for i in range(1, 4):  # Just check first few orders
            response = self._make_request("get", f"/store/order/{i}")
            if response:
                order_found = True
                order_data = response.json()
                if "id" in order_data and order_data["id"] not in self.order_ids:
                    self.order_ids.append(order_data["id"])
        
        # Try a few sequential usernames
        user_found = False
        for i in range(1, 4):  # Just check first few users
            response = self._make_request("get", f"/user/user{i}")
            if response:
                user_found = True
                user_data = response.json()
                if "username" in user_data and user_data["username"] not in self.usernames:
                    self.usernames.append(user_data["username"])
        
        logger.info(
            f"Current state - Pets: {len(self.pet_ids)}, "
            f"Users: {len(self.usernames)} {'(some existing)' if user_found else '(none found)'}, "
            f"Orders: {len(self.order_ids)} {'(some existing)' if order_found else '(none found)'}"
        )
        
        # Add debug logging for protected entities
        logger.debug(f"Protected entities - Pets: {sorted(self.protected_pet_ids)}, "
                    f"Users: {sorted(self.protected_user_ids)}, "
                    f"Orders: {sorted(self.protected_order_ids)}")
    
    def ensure_minimum_entities(self):
        """Ensure we have the minimum required entities"""
        # Check and create minimum pets
        pet_count_to_create = max(0, self.min_pets - len(self.pet_ids))
        if pet_count_to_create > 0:
            logger.info(f"Creating {pet_count_to_create} new pets to meet minimum")
            for _ in range(pet_count_to_create):
                self.create_random_pet()
        
        # Check and create minimum users
        user_count_to_create = max(0, self.min_users - len(self.usernames))
        if user_count_to_create > 0:
            logger.info(f"Creating {user_count_to_create} new users to meet minimum")
            for _ in range(user_count_to_create):
                self.create_random_user()
        
        # Check and create minimum orders
        order_count_to_create = max(0, self.min_orders - len(self.order_ids))
        if order_count_to_create > 0 and len(self.pet_ids) > 0:
            logger.info(f"Creating {order_count_to_create} new orders to meet minimum")
            for _ in range(order_count_to_create):
                self.create_random_order()
    
    def generate_random_string(self, length: int = 8) -> str:
        """Generate a random string of fixed length"""
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for _ in range(length))
    
    def create_random_pet(self) -> Optional[int]:
        """Create a random pet and return its ID if successful"""
        # Generate a random pet
        pet_data = {
            "name": random.choice(self.pet_names),
            "photoUrls": [f"https://example.com/pets/{self.generate_random_string()}.jpg"],
            "status": random.choice(self.pet_statuses),
            "category": random.choice(self.pet_categories),
            "tags": random.sample(self.pet_tags, k=random.randint(1, 3))
        }
        
        # Send POST request
        response = self._make_request("post", "/pet", json=pet_data)
        if not response:
            return None
            
        # Extract pet ID from response
        new_pet = response.json()
        if "id" in new_pet:
            pet_id = new_pet["id"]
            self.pet_ids.append(pet_id)
            logger.info(f"Created new pet with ID: {pet_id}, name: {pet_data['name']}")
            return pet_id
        
        logger.warning(f"Created pet but couldn't find ID in response: {new_pet}")
        return None
    
    def update_pet(self, pet_id: int) -> bool:
        """Update an existing pet"""
        # First get the current pet data
        response = self._make_request("get", f"/pet/{pet_id}")
        if not response:
            return False
            
        pet_data = response.json()
        
        # Update some fields
        pet_data["status"] = random.choice(self.pet_statuses)
        pet_data["name"] = random.choice(self.pet_names)
        if random.random() < 0.3:  # 30% chance to change category
            pet_data["category"] = random.choice(self.pet_categories)
        
        # Send the update
        response = self._make_request("put", "/pet", json=pet_data)
        if not response:
            return False
            
        logger.info(f"Updated pet with ID: {pet_id}")
        return True
    
    def delete_pet(self, pet_id: int) -> bool:
        """Delete a pet by ID"""
        try:
            # Ensure we're sending the API key in headers
            response = self._make_request("delete", f"/pet/{pet_id}")
            
            # Consider both 200 and 204 as success for DELETE
            if response is not None and response.status_code in [200, 204]:
                if pet_id in self.pet_ids:
                    self.pet_ids.remove(pet_id)
                    logger.info(f"Successfully deleted pet with ID: {pet_id}")
                return True
            
            if response is None:
                logger.error(f"Delete request failed for pet {pet_id} - no response")
            else:
                logger.error(f"Delete request failed for pet {pet_id} - status code: {response.status_code}")
            return False
        
        except Exception as e:
            logger.error(f"Error deleting pet {pet_id}: {str(e)}")
            return False
    
    def get_pet_by_id(self, pet_id: int) -> Optional[Dict]:
        """Get a pet by ID"""
        response = self._make_request("get", f"/pet/{pet_id}")
        if not response:
            return None
            
        pet_data = response.json()
        logger.info(f"Retrieved pet with ID: {pet_id}")
        return pet_data
    
    def find_pets_by_status(self, status: str) -> List[Dict]:
        """Find pets by status"""
        response = self._make_request("get", f"/pet/findByStatus?status={status}")
        if not response:
            return []
            
        pets = response.json()
        logger.info(f"Found {len(pets)} pets with status: {status}")
        return pets
    
    def find_pets_by_tags(self, tags: List[str]) -> List[Dict]:
        """Find pets by tags"""
        # Build URL with multiple tags
        params = []
        for tag in tags:
            params.append(f"tags={tag}")
        url = "/pet/findByTags?" + "&".join(params) if params else "/pet/findByTags"
            
        response = self._make_request("get", url)
        if not response:
            return []
            
        pets = response.json()
        logger.info(f"Found {len(pets)} pets with tags: {', '.join(tags)}")
        return pets
    
    def create_random_user(self) -> Optional[str]:
        """Create a random user and return username if successful"""
        # Generate random username
        username = f"user_{self.generate_random_string()}"
        
        # Generate user data
        user_data = {
            "username": username,
            "firstName": f"First_{self.generate_random_string(4)}",
            "lastName": f"Last_{self.generate_random_string(4)}",
            "email": f"{username}@example.com",
            "password": "password123",
            "phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "userStatus": random.randint(0, 2)
        }
        
        # Send POST request
        response = self._make_request("post", "/user", json=user_data)
        if not response:
            return None
        
        # Track username
        self.usernames.append(username)
        logger.info(f"Created new user with username: {username}")
        return username
    
    def update_user(self, username: str) -> bool:
        """Update an existing user"""
        # Generate update data (partial)
        user_data = {
            "firstName": f"Updated_{self.generate_random_string(4)}",
            "lastName": f"Updated_{self.generate_random_string(4)}",
            "email": f"updated_{username}@example.com",
            "phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
        }
        
        # Send PUT request
        response = self._make_request("put", f"/user/{username}", json=user_data)
        if not response:
            return False
        
        logger.info(f"Updated user: {username}")
        return True
    
    def delete_user(self, username: str) -> bool:
        """Delete a user by username"""
        response = self._make_request("delete", f"/user/{username}")
        if not response:
            return False
        
        # Remove from our list if successful
        if username in self.usernames:
            self.usernames.remove(username)
            
        logger.info(f"Deleted user: {username}")
        return True
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get a user by username"""
        response = self._make_request("get", f"/user/{username}")
        if not response:
            return None
        
        user_data = response.json()
        logger.info(f"Retrieved user: {username}")
        return user_data
    
    def login_user(self, username: str, password: str = "password123") -> bool:
        """Login as a user"""
        response = self._make_request("get", f"/user/login?username={username}&password={password}")
        if not response:
            return False
        
        logger.info(f"Logged in as user: {username}")
        return True
    
    def logout_user(self) -> bool:
        """Logout current user"""
        response = self._make_request("get", "/user/logout")
        if not response:
            return False
        
        logger.info("Logged out user")
        return True
    
    def create_random_order(self) -> Optional[int]:
        """Create a random order and return order ID if successful"""
        # Need at least one pet to create an order
        if not self.pet_ids:
            logger.warning("Can't create order: no pets available")
            return None
            
        # Generate order data
        pet_id = random.choice(self.pet_ids)
        ship_date = (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat() + "Z"
        
        order_data = {
            "petId": pet_id,
            "quantity": random.randint(1, 3),
            "shipDate": ship_date,
            "status": random.choice(self.order_statuses),
            "complete": random.choice([True, False])
        }
        
        # Send POST request
        response = self._make_request("post", "/store/order", json=order_data)
        if not response:
            return None
        
        # Extract order ID from response
        new_order = response.json()
        if "id" in new_order:
            order_id = new_order["id"]
            self.order_ids.append(order_id)
            logger.info(f"Created new order with ID: {order_id} for pet ID: {pet_id}")
            return order_id
        
        logger.warning(f"Created order but couldn't find ID in response: {new_order}")
        return None
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get an order by ID"""
        response = self._make_request("get", f"/store/order/{order_id}")
        if not response:
            return None
        
        order_data = response.json()
        logger.info(f"Retrieved order with ID: {order_id}")
        return order_data
    
    def delete_order(self, order_id: int) -> bool:
        """Delete an order by ID"""
        response = self._make_request("delete", f"/store/order/{order_id}")
        if not response:
            return False
        
        # Remove from our list if successful
        if order_id in self.order_ids:
            self.order_ids.remove(order_id)
            
        logger.info(f"Deleted order with ID: {order_id}")
        return True
    
    def get_inventory(self) -> Optional[Dict]:
        """Get store inventory"""
        response = self._make_request("get", "/store/inventory")
        if not response:
            return None
        
        inventory = response.json()
        logger.info(f"Retrieved inventory: {inventory}")
        return inventory
    
    def simulate_random_operation(self):
        """Simulate a random API operation"""
        operations = [
            # Pet operations - weighted more heavily
            self.op_create_pet,
            self.op_update_pet,
            self.op_delete_pet,
            self.op_get_pet,
            self.op_find_pets_by_status,
            self.op_find_pets_by_tags,
            
            # User operations
            self.op_create_user,
            self.op_update_user,
            self.op_delete_user,
            self.op_get_user,
            self.op_login_user,
            self.op_logout_user,
            
            # Order operations
            self.op_create_order,
            self.op_get_order,
            self.op_delete_order,
            self.op_get_inventory
        ]
        
        # Add weight to certain operations by duplicating them in the list
        weighted_operations = operations + [
            # Add more weight to common operations
            self.op_get_pet,
            self.op_get_pet,
            self.op_find_pets_by_status,
            self.op_find_pets_by_status,
            self.op_get_inventory,
            self.op_get_inventory
        ]
        
        # Pick and execute a random operation
        operation = random.choice(weighted_operations)
        operation()
    
    # Operation methods - these wrap the API methods with appropriate checks
    
    def op_create_pet(self):
        self.create_random_pet()
    
    def op_update_pet(self):
        if self.pet_ids:
            self.update_pet(random.choice(self.pet_ids))
        else:
            self.create_random_pet()
    
    def op_delete_pet(self):
        """Operation to delete a pet with improved handling"""
        if not self.pet_ids:
            logger.info("No pets available to delete")
            return
        
        # Filter out protected pet IDs from deletion candidates
        deletable_pets = [pid for pid in self.pet_ids if pid not in self.protected_pet_ids]
        
        if not deletable_pets:
            logger.info("No non-protected pets available to delete")
            self.create_random_pet()
            return
        
        if len(deletable_pets) <= (self.min_pets - len(self.protected_pet_ids)):
            logger.info(f"Not deleting pet - at minimum threshold for non-protected pets")
            # Create a new pet instead
            self.create_random_pet()
            return
        
        # Select a pet to delete from non-protected pets
        pet_id = random.choice(deletable_pets)
        logger.debug(f"Attempting to delete pet {pet_id}")
        
        if self.delete_pet(pet_id):
            logger.info(f"Successfully deleted pet {pet_id}. Remaining pets: {len(self.pet_ids)}")
        else:
            logger.warning(f"Failed to delete pet {pet_id} - will remove from tracking list")
            if pet_id in self.pet_ids:
                self.pet_ids.remove(pet_id)
    
    def op_get_pet(self):
        if self.pet_ids:
            self.get_pet_by_id(random.choice(self.pet_ids))
        else:
            self.create_random_pet()
    
    def op_find_pets_by_status(self):
        status = random.choice(self.pet_statuses)
        self.find_pets_by_status(status)
    
    def op_find_pets_by_tags(self):
        # Select 1-3 random tags
        tags = [tag["name"] for tag in random.sample(self.pet_tags, k=random.randint(1, 3))]
        self.find_pets_by_tags(tags)
    
    def op_create_user(self):
        self.create_random_user()
    
    def op_update_user(self):
        if self.usernames:
            self.update_user(random.choice(self.usernames))
        else:
            self.create_random_user()
    
    def op_delete_user(self):
        """Operation to delete a user with protection for base users"""
        if not self.usernames:
            logger.info("No users available to delete")
            return
        
        # Filter out protected users (assuming usernames follow pattern "user1", "user2", etc.)
        protected_usernames = {f"user{i}" for i in self.protected_user_ids}
        deletable_users = [u for u in self.usernames if u not in protected_usernames]
        
        if not deletable_users:
            logger.info("No non-protected users available to delete")
            self.create_random_user()
            return
        
        if len(deletable_users) <= (self.min_users - len(self.protected_user_ids)):
            logger.info(f"Not deleting user - at minimum threshold for non-protected users")
            self.create_random_user()
            return
        
        # Select a user to delete from non-protected users
        username = random.choice(deletable_users)
        self.delete_user(username)
    
    def op_get_user(self):
        if self.usernames:
            self.get_user_by_username(random.choice(self.usernames))
        else:
            self.create_random_user()
    
    def op_login_user(self):
        if self.usernames:
            self.login_user(random.choice(self.usernames))
        else:
            self.create_random_user()
    
    def op_logout_user(self):
        self.logout_user()
    
    def op_create_order(self):
        self.create_random_order()
    
    def op_get_order(self):
        if self.order_ids:
            self.get_order_by_id(random.choice(self.order_ids))
        else:
            self.create_random_order()
    
    def op_delete_order(self):
        """Operation to delete an order with protection for base orders"""
        if not self.order_ids:
            logger.info("No orders available to delete")
            return
        
        # Filter out protected order IDs from deletion candidates
        deletable_orders = [oid for oid in self.order_ids if oid not in self.protected_order_ids]
        
        if not deletable_orders:
            logger.info("No non-protected orders available to delete")
            self.create_random_order()
            return
        
        if len(deletable_orders) <= (self.min_orders - len(self.protected_order_ids)):
            logger.info(f"Not deleting order - at minimum threshold for non-protected orders")
            self.create_random_order()
            return
        
        # Select an order to delete from non-protected orders
        order_id = random.choice(deletable_orders)
        self.delete_order(order_id)
    
    def op_get_inventory(self):
        self.get_inventory()
    
    def get_table_counts(self):
        """Get actual table row counts if the endpoint exists"""
        response = self._make_request("get", "/system/counts")
        if response:
            counts = response.json()
            logger.info(f"Database table counts: {json.dumps(counts, indent=2)}")
            return counts
        return None
    
    def run_simulation(self, duration_minutes: int = 10, operations_per_minute: int = 30):
        """
        Run the simulation for a specified duration
        
        Args:
            duration_minutes: How long to run the simulation (in minutes)
            operations_per_minute: Approximate number of operations to perform per minute
        """
        logger.info(f"Starting simulation for {duration_minutes} minutes at ~{operations_per_minute} ops/min")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        operation_count = 0
        
        # Calculate sleep time between operations
        sleep_time = 60 / operations_per_minute
        
        try:
            while datetime.now() < end_time:
                # Perform a random operation
                self.simulate_random_operation()
                operation_count += 1
                
                # Periodically ensure minimum entities
                if operation_count % 50 == 0:
                    self.ensure_minimum_entities()
                    
                # Sleep between operations
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        
        logger.info(f"Simulation completed with {operation_count} operations")
        self.generate_summary_report()
    
    def run_parallel_simulation(self, duration_minutes: int = 10, 
                              operations_per_minute: int = 30, 
                              concurrency: int = 3):
        """
        Run simulation with multiple concurrent threads
        
        Args:
            duration_minutes: How long to run the simulation (in minutes)
            operations_per_minute: Approximate operations per minute per thread
            concurrency: Number of concurrent threads
        """
        logger.info(f"Starting parallel simulation with {concurrency} threads for {duration_minutes} minutes")
        
        # Adjust sleep time between operations for each thread
        sleep_time = 60 / operations_per_minute
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        def worker():
            operation_count = 0
            try:
                while datetime.now() < end_time:
                    self.simulate_random_operation()
                    operation_count += 1
                    time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Worker thread error: {e}")
            return operation_count
        
        # Create and start worker threads
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker) for _ in range(concurrency)]
            
            try:
                # Periodically check on min entities
                while datetime.now() < end_time:
                    time.sleep(10)  # Check every 10 seconds
                    self.ensure_minimum_entities()
            except KeyboardInterrupt:
                logger.info("Parallel simulation interrupted by user")
        
        # Get total operation count
        total_operations = sum(future.result() for future in futures)
        logger.info(f"Parallel simulation completed with {total_operations} total operations")
        self.generate_summary_report()

    def __del__(self):
        """Clean up resources when the object is destroyed"""
        # Close the requests session
        if hasattr(self, 'session'):
            self.session.close()

    def generate_summary_report(self):
        """Generate a summary report of operations and errors"""
        # Get all logs from the file
        error_count = 0
        operation_counts = {
            'pet': {'create': 0, 'update': 0, 'delete': 0, 'get': 0},
            'user': {'create': 0, 'update': 0, 'delete': 0, 'get': 0},
            'order': {'create': 0, 'update': 0, 'delete': 0, 'get': 0}
        }
        
        try:
            with open("petstore_simulator.log", "r") as f:
                for line in f:
                    # Count errors
                    if "ERROR" in line:
                        error_count += 1
                    
                    # Count operations
                    if "Created new pet" in line:
                        operation_counts['pet']['create'] += 1
                    elif "Updated pet" in line:
                        operation_counts['pet']['update'] += 1
                    elif "Deleted pet" in line:
                        operation_counts['pet']['delete'] += 1
                    elif "Retrieved pet" in line:
                        operation_counts['pet']['get'] += 1
                    elif "Created new user" in line:
                        operation_counts['user']['create'] += 1
                    elif "Updated user" in line:
                        operation_counts['user']['update'] += 1
                    elif "Deleted user" in line:
                        operation_counts['user']['delete'] += 1
                    elif "Retrieved user" in line:
                        operation_counts['user']['get'] += 1
                    elif "Created new order" in line:
                        operation_counts['order']['create'] += 1
                    elif "Updated order" in line:
                        operation_counts['order']['update'] += 1
                    elif "Deleted order" in line:
                        operation_counts['order']['delete'] += 1
                    elif "Retrieved order" in line:
                        operation_counts['order']['get'] += 1
        
            # Print summary report
            logger.info("\n" + "="*50)
            logger.info("SIMULATION SUMMARY REPORT")
            logger.info("="*50)
            logger.info(f"Total Errors: {error_count}")
            
            logger.info("\nOperation Counts:")
            for entity, ops in operation_counts.items():
                logger.info(f"\n{entity.upper()} Operations:")
                for op, count in ops.items():
                    logger.info(f"  {op.capitalize()}: {count}")
            
            logger.info("\nFinal State:")
            logger.info(f"  Pets: {len(self.pet_ids)}")
            logger.info(f"  Users: {len(self.usernames)}")
            logger.info(f"  Orders: {len(self.order_ids)}")
            logger.info("="*50)
        
        except FileNotFoundError:
            logger.error("Log file not found - cannot generate summary report")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Petstore API Traffic Simulator")
    parser.add_argument("--url", required=True, help="Base URL of the Petstore API")
    parser.add_argument("--api-key", required=True, help="API key for authentication")
    parser.add_argument("--duration", type=int, default=10, help="Duration in minutes (default: 10)")
    parser.add_argument("--rate", type=int, default=30, help="Operations per minute (default: 30)")
    parser.add_argument("--min-pets", type=int, default=10, help="Minimum number of pets (default: 10)")
    parser.add_argument("--min-users", type=int, default=5, help="Minimum number of users (default: 5)")
    parser.add_argument("--min-orders", type=int, default=3, help="Minimum number of orders (default: 3)")
    parser.add_argument("--parallel", type=int, default=0, help="Number of parallel threads (default: 0 - sequential)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Add after parsing args
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run simulator
    simulator = PetstoreTrafficSimulator(
        base_url=args.url,
        api_key=args.api_key,
        min_pets=args.min_pets,
        min_users=args.min_users,
        min_orders=args.min_orders
    )
    
    # Set the timeout
    simulator.timeout = args.timeout
    
    if args.parallel > 0:
        simulator.run_parallel_simulation(
            duration_minutes=args.duration,
            operations_per_minute=args.rate,
            concurrency=args.parallel
        )
    else:
        simulator.run_simulation(
            duration_minutes=args.duration,
            operations_per_minute=args.rate
        )
    # Generate and print summary report
    # simulator.generate_summary_report()
