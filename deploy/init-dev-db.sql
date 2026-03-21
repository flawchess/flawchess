-- Creates the dev and test databases on first container init
CREATE DATABASE flawchess;
CREATE DATABASE flawchess_test;

-- Create app user matching .env defaults
CREATE USER flawchess WITH PASSWORD 'flawchess';
GRANT ALL PRIVILEGES ON DATABASE flawchess TO flawchess;
GRANT ALL PRIVILEGES ON DATABASE flawchess_test TO flawchess;

-- Allow flawchess user to create objects in public schema
\c flawchess
GRANT ALL ON SCHEMA public TO flawchess;

\c flawchess_test
GRANT ALL ON SCHEMA public TO flawchess;
