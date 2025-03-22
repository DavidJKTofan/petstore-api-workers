# Copy of Swagger Petstore API on Cloudflare Workers + D1

This project attempts to implement the [Swagger Petstore API](https://github.com/swagger-api/swagger-petstore) using [Cloudflare Workers](https://workers.cloudflare.com/) and [Cloudflare D1](https://developers.cloudflare.com/d1/) database. It provides a fully functioning REST API for a pet store, including endpoints for managing pets, orders, and users.

## Features

- RESTful API following OpenAPI/Swagger Petstore specification
- Persistent storage using Cloudflare D1 (SQLite-based serverless database)
- Serverless architecture with Cloudflare Workers
- Authentication implemented with Cloudflare API Shield [JWT Validation](https://developers.cloudflare.com/api-shield/security/jwt-validation/)
- Complete CRUD operations for pets, users, and orders

## Deployment

### Prerequisites

- [Cloudflare account](https://developers.cloudflare.com/fundamentals/setup/account/create-account/)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)

### Setup

1. Install Wrangler CLI:

```bash
npm install wrangler --save-dev
```

2. Authenticate with your Cloudflare account:

```bash
npx wrangler login
```

3. Clone this repository:

```bash
git clone https://github.com/DavidJKTofan/petstore-api-workers.git
cd petstore-api-workers
```

4. Create a D1 database:

```bash
npx wrangler d1 create petstore
```

5. Update your `wrangler.jsonc` [configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/) with the database ID from the previous step:

```json
{
	"$schema": "node_modules/wrangler/config-schema.json",
	"name": "petstore-api",
	"main": "src/index.js",
	"compatibility_date": "2025-03-20",
	"observability": {
		"enabled": true
	},
	"d1_databases": [
		{
			"binding": "PETSTORE_DB",
			"database_name": "petstore",
			"database_id": "6c662a4b-91d5-482e-8032-fd19c28cae9d"
		}
	]
}
```

6. Create the database schema:

```bash
npx wrangler d1 execute petstore --file=schema.sql --remote
```

7. Add sample data (optional):

```bash
npx wrangler d1 execute petstore --file=sample-data.sql --remote
```

8. Deploy your Worker:

```bash
npx wrangler deploy
```

## API Documentation

This API implements the [Swagger Petstore specification](https://petstore.swagger.io/). Below are examples of how to use the key endpoints.

### Base URL

```
https://petstore.automatic-demo.com/api/v3
```

### Authentication

Many endpoints require an API key for authentication:

```
api_key: your_api_key
```

Pass this key in the header of your requests.

### Pet Endpoints

#### Create a new pet

```bash
curl -X POST "https://petstore.automatic-demo.com/api/v3/pet" \
  -H "Content-Type: application/json" \
  -H "api_key: your_api_key" \
  -d '{
    "name": "Doggo",
    "photoUrls": ["https://example.com/doggo.jpg"],
    "status": "available",
    "category": {
      "id": 1,
      "name": "Dogs"
    },
    "tags": [
      {
        "id": 1,
        "name": "friendly"
      }
    ]
  }'
```

#### Get a pet by ID

```bash
curl -X GET "https://petstore.automatic-demo.com/api/v3/pet/1" \
  -H "api_key: your_api_key"
```

#### Update an existing pet

```bash
curl -X PUT "https://petstore.automatic-demo.com/api/v3/pet" \
  -H "Content-Type: application/json" \
  -H "api_key: your_api_key" \
  -d '{
    "id": 1,
    "name": "Doggo Updated",
    "photoUrls": ["https://example.com/doggo.jpg"],
    "status": "pending",
    "category": {
      "id": 1,
      "name": "Dogs"
    },
    "tags": [
      {
        "id": 1,
        "name": "friendly"
      }
    ]
  }'
```

#### Find pets by status

```bash
curl -X GET "https://petstore.automatic-demo.com/api/v3/pet/findByStatus?status=available" \
  -H "api_key: your_api_key"
```

#### Find pets by tags

```bash
curl -X GET "https://petstore.automatic-demo.com/api/v3/pet/findByTags?tags=friendly&tags=trained" \
  -H "api_key: your_api_key"
```

#### Delete a pet

```bash
curl -X DELETE "https://petstore.automatic-demo.com/api/v3/pet/1" \
  -H "api_key: your_api_key"
```

#### Upload an image for a pet

```bash
curl -X POST "https://petstore.automatic-demo.com/api/v3/pet/1/uploadImage" \
  -H "api_key: your_api_key" \
  -F "file=@pet-image.jpg" \
  -F "additionalMetadata=Profile photo for pet"
```

### Store Endpoints

#### Get inventory by status

```bash
curl -X GET "https://petstore.automatic-demo.com/api/v3/store/inventory" \
  -H "api_key: your_api_key"
```

#### Place an order

```bash
curl -X POST "https://petstore.automatic-demo.com/api/v3/store/order" \
  -H "Content-Type: application/json" \
  -d '{
    "petId": 2,
    "quantity": 1,
    "shipDate": "2023-08-01T10:00:00Z",
    "status": "placed",
    "complete": false
  }'
```

#### Get order by ID

```bash
curl -X GET "https://petstore.automatic-demo.com/api/v3/store/order/1"
```

#### Delete an order

```bash
curl -X DELETE "https://petstore.automatic-demo.com/api/v3/store/order/1"
```

### User Endpoints

#### Create a user

```bash
curl -X POST "https://petstore.automatic-demo.com/api/v3/user" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user1",
    "firstName": "Test",
    "lastName": "User",
    "email": "test.user@example.com",
    "password": "password123",
    "phone": "555-123-4567",
    "userStatus": 1
  }'
```

#### Create multiple users with list

```bash
curl -X POST "https://petstore.automatic-demo.com/api/v3/user/createWithList" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "username": "user2",
      "firstName": "Test",
      "lastName": "User2",
      "email": "test.user2@example.com",
      "password": "password456",
      "phone": "555-234-5678",
      "userStatus": 1
    },
    {
      "username": "user3",
      "firstName": "Test",
      "lastName": "User3",
      "email": "test.user3@example.com",
      "password": "password789",
      "phone": "555-345-6789",
      "userStatus": 1
    }
  ]'
```

#### User login

```bash
curl -X GET "https://petstore.automatic-demo.com/api/v3/user/login?username=user1&password=password123"
```

#### User logout

```bash
curl -X GET "https://petstore.automatic-demo.com/api/v3/user/logout"
```

#### Get user by username

```bash
curl -X GET "https://petstore.automatic-demo.com/api/v3/user/user1"
```

#### Update a user

```bash
curl -X PUT "https://petstore.automatic-demo.com/api/v3/user/user1" \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Updated",
    "lastName": "User",
    "email": "updated.user@example.com"
  }'
```

#### Delete a user

```bash
curl -X DELETE "https://petstore.automatic-demo.com/api/v3/user/user1"
```

## Database Schema

The API uses the following tables:

- `pets`: Stores basic pet information
- `categories`: Pet categories
- `pet_photos`: URLs of pet photos (many-to-one relationship with pets)
- `pet_tags`: Pet tags (many-to-many relationship)
- `inventory`: Counts of pets by status
- `orders`: Store orders
- `users`: User accounts

## Development

### Local Development

Start a local development server:

```bash
npx wrangler dev
```

### Simulating traffic

Simulate API traffic for testing purposes and to populate analytics.

Use a virtual environment:

```bash
python -m venv PETSTORE_API
source PETSTORE_API/bin/activate
```

#### Required Arguments

- `--url`: The base URL of the Petstore API you want to test
- `--api-key`: Your API key for authentication

#### Optional Arguments

- `--duration`: How long to run the simulation in minutes (default: 10)
- `--rate`: Operations per minute to perform (default: 30)
- `--min-pets`: Minimum number of pets to maintain (default: 10)
- `--min-users`: Minimum number of users to maintain (default: 5)
- `--min-orders`: Minimum number of orders to maintain (default: 3)
- `--parallel`: Number of parallel threads for concurrent operations (default: 0, which means sequential operation)

```bash
python traffic-simulator.py --url "https://petstore.automatic-demo.com/" --api-key "special-key" --duration 30 --rate 60 --min-pets 10 --min-users 10 --parallel 3
```

- Run the simulator for 30 minutes
- Generate about 60 operations per minute per thread
- Maintain at least 20 pets and 10 users in the system
- Run 3 concurrent threads (for a total of ~180 operations per minute)

### Modifying the Schema

If you need to modify the database schema:

1. Update the `schema.sql` file
2. Apply changes to your D1 database:

```bash
npx wrangler d1 execute petstore --file=schema.sql
```

Note: This will attempt to recreate tables that already exist, which is safe due to the `IF NOT EXISTS` clauses.

---

## Disclaimer

Educational purposes only.

All trademarks, logos and brand names are the property of their respective owners. All company, product and service names used in this website are for identification and/or educational purposes only. Use of these names, trademarks and brands does not imply endorsement.

This repo does not reflect the opinions of, and is not affiliated with any of the institutions mentioned here.
