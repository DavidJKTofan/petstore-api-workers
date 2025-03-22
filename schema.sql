-- Drop dependent tables first
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS pet_tags;
DROP TABLE IF EXISTS pet_photos;

-- Drop tables that don't have dependent constraints
DROP TABLE IF EXISTS pets;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS users;

-- Create the tables needed for the petstore

-- Create categories first (since pets reference categories in sample data)
CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

-- Create pets table next
CREATE TABLE IF NOT EXISTS pets (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'available',
  category_id INTEGER
);

-- Create pet_photos table
CREATE TABLE IF NOT EXISTS pet_photos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pet_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  FOREIGN KEY (pet_id) REFERENCES pets(id)
);

-- Create pet_tags table
CREATE TABLE IF NOT EXISTS pet_tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pet_id INTEGER NOT NULL,
  tag_id INTEGER,
  tag_name TEXT NOT NULL,
  FOREIGN KEY (pet_id) REFERENCES pets(id)
);

-- Create inventory table
CREATE TABLE IF NOT EXISTS inventory (
  status TEXT PRIMARY KEY,
  count INTEGER DEFAULT 0
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY,
  pet_id INTEGER NOT NULL,
  quantity INTEGER DEFAULT 1,
  ship_date TEXT,
  status TEXT DEFAULT 'placed',
  complete BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (pet_id) REFERENCES pets(id)
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  password TEXT,
  phone TEXT,
  user_status INTEGER DEFAULT 0
);

-- Initialize inventory counts
INSERT OR IGNORE INTO inventory (status, count) VALUES ('available', 0);
INSERT OR IGNORE INTO inventory (status, count) VALUES ('pending', 0);
INSERT OR IGNORE INTO inventory (status, count) VALUES ('sold', 0);
