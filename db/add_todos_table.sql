-- Migration: Add todos table
-- Run this if you already have an existing database

CREATE TABLE todos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    titel VARCHAR(250) NOT NULL,
    erledigt BOOLEAN DEFAULT FALSE,
    faelligkeitsdatum DATE,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
