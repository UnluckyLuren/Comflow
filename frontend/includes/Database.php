<?php
/**
 * ClawFlow - Database Connection (Singleton Pattern)
 */
class Database {
    private static ?Database $instance = null;
    private PDO $connection;

    private string $host     = 'mysql';
    private string $dbname   = 'comflow_db';
    private string $username = 'comflow_user';
    private string $password = 'comflow_pass';
    private string $charset  = 'utf8mb4';

    private function __construct() {
        $dsn = "mysql:host={$this->host};dbname={$this->dbname};charset={$this->charset}";
        $options = [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ];
        try {
            $this->connection = new PDO($dsn, $this->username, $this->password, $options);
        } catch (PDOException $e) {
            error_log("DB Connection Error: " . $e->getMessage());
            throw new RuntimeException("Database connection failed.");
        }
    }

    public static function getInstance(): Database {
        if (self::$instance === null) {
            self::$instance = new Database();
        }
        return self::$instance;
    }

    public function getConnection(): PDO {
        return $this->connection;
    }

    /** Execute a prepared query and return the statement */
    public function query(string $sql, array $params = []): PDOStatement {
        $stmt = $this->connection->prepare($sql);
        $stmt->execute($params);
        return $stmt;
    }

    public function lastInsertId(): string {
        return $this->connection->lastInsertId();
    }
}
