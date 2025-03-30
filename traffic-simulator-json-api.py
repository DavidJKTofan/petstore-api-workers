import asyncio
import httpx
import random
import logging
import time
from typing import List, Dict, Any, Optional
from collections import defaultdict
from fake_useragent import UserAgent

class APITrafficSimulator:
    def __init__(self, 
                 base_url: str, 
                 max_concurrent_requests: int = 10,
                 timeout: float = 10.0):
        """
        Initialize the API Traffic Simulator with HTTP/2 support
        
        :param base_url: Base URL of the API
        :param max_concurrent_requests: Maximum number of concurrent requests
        :param timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.max_concurrent_requests = max_concurrent_requests
        self.ua = UserAgent()
        
        # Tracking metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'endpoint_requests': defaultdict(int),
            'endpoint_errors': defaultdict(int),
            'status_code_counts': defaultdict(int),
            'request_times': []
        }
        
        # Define endpoints with metadata
        self.endpoints = {
            '/albums': {
                'max_items': 100,
                'query_strategy': self._generate_list_strategy('/albums'),
                'item_strategy': self._generate_item_strategy('/albums')
            },
            '/users': {
                'max_items': 10,
                'query_strategy': self._generate_list_strategy('/users'),
                'item_strategy': self._generate_item_strategy('/users')
            },
            '/photos': {
                'max_items': 5000,
                'query_strategy': self._generate_list_strategy('/photos', additional_params={
                    'albumId': random.randint(1, 10)
                }),
                'item_strategy': self._generate_item_strategy('/photos')
            },
            '/posts': {
                'max_items': 100,
                'query_strategy': self._generate_list_strategy('/posts'),
                'item_strategy': self._generate_item_strategy('/posts')
            },
            '/todos': {
                'max_items': 200,
                'query_strategy': self._generate_list_strategy('/todos'),
                'item_strategy': self._generate_item_strategy('/todos')
            }
        }
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s: %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('api_traffic_simulation.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # HTTP/2 client configuration
        self.http2_client_limits = httpx.Limits(
            max_connections=max_concurrent_requests,
            max_keepalive_connections=max_concurrent_requests
        )
        self.timeout = httpx.Timeout(timeout)

    def _generate_list_strategy(self, endpoint: str, additional_params: Optional[Dict[str, Any]] = None) -> callable:
        """
        Generate a strategy for list endpoint queries
        
        :param endpoint: Base endpoint
        :param additional_params: Optional additional query parameters
        :return: Query parameter generation function
        """
        def generate_params():
            params = {
                '_page': random.randint(1, 10),
                '_limit': random.randint(10, 50)
            }
            if additional_params:
                params.update(additional_params)
            return params
        return generate_params

    def _generate_item_strategy(self, endpoint: str) -> callable:
        """
        Generate a strategy for individual item retrieval
        
        :param endpoint: Base endpoint
        :return: Item ID generation function
        """
        def generate_item_id():
            max_items = self.endpoints[endpoint]['max_items']
            return random.randint(1, max_items)
        return generate_item_id

    def generate_summary_report(self) -> str:
            """
            Generate a comprehensive summary report of the traffic simulation
            
            :return: Formatted summary report
            """
            # Calculate summary statistics
            total_requests = self.metrics['total_requests']
            successful_requests = self.metrics['successful_requests']
            failed_requests = self.metrics['failed_requests']
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Calculate request time statistics
            request_times = self.metrics['request_times']
            avg_request_time = sum(request_times) / len(request_times) if request_times else 0
            
            # Construct report
            report = [
                "=" * 50,
                "API TRAFFIC SIMULATION - SUMMARY REPORT",
                "=" * 50,
                f"Total Requests: {total_requests}",
                f"Successful Requests: {successful_requests}",
                f"Failed Requests: {failed_requests}",
                f"Success Rate: {success_rate:.2f}%",
                f"Average Request Duration: {avg_request_time:.4f}s",
                "\nRequest Distribution by Endpoint:",
                *[f"  {endpoint}: {count} requests" for endpoint, count in self.metrics['endpoint_requests'].items()],
                "\nError Distribution by Endpoint:",
                *[f"  {endpoint}: {count} errors" for endpoint, count in self.metrics['endpoint_errors'].items()],
                "\nStatus Code Breakdown:",
                *[f"  {code}: {count} requests" for code, count in self.metrics['status_code_counts'].items()],
                "=" * 50
            ]  
            return "\n".join(report)

    async def fetch_endpoint(self, session: httpx.AsyncClient, endpoint: str, item_mode: bool = False) -> None:
        """
        Fetch a specific endpoint with intelligent parameter generation
        
        :param session: Async HTTP client session
        :param endpoint: API endpoint to fetch
        :param item_mode: Whether to fetch a specific item
        """
        try:
            # Increment total and endpoint-specific request count
            self.metrics['total_requests'] += 1
            self.metrics['endpoint_requests'][endpoint] += 1
            
            # Determine query strategy
            if item_mode:
                # Individual item retrieval
                item_id = self.endpoints[endpoint]['item_strategy']()
                url = f"{self.base_url}{endpoint}/{item_id}"
                params = {}
            else:
                # List endpoint
                query_strategy = self.endpoints[endpoint]['query_strategy']
                params = query_strategy()
                url = f"{self.base_url}{endpoint}"
            
            # Randomize user agent
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'application/json'
            }
            
            # Simulate variable request timing
            await asyncio.sleep(random.uniform(0.1, 1.5))
            
            # Perform request
            start_time = time.time()
            response = await session.get(
                url, 
                params=params, 
                headers=headers
            )
            
            # Calculate request duration
            request_duration = time.time() - start_time
            self.metrics['request_times'].append(request_duration)
            
            # Track status code
            self.metrics['status_code_counts'][response.status_code] += 1
            
            # Log request details
            request_type = "Item" if item_mode else "List"
            if response.status_code == 200:
                self.metrics['successful_requests'] += 1
                self.logger.info(
                    f"Successful {request_type} request: {endpoint} "
                    f"(Status: {response.status_code}, "
                    f"Duration: {request_duration:.2f}s, "
                    f"UA: {headers['User-Agent']})"
                )
                
                # Optional: Parse and validate response
                try:
                    data = response.json()
                    
                    # Different validation for list vs item endpoints
                    if not item_mode:
                        item_count = len(data)
                        max_expected = self.endpoints[endpoint]['max_items']
                        
                        if item_count > max_expected:
                            self.logger.warning(
                                f"Unexpected item count for {endpoint}: "
                                f"Expected ≤{max_expected}, Got {item_count}"
                            )
                except ValueError:
                    self.logger.error(f"Invalid JSON response for {endpoint}")
            else:
                # Track failed requests
                self.metrics['failed_requests'] += 1
                self.metrics['endpoint_errors'][endpoint] += 1
                self.logger.warning(
                    f"Failed {request_type} request: {endpoint} "
                    f"(Status: {response.status_code})"
                )
        
        except Exception as e:
            # Track exceptions
            self.metrics['failed_requests'] += 1
            self.metrics['endpoint_errors'][endpoint] += 1
            self.logger.error(f"Error fetching {endpoint}: {e}")

    # ... [rest of the previous implementation remains the same, including generate_summary_report() and simulate_traffic()]

    async def simulate_traffic(
        self, 
        duration: int = 300, 
        request_frequency: float = 2.0
    ) -> None:
        """
        Simulate traffic to API endpoints with HTTP/2
        
        :param duration: Total simulation duration in seconds
        :param request_frequency: Average time between requests per endpoint
        """
        # Create HTTP/2 compatible client
        async with httpx.AsyncClient(
            http2=True,  # Enable HTTP/2
            limits=self.http2_client_limits,
            timeout=self.timeout
        ) as session:
            start_time = time.time()
            
            while time.time() - start_time < duration:
                # Randomly select endpoints with weighted probability
                selected_endpoints = random.choices(
                    list(self.endpoints.keys()), 
                    k=random.randint(1, 3)
                )
                
                # Create tasks for selected endpoints
                tasks = []
                for endpoint in selected_endpoints:
                    # Randomly choose between list and item retrieval
                    modes = [False, True] if random.random() > 0.5 else [False]
                    tasks.extend([
                        self.fetch_endpoint(session, endpoint, item_mode) 
                        for item_mode in modes
                    ])
                
                # Run tasks concurrently
                await asyncio.gather(*tasks)
                
                # Wait before next batch of requests
                await asyncio.sleep(random.uniform(0.5, request_frequency))
            
            self.logger.info("Traffic simulation completed")

async def main():
    base_url = 'https://json.dlsdemo.com'
    simulator = APITrafficSimulator(base_url)
    
    try:
        await simulator.simulate_traffic(
            duration=300,  # 5 minutes of simulation
            request_frequency=2.0  # Average 2 seconds between request batches
        )
        
        # Print summary report
        print(simulator.generate_summary_report())
        
        # Optional: Write report to file
        with open('traffic_simulation_report.txt', 'w') as f:
            f.write(simulator.generate_summary_report())
    
    except Exception as e:
        print(f"Simulation error: {e}")

if __name__ == "__main__":
    asyncio.run(main())