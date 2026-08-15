-- PostgreSQL initialization script
-- This file is used to initialize the PostgreSQL database for RAGFlow

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Note: The main database 'rag_flow' is created automatically by Docker
-- using the POSTGRES_DB environment variable.
-- This script runs after the database is created.
