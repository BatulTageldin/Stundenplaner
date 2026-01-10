-- Tabelle für Schüler
CREATE TABLE schueler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    klasse VARCHAR(50)
);

-- Tabelle für Lehrer
CREATE TABLE lehrer (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    user_id INT UNIQUE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabelle für Räume
CREATE TABLE raum (
    id INT AUTO_INCREMENT PRIMARY KEY,
    raumnummer VARCHAR(50) NOT NULL,
    kapazitaet INT
);

-- Tabelle für Fächer
CREATE TABLE faecher (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fachname VARCHAR(100) NOT NULL,
    lehrer_id INT,
    raum_id INT,
    tag VARCHAR(20),
    startzeit TIME,
    endzeit TIME,
    FOREIGN KEY (lehrer_id) REFERENCES lehrer(id),
    FOREIGN KEY (raum_id) REFERENCES raum(id)
);

-- Tabelle für Stundenplan
CREATE TABLE stundenplan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    fach_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (fach_id) REFERENCES faecher(id)
);


CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(250) NOT NULL UNIQUE,
    password VARCHAR(250) NOT NULL,
    role VARCHAR(20) NOT NULL
);
