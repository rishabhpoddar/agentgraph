import Database from 'better-sqlite3';
import path from 'path';

const dbPath = path.join(__dirname, 'database.sqlite');
const db = new Database(dbPath);

export function initializeDatabase() {
    // Create users table
    db.exec(`
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    `);

    // Check if we need to seed the database
    const count = db.prepare('SELECT COUNT(*) as count FROM users').get() as { count: number };

    if (count.count === 0) {
        // Seed the database with sample users
        const insert = db.prepare('INSERT INTO users (name, email) VALUES (?, ?)');

        const sampleUsers: [string, string][] = [
            ['John Doe', 'john.doe@example.com'],
            ['Jane Smith', 'jane.smith@example.com'],
            ['Bob Johnson', 'bob.johnson@example.com'],
            ['Alice Brown', 'alice.brown@example.com']
        ];

        const insertMany = db.transaction((users: [string, string][]) => {
            for (const user of users) {
                insert.run(user);
            }
        });

        insertMany(sampleUsers);
        console.log('Database seeded with sample users');
    }
}

export function queryDatabase(sql: string) {
    try {
        const result = db.prepare(sql).all();
        return JSON.stringify(result, null, 2);
    } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        return `Error executing query: ${errorMessage}`;
    }
}

// Initialize the database when this module is imported
initializeDatabase(); 