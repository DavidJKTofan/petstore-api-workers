// petstore-worker-d1.js - Swagger Petstore implementation using Cloudflare D1
// Using ES Modules syntax

// Helper for response formatting
function jsonResponse(data, status = 200) {
	return new Response(JSON.stringify(data, null, 2), {
		status,
		headers: {
			'Content-Type': 'application/json',
			'Access-Control-Allow-Origin': '*',
			'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
			'Access-Control-Allow-Headers': 'Content-Type, Authorization, api-key-petstore',
		},
	});
}

// Error response helper
function errorResponse(message, status = 400) {
	return jsonResponse({ code: status.toString(), message }, status);
}

// Middleware for authentication (simple implementation)
async function authenticate(request) {
	const apiKey = request.headers.get('api-key-petstore');
	if (request.url.includes('/pet/') || request.url.includes('/store/inventory')) {
		if (!apiKey || apiKey.trim() === '') {
			return new Response('API key is required', {
				status: 401,
				headers: {
					'Content-Type': 'application/json',
					'Access-Control-Allow-Origin': '*'
				}
			});
		}
		// You might want to add additional validation here
		// For example, checking against a list of valid API keys
		const validApiKeys = ['your_api_key', 'special-key', 'test-key']; // Add your valid keys here
		if (!validApiKeys.includes(apiKey)) {
			return new Response('Invalid API key', {
				status: 403,
				headers: {
					'Content-Type': 'application/json',
					'Access-Control-Allow-Origin': '*'
				}
			});
		}
	}
	return null; // Authentication passed
}

// Route handlers for Pet endpoints
const petHandlers = {
	async createPet(request, db) {
		try {
			const pet = await request.json();

			// Validation
			if (!pet.name || !pet.photoUrls) {
				return errorResponse('Pet requires name and photoUrls', 422);
			}

			// Generate ID if not provided
			if (!pet.id) {
				// Get the next ID from the database or generate one
				const lastPet = await db.prepare('SELECT MAX(id) as maxId FROM pets').first();
				pet.id = (lastPet?.maxId || 0) + 1;
			}

			// Set default status if not provided
			if (!pet.status) {
				pet.status = 'available';
			}

			// Insert pet into database
			// Store pet tags and photos in separate tables for proper normalization
			await db
				.prepare('INSERT INTO pets (id, name, status, category_id) VALUES (?, ?, ?, ?)')
				.bind(pet.id, pet.name, pet.status, pet.category?.id || null)
				.run();

			// Insert photo URLs
			if (Array.isArray(pet.photoUrls)) {
				for (const url of pet.photoUrls) {
					await db.prepare('INSERT INTO pet_photos (pet_id, url) VALUES (?, ?)').bind(pet.id, url).run();
				}
			}

			// Insert tags
			if (Array.isArray(pet.tags)) {
				for (const tag of pet.tags) {
					await db
						.prepare('INSERT INTO pet_tags (pet_id, tag_id, tag_name) VALUES (?, ?, ?)')
						.bind(pet.id, tag.id || null, tag.name)
						.run();
				}
			}

			// Update inventory count in the inventory table
			await db
				.prepare('INSERT INTO inventory (status, count) VALUES (?, 1) ' + 'ON CONFLICT(status) DO UPDATE SET count = count + 1')
				.bind(pet.status)
				.run();

			return jsonResponse(pet);
		} catch (err) {
			return errorResponse('Invalid input: ' + err.message, 400);
		}
	},

	async updatePet(request, db) {
		try {
			const pet = await request.json();

			if (!pet.id) {
				return errorResponse('Pet ID is required', 400);
			}

			// Check if pet exists
			const existingPet = await db.prepare('SELECT id, status FROM pets WHERE id = ?').bind(pet.id).first();
			if (!existingPet) {
				return errorResponse('Pet not found', 404);
			}

			// Update inventory if status changed
			if (existingPet.status !== pet.status && pet.status) {
				// Decrease count for old status
				await db.prepare('UPDATE inventory SET count = count - 1 WHERE status = ?').bind(existingPet.status).run();

				// Increase count for new status
				await db
					.prepare('INSERT INTO inventory (status, count) VALUES (?, 1) ' + 'ON CONFLICT(status) DO UPDATE SET count = count + 1')
					.bind(pet.status)
					.run();
			}

			// Update pet in database
			await db
				.prepare('UPDATE pets SET name = ?, status = ?, category_id = ? WHERE id = ?')
				.bind(pet.name, pet.status, pet.category?.id || null, pet.id)
				.run();

			// Delete existing photos and tags to replace them
			await db.prepare('DELETE FROM pet_photos WHERE pet_id = ?').bind(pet.id).run();
			await db.prepare('DELETE FROM pet_tags WHERE pet_id = ?').bind(pet.id).run();

			// Insert new photo URLs
			if (Array.isArray(pet.photoUrls)) {
				for (const url of pet.photoUrls) {
					await db.prepare('INSERT INTO pet_photos (pet_id, url) VALUES (?, ?)').bind(pet.id, url).run();
				}
			}

			// Insert new tags
			if (Array.isArray(pet.tags)) {
				for (const tag of pet.tags) {
					await db
						.prepare('INSERT INTO pet_tags (pet_id, tag_id, tag_name) VALUES (?, ?, ?)')
						.bind(pet.id, tag.id || null, tag.name)
						.run();
				}
			}

			return jsonResponse(pet);
		} catch (err) {
			return errorResponse('Invalid input: ' + err.message, 400);
		}
	},

	async findByStatus(url, db) {
		const params = new URL(url).searchParams;
		const status = params.get('status') || 'available';

		// Query pets by status with their associated data
		const stmt = await db
			.prepare(
				`
		SELECT 
		  p.id, p.name, p.status, p.category_id,
		  c.name as category_name,
		  GROUP_CONCAT(DISTINCT pp.url) as photo_urls,
		  GROUP_CONCAT(DISTINCT pt.tag_id || ':' || pt.tag_name) as tags
		FROM pets p
		LEFT JOIN categories c ON p.category_id = c.id
		LEFT JOIN pet_photos pp ON p.id = pp.pet_id
		LEFT JOIN pet_tags pt ON p.id = pt.pet_id
		WHERE p.status = ?
		GROUP BY p.id
	  `
			)
			.bind(status);

		const results = await stmt.all();

		// Format results to match the expected response structure
		const pets = results.results.map((row) => {
			const pet = {
				id: row.id,
				name: row.name,
				status: row.status,
				photoUrls: row.photo_urls ? row.photo_urls.split(',') : [],
			};

			if (row.category_id) {
				pet.category = {
					id: row.category_id,
					name: row.category_name,
				};
			}

			if (row.tags) {
				pet.tags = row.tags.split(',').map((tag) => {
					const [id, name] = tag.split(':');
					return { id: Number(id) || null, name };
				});
			} else {
				pet.tags = [];
			}

			return pet;
		});

		return jsonResponse(pets);
	},

	async findByTags(url, db) {
		const params = new URL(url).searchParams;
		const tags = params.getAll('tags');

		if (!tags || tags.length === 0) {
			return jsonResponse([]);
		}

		// Query pets by tags with their associated data
		const placeholders = tags.map(() => '?').join(',');
		const stmt = await db
			.prepare(
				`
		SELECT 
		  p.id, p.name, p.status, p.category_id,
		  c.name as category_name,
		  GROUP_CONCAT(DISTINCT pp.url) as photo_urls,
		  GROUP_CONCAT(DISTINCT pt.tag_id || ':' || pt.tag_name) as tags
		FROM pets p
		JOIN pet_tags pt ON p.id = pt.pet_id
		LEFT JOIN categories c ON p.category_id = c.id
		LEFT JOIN pet_photos pp ON p.id = pp.pet_id
		WHERE pt.tag_name IN (${placeholders})
		GROUP BY p.id
	  `
			)
			.bind(...tags);

		const results = await stmt.all();

		// Format results similarly to findByStatus
		const pets = results.results.map((row) => {
			const pet = {
				id: row.id,
				name: row.name,
				status: row.status,
				photoUrls: row.photo_urls ? row.photo_urls.split(',') : [],
			};

			if (row.category_id) {
				pet.category = {
					id: row.category_id,
					name: row.category_name,
				};
			}

			if (row.tags) {
				pet.tags = row.tags.split(',').map((tag) => {
					const [id, name] = tag.split(':');
					return { id: Number(id) || null, name };
				});
			} else {
				pet.tags = [];
			}

			return pet;
		});

		return jsonResponse(pets);
	},

	async getPetById(petId, db) {
		// Query a single pet with its associated data
		const stmt = await db
			.prepare(
				`
		SELECT 
		  p.id, p.name, p.status, p.category_id,
		  c.name as category_name,
		  GROUP_CONCAT(DISTINCT pp.url) as photo_urls,
		  GROUP_CONCAT(DISTINCT pt.tag_id || ':' || pt.tag_name) as tags
		FROM pets p
		LEFT JOIN categories c ON p.category_id = c.id
		LEFT JOIN pet_photos pp ON p.id = pp.pet_id
		LEFT JOIN pet_tags pt ON p.id = pt.pet_id
		WHERE p.id = ?
		GROUP BY p.id
	  `
			)
			.bind(petId);

		const row = await stmt.first();
		if (!row) {
			return errorResponse('Pet not found', 404);
		}

		// Format the pet object
		const pet = {
			id: row.id,
			name: row.name,
			status: row.status,
			photoUrls: row.photo_urls ? row.photo_urls.split(',') : [],
		};

		if (row.category_id) {
			pet.category = {
				id: row.category_id,
				name: row.category_name,
			};
		}

		if (row.tags) {
			pet.tags = row.tags.split(',').map((tag) => {
				const [id, name] = tag.split(':');
				return { id: Number(id) || null, name };
			});
		} else {
			pet.tags = [];
		}

		return jsonResponse(pet);
	},

	async updatePetWithForm(petId, url, request, db) {
		// Check if pet exists
		const pet = await db.prepare('SELECT id, status FROM pets WHERE id = ?').bind(petId).first();
		if (!pet) {
			return errorResponse('Pet not found', 404);
		}

		const formData = await request.formData();
		const name = formData.get('name');
		const status = formData.get('status');

		if (name || status) {
			const updates = [];
			const values = [];

			if (name) {
				updates.push('name = ?');
				values.push(name);
			}

			if (status) {
				updates.push('status = ?');
				values.push(status);

				// Update inventory counts if status changed
				if (pet.status !== status) {
					// Decrease count for old status
					await db.prepare('UPDATE inventory SET count = count - 1 WHERE status = ?').bind(pet.status).run();

					// Increase count for new status
					await db
						.prepare('INSERT INTO inventory (status, count) VALUES (?, 1) ' + 'ON CONFLICT(status) DO UPDATE SET count = count + 1')
						.bind(status)
						.run();
				}
			}

			// Update the pet
			if (updates.length > 0) {
				await db
					.prepare(`UPDATE pets SET ${updates.join(', ')} WHERE id = ?`)
					.bind(...values, petId)
					.run();
			}
		}

		// Return the updated pet
		return await petHandlers.getPetById(petId, db);
	},

	async deletePet(petId, db) {
		// Check if pet exists
		const pet = await db.prepare('SELECT id, status FROM pets WHERE id = ?').bind(petId).first();
		if (!pet) {
			return errorResponse('Pet not found', 404);
		}

		// Update inventory
		await db.prepare('UPDATE inventory SET count = count - 1 WHERE status = ?').bind(pet.status).run();

		// Delete pet and related records
		await db.prepare('DELETE FROM pet_photos WHERE pet_id = ?').bind(petId).run();
		await db.prepare('DELETE FROM pet_tags WHERE pet_id = ?').bind(petId).run();
		await db.prepare('DELETE FROM pets WHERE id = ?').bind(petId).run();

		return new Response(null, { status: 200 });
	},

	async uploadImage(petId, request, db) {
		// Check if pet exists
		const pet = await db.prepare('SELECT id FROM pets WHERE id = ?').bind(petId).first();
		if (!pet) {
			return errorResponse('Pet not found', 404);
		}

		const formData = await request.formData();
		const file = formData.get('file');
		const additionalMetadata = formData.get('additionalMetadata');

		// In a real implementation, you would store the file and its URL
		// This is a simplified version
		const imageUrl = `https://example.com/petimages/${petId}-${Date.now()}.jpg`;

		// Store the new image URL
		await db.prepare('INSERT INTO pet_photos (pet_id, url) VALUES (?, ?)').bind(petId, imageUrl).run();

		return jsonResponse({
			code: 200,
			type: 'success',
			message: `Image uploaded for pet ${petId}${additionalMetadata ? ` with metadata: ${additionalMetadata}` : ''}`,
		});
	},
};

// Route handlers for Store endpoints
const storeHandlers = {
	async getInventory(db) {
		const results = await db.prepare('SELECT status, count FROM inventory').all();

		// Convert array to object
		const inventory = {};
		for (const row of results.results) {
			inventory[row.status] = row.count;
		}

		return jsonResponse(inventory);
	},

	async placeOrder(request, db) {
		try {
			const order = await request.json();

			if (!order.petId) {
				return errorResponse('PetId is required', 400);
			}

			// Check if pet exists
			const pet = await db.prepare('SELECT id FROM pets WHERE id = ?').bind(order.petId).first();
			if (!pet) {
				return errorResponse('Pet not found', 404);
			}

			// Generate ID if not provided
			if (!order.id) {
				const lastOrder = await db.prepare('SELECT MAX(id) as maxId FROM orders').first();
				order.id = (lastOrder?.maxId || 0) + 1;
			}

			// Set defaults
			if (!order.quantity) order.quantity = 1;
			if (!order.status) order.status = 'placed';
			if (!order.shipDate) order.shipDate = new Date().toISOString();

			// Insert order
			await db
				.prepare('INSERT INTO orders (id, pet_id, quantity, ship_date, status, complete) VALUES (?, ?, ?, ?, ?, ?)')
				.bind(order.id, order.petId, order.quantity, order.shipDate, order.status, order.complete || false)
				.run();

			return jsonResponse(order);
		} catch (err) {
			return errorResponse('Invalid input: ' + err.message, 400);
		}
	},

	async getOrderById(orderId, db) {
		// Swagger spec notes: valid IDs are <= 5 or > 10
		const orderIdNum = parseInt(orderId);
		if (isNaN(orderIdNum) || (orderIdNum > 5 && orderIdNum <= 10)) {
			return errorResponse('Invalid ID supplied', 400);
		}

		const order = await db
			.prepare('SELECT id, pet_id, quantity, ship_date, status, complete FROM orders WHERE id = ?')
			.bind(orderId)
			.first();

		if (!order) {
			return errorResponse('Order not found', 404);
		}

		// Format the response to match the expected structure
		return jsonResponse({
			id: order.id,
			petId: order.pet_id,
			quantity: order.quantity,
			shipDate: order.ship_date,
			status: order.status,
			complete: Boolean(order.complete),
		});
	},

	async deleteOrder(orderId, db) {
		// Swagger spec: valid IDs < 1000
		const orderIdNum = parseInt(orderId);
		if (isNaN(orderIdNum) || orderIdNum >= 1000) {
			return errorResponse('Invalid ID supplied', 400);
		}

		const order = await db.prepare('SELECT id FROM orders WHERE id = ?').bind(orderId).first();
		if (!order) {
			return errorResponse('Order not found', 404);
		}

		await db.prepare('DELETE FROM orders WHERE id = ?').bind(orderId).run();
		return new Response(null, { status: 200 });
	},
};

// Route handlers for User endpoints
const userHandlers = {
	async createUser(request, db) {
		try {
			const user = await request.json();

			if (!user.username) {
				return errorResponse('Username is required', 400);
			}

			// Generate ID if not provided
			if (!user.id) {
				const lastUser = await db.prepare('SELECT MAX(id) as maxId FROM users').first();
				user.id = (lastUser?.maxId || 0) + 1;
			}

			// Insert user
			await db
				.prepare(
					'INSERT INTO users (id, username, first_name, last_name, email, password, phone, user_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
				)
				.bind(
					user.id,
					user.username,
					user.firstName || null,
					user.lastName || null,
					user.email || null,
					user.password || null,
					user.phone || null,
					user.userStatus || 0
				)
				.run();

			return jsonResponse(user);
		} catch (err) {
			return errorResponse('Invalid input: ' + err.message, 400);
		}
	},

	async createUsersWithList(request, db) {
		try {
			const usersList = await request.json();

			if (!Array.isArray(usersList)) {
				return errorResponse('Input must be an array', 400);
			}

			// Start a transaction for better performance and atomicity
			await db.exec('BEGIN TRANSACTION');

			try {
				for (const user of usersList) {
					if (!user.username) continue;

					// Generate ID if not provided
					if (!user.id) {
						const lastUser = await db.prepare('SELECT MAX(id) as maxId FROM users').first();
						user.id = (lastUser?.maxId || 0) + 1;
					}

					// Insert user
					await db
						.prepare(
							'INSERT INTO users (id, username, first_name, last_name, email, password, phone, user_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
						)
						.bind(
							user.id,
							user.username,
							user.firstName || null,
							user.lastName || null,
							user.email || null,
							user.password || null,
							user.phone || null,
							user.userStatus || 0
						)
						.run();
				}

				await db.exec('COMMIT');
				return jsonResponse(usersList[0] || {});
			} catch (err) {
				await db.exec('ROLLBACK');
				throw err;
			}
		} catch (err) {
			return errorResponse('Invalid input: ' + err.message, 400);
		}
	},

	async loginUser(url, db) {
		const params = new URL(url).searchParams;
		const username = params.get('username');
		const password = params.get('password');

		if (!username || !password) {
			return errorResponse('Invalid username/password supplied', 400);
		}

		const user = await db.prepare('SELECT username, password FROM users WHERE username = ?').bind(username).first();

		if (!user || user.password !== password) {
			return errorResponse('Invalid username/password supplied', 400);
		}

		// Set headers as specified in the OpenAPI doc
		const response = new Response(JSON.stringify('Logged in successfully'), {
			status: 200,
			headers: {
				'Content-Type': 'application/json',
				'X-Rate-Limit': '5000',
				'X-Expires-After': new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
			},
		});

		return response;
	},

	async logoutUser() {
		return new Response(null, { status: 200 });
	},

	async getUserByName(username, db) {
		const user = await db
			.prepare('SELECT id, username, first_name, last_name, email, password, phone, user_status FROM users WHERE username = ?')
			.bind(username)
			.first();

		if (!user) {
			return errorResponse('User not found', 404);
		}

		// Format the response to match the expected structure
		return jsonResponse({
			id: user.id,
			username: user.username,
			firstName: user.first_name,
			lastName: user.last_name,
			email: user.email,
			password: user.password,
			phone: user.phone,
			userStatus: user.user_status,
		});
	},

	async updateUser(username, request, db) {
		const user = await db.prepare('SELECT id FROM users WHERE username = ?').bind(username).first();
		if (!user) {
			return errorResponse('User not found', 404);
		}

		try {
			const userData = await request.json();

			// Build update query dynamically based on provided fields
			const updates = [];
			const values = [];

			if (userData.firstName !== undefined) {
				updates.push('first_name = ?');
				values.push(userData.firstName);
			}

			if (userData.lastName !== undefined) {
				updates.push('last_name = ?');
				values.push(userData.lastName);
			}

			if (userData.email !== undefined) {
				updates.push('email = ?');
				values.push(userData.email);
			}

			if (userData.password !== undefined) {
				updates.push('password = ?');
				values.push(userData.password);
			}

			if (userData.phone !== undefined) {
				updates.push('phone = ?');
				values.push(userData.phone);
			}

			if (userData.userStatus !== undefined) {
				updates.push('user_status = ?');
				values.push(userData.userStatus);
			}

			// Only update if there are fields to update
			if (updates.length > 0) {
				await db
					.prepare(`UPDATE users SET ${updates.join(', ')} WHERE username = ?`)
					.bind(...values, username)
					.run();
			}

			return new Response(null, { status: 200 });
		} catch (err) {
			return errorResponse('Invalid input: ' + err.message, 400);
		}
	},

	async deleteUser(username, db) {
		const user = await db.prepare('SELECT id FROM users WHERE username = ?').bind(username).first();
		if (!user) {
			return errorResponse('User not found', 404);
		}

		await db.prepare('DELETE FROM users WHERE username = ?').bind(username).run();
		return new Response(null, { status: 200 });
	},
};

// Main request handler
export default {
	async fetch(request, env, ctx) {
		const url = new URL(request.url);
		
		// Add CORS headers helper
		const corsHeaders = {
			'Access-Control-Allow-Origin': '*',
			'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
			'Access-Control-Allow-Headers': 'Content-Type, Authorization, api-key-petstore',
		};

		// Handle CORS preflight for all requests
		if (request.method === 'OPTIONS') {
			return new Response(null, {
				headers: corsHeaders,
			});
		}

		// Serve OpenAPI specification file
		if (url.pathname === '/api-docs/openapi.yaml' || url.pathname === '/openapi.yaml') {
			const response = await env.ASSETS.fetch(request);
			// Add CORS headers to the response
			const newResponse = new Response(response.body, response);
			Object.entries(corsHeaders).forEach(([key, value]) => {
				newResponse.headers.set(key, value);
			});
			return newResponse;
		}
		
		// If the path starts with /api/v3, handle API requests
		if (url.pathname.startsWith('/api/v3')) {
			// Access the D1 database
			const db = env.PETSTORE_DB;

			// Check authentication for protected routes
			const authError = await authenticate(request);
			if (authError) return authError;

			const parsedUrl = new URL(url);
			const path = parsedUrl.pathname;
			const apiPath = path.replace(/^\/api\/v3/, '');

			try {
				// Pet Routes
				if (apiPath === '/pet' && request.method === 'POST') {
					return await petHandlers.createPet(request, db);
				}

				if (apiPath === '/pet' && request.method === 'PUT') {
					return await petHandlers.updatePet(request, db);
				}

				if (apiPath === '/pet/findByStatus' && request.method === 'GET') {
					return await petHandlers.findByStatus(url, db);
				}

				if (apiPath === '/pet/findByTags' && request.method === 'GET') {
					return await petHandlers.findByTags(url, db);
				}

				if (apiPath.match(/^\/pet\/\d+$/) && request.method === 'GET') {
					const petId = apiPath.split('/')[2];
					return await petHandlers.getPetById(petId, db);
				}

				if (apiPath.match(/^\/pet\/\d+$/) && request.method === 'POST') {
					const petId = apiPath.split('/')[2];
					return await petHandlers.updatePetWithForm(petId, url, request, db);
				}

				if (apiPath.match(/^\/pet\/\d+$/) && request.method === 'DELETE') {
					const petId = apiPath.split('/')[2];
					return await petHandlers.deletePet(petId, db);
				}

				if (apiPath.match(/^\/pet\/\d+\/uploadImage$/) && request.method === 'POST') {
					const petId = apiPath.split('/')[2];
					return await petHandlers.uploadImage(petId, request, db);
				}

				// Store Routes
				if (apiPath === '/store/inventory' && request.method === 'GET') {
					return await storeHandlers.getInventory(db);
				}

				if (apiPath === '/store/order' && request.method === 'POST') {
					return await storeHandlers.placeOrder(request, db);
				}

				if (apiPath.match(/^\/store\/order\/\d+$/) && request.method === 'GET') {
					const orderId = apiPath.split('/')[3];
					return await storeHandlers.getOrderById(orderId, db);
				}

				if (apiPath.match(/^\/store\/order\/\d+$/) && request.method === 'DELETE') {
					const orderId = apiPath.split('/')[3];
					return await storeHandlers.deleteOrder(orderId, db);
				}

				// User Routes
				if (apiPath === '/user' && request.method === 'POST') {
					return await userHandlers.createUser(request, db);
				}

				if (apiPath === '/user/createWithList' && request.method === 'POST') {
					return await userHandlers.createUsersWithList(request, db);
				}

				if (apiPath === '/user/login' && request.method === 'GET') {
					return await userHandlers.loginUser(url, db);
				}

				if (apiPath === '/user/logout' && request.method === 'GET') {
					return await userHandlers.logoutUser();
				}

				if (apiPath.match(/^\/user\/[^\/]+$/) && request.method === 'GET') {
					const username = apiPath.split('/')[2];
					return await userHandlers.getUserByName(username, db);
				}

				if (apiPath.match(/^\/user\/[^\/]+$/) && request.method === 'PUT') {
					const username = apiPath.split('/')[2];
					return await userHandlers.updateUser(username, request, db);
				}

				if (apiPath.match(/^\/user\/[^\/]+$/) && request.method === 'DELETE') {
					const username = apiPath.split('/')[2];
					return await userHandlers.deleteUser(username, db);
				}

				// If we get here, the route wasn't found
				return errorResponse('Not Found', 404);
			} catch (error) {
				return errorResponse('Internal Server Error: ' + error.message, 500);
			}
		}
		
		// For all other requests, serve static assets with CORS headers
		const response = await env.ASSETS.fetch(request);
		const newResponse = new Response(response.body, response);
		Object.entries(corsHeaders).forEach(([key, value]) => {
			newResponse.headers.set(key, value);
		});
		return newResponse;
	}
};
