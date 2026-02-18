-- Datos iniciales para la aplicación

-- Géneros musicales
INSERT INTO genres (name, description) VALUES
('Pop', 'Música popular contemporánea'),
('Rock', 'Rock y sus variantes'),
('Reggaeton', 'Música urbana latina'),
('Trap', 'Trap y hip hop moderno'),
('Electronic', 'Música electrónica y EDM'),
('Jazz', 'Jazz clásico y moderno'),
('Latino', 'Música latina variada'),
('Hip Hop', 'Hip hop clásico'),
('Urbano', 'Música urbana'),
('R&B', 'Rhythm and Blues');

-- Usuario admin inicial
INSERT INTO users (email, username, role, created_at) VALUES
('admin@discoteca.com', 'admin', 'admin', NOW());
