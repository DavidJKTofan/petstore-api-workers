-- Sample data for categories
INSERT INTO categories (id, name) VALUES 
(1, 'Dogs'),
(2, 'Cats'),
(3, 'Birds'),
(4, 'Fish'),
(5, 'Reptiles');

-- Sample data for pets
INSERT INTO pets (id, name, status, category_id) VALUES 
(1, 'Buddy', 'available', 1),
(2, 'Whiskers', 'available', 2),
(3, 'Tweety', 'pending', 3),
(4, 'Nemo', 'sold', 4),
(5, 'Rex', 'available', 5),
(6, 'Max', 'available', 1),
(7, 'Luna', 'pending', 2),
(8, 'Charlie', 'available', 1),
(9, 'Oscar', 'sold', 4),
(10, 'Leo', 'available', 2);

-- Sample data for pet photos
INSERT INTO pet_photos (pet_id, url) VALUES 
(1, 'https://example.com/pets/buddy1.jpg'),
(1, 'https://example.com/pets/buddy2.jpg'),
(2, 'https://example.com/pets/whiskers1.jpg'),
(3, 'https://example.com/pets/tweety1.jpg'),
(4, 'https://example.com/pets/nemo1.jpg'),
(5, 'https://example.com/pets/rex1.jpg'),
(6, 'https://example.com/pets/max1.jpg'),
(7, 'https://example.com/pets/luna1.jpg'),
(8, 'https://example.com/pets/charlie1.jpg'),
(9, 'https://example.com/pets/oscar1.jpg'),
(10, 'https://example.com/pets/leo1.jpg');

-- Sample data for pet tags
INSERT INTO pet_tags (pet_id, tag_id, tag_name) VALUES 
(1, 1, 'friendly'),
(1, 2, 'trained'),
(2, 3, 'playful'),
(3, 4, 'colorful'),
(4, 5, 'tropical'),
(5, 6, 'rare'),
(6, 7, 'puppy'),
(7, 8, 'kitten'),
(8, 9, 'senior'),
(9, 10, 'exotic'),
(10, 11, 'domestic');

-- Update inventory counts based on pet statuses
UPDATE inventory SET count = (SELECT COUNT(*) FROM pets WHERE status = 'available') WHERE status = 'available';
UPDATE inventory SET count = (SELECT COUNT(*) FROM pets WHERE status = 'pending') WHERE status = 'pending';
UPDATE inventory SET count = (SELECT COUNT(*) FROM pets WHERE status = 'sold') WHERE status = 'sold';

-- Sample data for orders
INSERT INTO orders (id, pet_id, quantity, ship_date, status, complete) VALUES 
(1, 4, 1, '2023-05-15T14:30:00Z', 'approved', true),
(2, 9, 1, '2023-06-20T10:15:00Z', 'delivered', true),
(3, 3, 1, '2023-07-05T09:45:00Z', 'placed', false),
(4, 7, 2, '2023-07-10T16:20:00Z', 'placed', false),
(5, 1, 1, '2023-07-15T11:30:00Z', 'approved', false);

-- Sample data for users
INSERT INTO users (id, username, first_name, last_name, email, password, phone, user_status) VALUES 
(1, 'user1', 'John', 'Doe', 'john.doe@example.com', 'password123', '555-123-4567', 1),
(2, 'user2', 'Jane', 'Doe', 'jane.doe@example.com', 'password123', '555-234-5678', 1),
(3, 'user3', 'Bob', 'Smith', 'bob.smith@example.com', 'password123', '555-345-6789', 1),
(4, 'user4', 'Alice', 'Jones', 'alice.jones@example.com', 'password123', '555-456-7890', 1),
(5, 'user5', 'Mike', 'Brown', 'mike.brown@example.com', 'password123', '555-567-8901', 1);