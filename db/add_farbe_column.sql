-- Migration: Add farbe column to faecher table
-- Run this if you already have an existing database

ALTER TABLE faecher ADD COLUMN farbe VARCHAR(7) DEFAULT '#3498db';

-- Optional: Set some default colors for existing subjects
UPDATE faecher SET farbe = '#e74c3c' WHERE fachname = 'Mathematik';
UPDATE faecher SET farbe = '#3498db' WHERE fachname = 'Deutsch';
UPDATE faecher SET farbe = '#9b59b6' WHERE fachname = 'Englisch';
UPDATE faecher SET farbe = '#f39c12' WHERE fachname = 'Französisch';
UPDATE faecher SET farbe = '#1abc9c' WHERE fachname = 'Geschichte';
UPDATE faecher SET farbe = '#2ecc71' WHERE fachname = 'Geografie';
UPDATE faecher SET farbe = '#27ae60' WHERE fachname = 'Biologie';
UPDATE faecher SET farbe = '#16a085' WHERE fachname = 'Chemie';
UPDATE faecher SET farbe = '#34495e' WHERE fachname = 'Physik';
UPDATE faecher SET farbe = '#95a5a6' WHERE fachname = 'Informatik';
UPDATE faecher SET farbe = '#d35400' WHERE fachname = 'Wirtschaft & Recht';
UPDATE faecher SET farbe = '#c0392b' WHERE fachname = 'Musik';
UPDATE faecher SET farbe = '#8e44ad' WHERE fachname = 'Bildnerisches Gestalten';
UPDATE faecher SET farbe = '#e67e22' WHERE fachname = 'Sport';
