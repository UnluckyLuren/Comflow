<?php
require_once __DIR__ . '/Database.php';

/**
 * ClawFlow - Authentication Service
 * Handles login, session management, brute-force protection
 */
class AuthService {
    private Database $db;
    private const SESSION_DURATION = 3600 * 8; // 8 hours
    private const MAX_ATTEMPTS     = 3;
    private const LOCKOUT_MINUTES  = 3;

    public function __construct() {
        $this->db = Database::getInstance();
        if (session_status() === PHP_SESSION_NONE) {
            session_start([
                'cookie_httponly' => true,
                'cookie_samesite' => 'Lax',
            ]);
        }
    }

    /**
     * Attempt to authenticate a user.
     * Returns ['success'=>true, 'user'=>[...]] or ['success'=>false, 'message'=>'...']
     */
    public function login(string $correo, string $password): array {
        $correo = strtolower(trim($correo));

        // 1. Fetch user
        $stmt = $this->db->query(
            "SELECT * FROM usuarios WHERE correo = ? AND activo = 1 LIMIT 1",
            [$correo]
        );
        $user = $stmt->fetch();

        if (!$user) {
            return ['success' => false, 'message' => 'Credenciales incorrectas.'];
        }

        // 2. Check lockout
        if ($user['bloqueado_hasta'] && strtotime($user['bloqueado_hasta']) > time()) {
            $remaining = ceil((strtotime($user['bloqueado_hasta']) - time()) / 60);
            return ['success' => false, 'message' => "Cuenta bloqueada. Intenta en {$remaining} min."];
        }

        // 3. Verify password
        if (!password_verify($password, $user['hash_contrasena'])) {
            $this->incrementFailedAttempts($user);
            $newAttempts = $user['intentos_fallidos'] + 1;
            $remaining   = self::MAX_ATTEMPTS - $newAttempts;

            if ($newAttempts >= self::MAX_ATTEMPTS) {
                return ['success' => false, 'message' => 'Cuenta bloqueada por ' . self::LOCKOUT_MINUTES . ' minutos.'];
            }
            return ['success' => false, 'message' => "Credenciales incorrectas. Intentos restantes: {$remaining}"];
        }

        // 4. Reset failed attempts and update last access
        $this->db->query(
            "UPDATE usuarios SET intentos_fallidos=0, bloqueado_hasta=NULL, ultimo_acceso=NOW() WHERE id_usuario=?",
            [$user['id_usuario']]
        );

        // 5. Store session
        $_SESSION['user_id']    = $user['id_usuario'];
        $_SESSION['user_email'] = $user['correo'];
        $_SESSION['user_name']  = $user['nombre'];
        $_SESSION['is_admin']   = (bool)$user['acceso_admin'];
        $_SESSION['expires']    = time() + self::SESSION_DURATION;

        $this->setFastApiToken($user['correo']);
        $this->logEvent($user['id_usuario'], 'info', 'auth', 'Login exitoso');

        return ['success' => true, 'user' => $user];
    }

    /**
     * Register a new administrator
     */
    public function register(string $correo, string $nombre, string $password, string $serverKey): array {
        // Validate server key
        $stmt = $this->db->query("SELECT valor FROM configuracion WHERE clave='server_registration_key'");
        $row  = $stmt->fetch();
        if (!$row || $row['valor'] !== $serverKey) {
            return ['success' => false, 'message' => 'Clave de servidor inválida.'];
        }

        $correo = strtolower(trim($correo));

        // Check duplicate
        $stmt = $this->db->query("SELECT id_usuario FROM usuarios WHERE correo=?", [$correo]);
        if ($stmt->fetch()) {
            return ['success' => false, 'message' => 'El correo ya está registrado.'];
        }

        // Validate password strength
        if (strlen($password) < 8) {
            return ['success' => false, 'message' => 'La contraseña debe tener al menos 8 caracteres.'];
        }

        $hash = password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);
        $this->db->query(
            "INSERT INTO usuarios (correo, nombre, hash_contrasena, acceso_admin) VALUES (?,?,?,1)",
            [$correo, $nombre, $hash]
        );

        return ['success' => true, 'message' => 'Administrador registrado correctamente.'];
    }

    public function logout(): void {
        $_SESSION = [];
        if (ini_get('session.use_cookies')) {
            $p = session_get_cookie_params();
            setcookie(session_name(), '', time() - 42000, $p['path'], $p['domain'], $p['secure'], $p['httponly']);
        }
        session_destroy();
    }

    public function isAuthenticated(): bool {
        return isset($_SESSION['user_id']) && $_SESSION['expires'] > time();
    }

    public function requireAuth(): void {
        if (!$this->isAuthenticated()) {
            header('Location: /index.php?expired=1');
            exit;
        }
    }

    public function getCurrentUser(): ?array {
        if (!$this->isAuthenticated()) return null;
        return [
            'id'       => $_SESSION['user_id'],
            'email'    => $_SESSION['user_email'],
            'name'     => $_SESSION['user_name'],
            'is_admin' => $_SESSION['is_admin'],
        ];
    }

    private function incrementFailedAttempts(array $user): void {
        $newAttempts = $user['intentos_fallidos'] + 1;
        $lockout     = null;

        if ($newAttempts >= self::MAX_ATTEMPTS) {
            $lockout = date('Y-m-d H:i:s', time() + self::LOCKOUT_MINUTES * 60);
            $this->logEvent($user['id_usuario'], 'warning', 'auth', 'Cuenta bloqueada por intentos fallidos');
        }

        $this->db->query(
            "UPDATE usuarios SET intentos_fallidos=?, bloqueado_hasta=? WHERE id_usuario=?",
            [$newAttempts, $lockout, $user['id_usuario']]
        );
    }

    private function logEvent(?int $userId, string $nivel, string $modulo, string $mensaje): void {
        try {
            $this->db->query(
                "INSERT INTO logs_sistema (id_usuario, nivel, modulo, mensaje, ip_origen) VALUES (?,?,?,?,?)",
                [$userId, $nivel, $modulo, $mensaje, $_SERVER['REMOTE_ADDR'] ?? null]
            );
        } catch (Exception $e) { /* fail silently */ }
    }

    // Genera un token JWT compatible con FastAPI sin usar librerías externas
    private function setFastApiToken(string $correo): void {
        // ESTA CLAVE DEBE SER EXACTAMENTE LA MISMA QUE PUSISTE EN EL .env DE FASTAPI
        $secret = "comflow_secret"; 
        
        $header = json_encode(['alg' => 'HS256', 'typ' => 'JWT']);
        // FastAPI usa comúnmente 'sub' (subject) para identificar al usuario
        $payload = json_encode(['sub' => $correo, 'exp' => time() + self::SESSION_DURATION]);

        $base64UrlHeader = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($header));
        $base64UrlPayload = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($payload));
        
        $signature = hash_hmac('sha256', $base64UrlHeader . "." . $base64UrlPayload, $secret, true);
        $base64UrlSignature = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($signature));
        
        $jwt = $base64UrlHeader . "." . $base64UrlPayload . "." . $base64UrlSignature;

        // Guardamos la cookie 'access_token' permitiendo que JS la lea
        setcookie("access_token", $jwt, [
            'expires' => time() + self::SESSION_DURATION,
            'path' => '/',
            'domain' => '', 
            'secure' => true,     
            'httponly' => false,  
            'samesite' => 'Lax'    
        ]);
    }
}
