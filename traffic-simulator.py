import requests
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
    """Simulates real-life traffic to the Petstore API"""
    
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
        self.headers = {"api_key": api_key, "Content-Type": "application/json"}
        
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
        
        # Initialize the system state
        self.initialize()
    
    def initialize(self):
        """Initialize system state by ensuring minimum data is present"""
        logger.info("Initializing system state...")
        
        # Get current entity counts
        self.refresh_state()
        
        # Create minimum entities if needed
        self.ensure_minimum_entities()
        logger.info("Initialization complete")
    
    def refresh_state(self):
        """Refresh our understanding of what's in the database"""
        try:
            # Get all available pets
            pets_resp = requests.get(f"{self.base_url}/pet/findByStatus?status=available", 
                                    headers=self.headers, timeout=10)
            pets_resp.raise_for_status()
            available_pets = pets_resp.json()
            
            # Get pending and sold pets 
            pending_resp = requests.get(f"{self.base_url}/pet/findByStatus?status=pending", 
                                       headers=self.headers, timeout=10)
            pending_resp.raise_for_status()
            pending_pets = pending_resp.json()
            
            sold_resp = requests.get(f"{self.base_url}/pet/findByStatus?status=sold", 
                                    headers=self.headers, timeout=10)
            sold_resp.raise_for_status()
            sold_pets = sold_resp.json()
            
            # Combine all pet lists and extract IDs
            all_pets = available_pets + pending_pets + sold_pets
            self.pet_ids = [pet["id"] for pet in all_pets if "id" in pet]
            
            # For users, we'll use a different approach since there's no endpoint to list all users
            # We'll maintain our list of created usernames
            
            # Get inventory to check order counts (approximation)
            inventory_resp = requests.get(f"{self.base_url}/store/inventory", 
                                         headers=self.headers, timeout=10)
            inventory_resp.raise_for_status()
            
            logger.info(f"Current state - Pets: {len(self.pet_ids)}, Users: {len(self.usernames)}, " +
                       f"Orders: {len(self.order_ids)}")
            
        except requests.RequestException as e:
            logger.error(f"Error refreshing state: {e}")
    
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
        try:
            # Generate a random pet
            pet_data = {
                "name": random.choice(self.pet_names),
                "photoUrls": [f"https://example.com/pets/{self.generate_random_string()}.jpg"],
                "status": random.choice(self.pet_statuses),
                "category": random.choice(self.pet_categories),
                "tags": random.sample(self.pet_tags, k=random.randint(1, 3))
            }
            
            # Send POST request
            response = requests.post(
                f"{self.base_url}/pet",
                headers=self.headers,
                json=pet_data,
                timeout=10
            )
            response.raise_for_status()
            
            # Extract pet ID from response
            new_pet = response.json()
            if "id" in new_pet:
                pet_id = new_pet["id"]
                self.pet_ids.append(pet_id)
                logger.info(f"Created new pet with ID: {pet_id}, name: {pet_data['name']}")
                return pet_id
            
            logger.warning(f"Created pet but couldn't find ID in response: {new_pet}")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error creating pet: {e}")
            return None
    
    def update_pet(self, pet_id: int) -> bool:
        """Update an existing pet"""
        try:
            # First get the current pet data
            response = requests.get(
                f"{self.base_url}/pet/{pet_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            pet_data = response.json()
            
            # Update some fields
            pet_data["status"] = random.choice(self.pet_statuses)
            pet_data["name"] = random.choice(self.pet_names)
            if random.random() < 0.3:  # 30% chance to change category
                pet_data["category"] = random.choice(self.pet_categories)
            
            # Send the update
            response = requests.put(
                f"{self.base_url}/pet",
                headers=self.headers,
                json=pet_data,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Updated pet with ID: {pet_id}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error updating pet {pet_id}: {e}")
            if "404" in str(e):
                # Pet no longer exists, remove from our list
                if pet_id in self.pet_ids:
                    self.pet_ids.remove(pet_id)
            return False
    
    def delete_pet(self, pet_id: int) -> bool:
        """Delete a pet by ID"""
        try:
            response = requests.delete(
                f"{self.base_url}/pet/{pet_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            # Remove from our list if successful
            if pet_id in self.pet_ids:
                self.pet_ids.remove(pet_id)
                
            logger.info(f"Deleted pet with ID: {pet_id}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error deleting pet {pet_id}: {e}")
            if "404" in str(e):
                # Pet is already gone, remove from our list
                if pet_id in self.pet_ids:
                    self.pet_ids.remove(pet_id)
            return False
    
    def get_pet_by_id(self, pet_id: int) -> Optional[Dict]:
        """Get a pet by ID"""
        try:
            response = requests.get(
                f"{self.base_url}/pet/{pet_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            pet_data = response.json()
            logger.info(f"Retrieved pet with ID: {pet_id}")
            return pet_data
            
        except requests.RequestException as e:
            logger.error(f"Error getting pet {pet_id}: {e}")
            if "404" in str(e):
                # Pet no longer exists, remove from our list
                if pet_id in self.pet_ids:
                    self.pet_ids.remove(pet_id)
            return None
    
    def find_pets_by_status(self, status: str) -> List[Dict]:
        """Find pets by status"""
        try:
            response = requests.get(
                f"{self.base_url}/pet/findByStatus?status={status}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            pets = response.json()
            logger.info(f"Found {len(pets)} pets with status: {status}")
            return pets
            
        except requests.RequestException as e:
            logger.error(f"Error finding pets by status {status}: {e}")
            return []
    
    def find_pets_by_tags(self, tags: List[str]) -> List[Dict]:
        """Find pets by tags"""
        try:
            # Build URL with multiple tags
            url = f"{self.base_url}/pet/findByTags"
            params = []
            for tag in tags:
                params.append(f"tags={tag}")
            if params:
                url += "?" + "&".join(params)
                
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            pets = response.json()
            logger.info(f"Found {len(pets)} pets with tags: {', '.join(tags)}")
            return pets
            
        except requests.RequestException as e:
            logger.error(f"Error finding pets by tags {tags}: {e}")
            return []
    
    def create_random_user(self) -> Optional[str]:
        """Create a random user and return username if successful"""
        try:
            # Generate random username
            username = f"user_{self.generate_random_string()}"
            
            # Generate user data
            user_data = {
                "username": username,
                "firstName": f"First_{self.generate_random_string(4)}",
                "lastName": f"Last_{self.generate_random_string(4)}",
                "email": f"{username}@example.com",
                # "password": f"pass_{self.generate_random_string(8)}",
                "password": f"password",
                "phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                "userStatus": random.randint(0, 2)
            }
            
            # Send POST request
            response = requests.post(
                f"{self.base_url}/user",
                headers=self.headers,
                json=user_data,
                timeout=10
            )
            response.raise_for_status()
            
            # Track username
            self.usernames.append(username)
            logger.info(f"Created new user with username: {username}")
            return username
            
        except requests.RequestException as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def update_user(self, username: str) -> bool:
        """Update an existing user"""
        try:
            # Generate update data (partial)
            user_data = {
                "firstName": f"Updated_{self.generate_random_string(4)}",
                "lastName": f"Updated_{self.generate_random_string(4)}",
                "email": f"updated_{username}@example.com",
                "phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            }
            
            # Send PUT request
            response = requests.put(
                f"{self.base_url}/user/{username}",
                headers=self.headers,
                json=user_data,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Updated user: {username}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error updating user {username}: {e}")
            if "404" in str(e):
                # User no longer exists
                if username in self.usernames:
                    self.usernames.remove(username)
            return False
    
    def delete_user(self, username: str) -> bool:
        """Delete a user by username"""
        try:
            response = requests.delete(
                f"{self.base_url}/user/{username}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            # Remove from our list if successful
            if username in self.usernames:
                self.usernames.remove(username)
                
            logger.info(f"Deleted user: {username}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error deleting user {username}: {e}")
            if "404" in str(e):
                # User is already gone
                if username in self.usernames:
                    self.usernames.remove(username)
            return False
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get a user by username"""
        try:
            response = requests.get(
                f"{self.base_url}/user/{username}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            user_data = response.json()
            logger.info(f"Retrieved user: {username}")
            return user_data
            
        except requests.RequestException as e:
            logger.error(f"Error getting user {username}: {e}")
            if "404" in str(e) and username in self.usernames:
                self.usernames.remove(username)
            return None
    
    def login_user(self, username: str, password: str = "password") -> bool:
        """Login as a user"""
        try:
            response = requests.get(
                f"{self.base_url}/user/login?username={username}&password={password}",
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Logged in as user: {username}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error logging in as user {username}: {e}")
            return False
    
    def logout_user(self) -> bool:
        """Logout current user"""
        try:
            response = requests.get(
                f"{self.base_url}/user/logout",
                timeout=10
            )
            response.raise_for_status()
            logger.info("Logged out user")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error logging out: {e}")
            return False
    
    def create_random_order(self) -> Optional[int]:
        """Create a random order and return order ID if successful"""
        # Need at least one pet to create an order
        if not self.pet_ids:
            logger.warning("Can't create order: no pets available")
            return None
            
        try:
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
            response = requests.post(
                f"{self.base_url}/store/order",
                headers=self.headers,
                json=order_data,
                timeout=10
            )
            response.raise_for_status()
            
            # Extract order ID from response
            new_order = response.json()
            if "id" in new_order:
                order_id = new_order["id"]
                self.order_ids.append(order_id)
                logger.info(f"Created new order with ID: {order_id} for pet ID: {pet_id}")
                return order_id
            
            logger.warning(f"Created order but couldn't find ID in response: {new_order}")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error creating order: {e}")
            return None
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Get an order by ID"""
        try:
            response = requests.get(
                f"{self.base_url}/store/order/{order_id}",
                timeout=10
            )
            response.raise_for_status()
            order_data = response.json()
            logger.info(f"Retrieved order with ID: {order_id}")
            return order_data
            
        except requests.RequestException as e:
            logger.error(f"Error getting order {order_id}: {e}")
            if "404" in str(e) and order_id in self.order_ids:
                self.order_ids.remove(order_id)
            return None
    
    def delete_order(self, order_id: int) -> bool:
        """Delete an order by ID"""
        try:
            response = requests.delete(
                f"{self.base_url}/store/order/{order_id}",
                timeout=10
            )
            response.raise_for_status()
            
            # Remove from our list if successful
            if order_id in self.order_ids:
                self.order_ids.remove(order_id)
                
            logger.info(f"Deleted order with ID: {order_id}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error deleting order {order_id}: {e}")
            if "404" in str(e) and order_id in self.order_ids:
                self.order_ids.remove(order_id)
            return False
    
    def get_inventory(self) -> Optional[Dict]:
        """Get store inventory"""
        try:
            response = requests.get(
                f"{self.base_url}/store/inventory",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            inventory = response.json()
            logger.info(f"Retrieved inventory: {inventory}")
            return inventory
            
        except requests.RequestException as e:
            logger.error(f"Error getting inventory: {e}")
            return None
    
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
        if len(self.pet_ids) > self.min_pets:
            # Only delete if we have more than the minimum
            pet_id = random.choice(self.pet_ids)
            self.delete_pet(pet_id)
        else:
            # Otherwise create one
            self.create_random_pet()
    
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
        if len(self.usernames) > self.min_users:
            # Only delete if we have more than the minimum
            username = random.choice(self.usernames)
            self.delete_user(username)
        else:
            # Otherwise create one
            self.create_random_user()
    
    def op_get_user(self):
        if self.usernames:
            self.get_user_by_username(random.choice(self.usernames))
        else:
            self.create_random_user()
    
    def op_login_user(self):
        if self.usernames:
            # We don't know the passwords for existing users, so we'll try with a default
            # This will likely fail in a real system, but demonstrates the API call
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
        if len(self.order_ids) > self.min_orders:
            # Only delete if we have more than the minimum
            order_id = random.choice(self.order_ids)
            self.delete_order(order_id)
        else:
            # Otherwise create one
            self.create_random_order()
    
    def op_get_inventory(self):
        self.get_inventory()
    
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
    
    args = parser.parse_args()
    
    # Create and run simulator
    simulator = PetstoreTrafficSimulator(
        base_url=args.url,
        api_key=args.api_key,
        min_pets=args.min_pets,
        min_users=args.min_users,
        min_orders=args.min_orders
    )
    
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