-- ═══════════════════════════════════════════════════════
-- ClawFlow Database Schema v1.0
-- ═══════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS clawflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE clawflow;

-- ── Usuarios ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario    INT AUTO_INCREMENT PRIMARY KEY,
    correo        VARCHAR(255) NOT NULL UNIQUE,
    nombre        VARCHAR(100) NOT NULL,
    hash_contrasena VARCHAR(255) NOT NULL,
    acceso_admin  BOOLEAN DEFAULT FALSE,
    activo        BOOLEAN DEFAULT TRUE,
    intentos_fallidos TINYINT DEFAULT 0,
    bloqueado_hasta DATETIME NULL,
    ultimo_acceso DATETIME NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_correo (correo)
) ENGINE=InnoDB;

-- ── Instancias n8n ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS instancias_n8n (
    id_instancia      INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario        INT NOT NULL,
    nombre            VARCHAR(100) NOT NULL DEFAULT 'Local n8n',
    host_url          VARCHAR(500) NOT NULL,
    api_key_cifrada   TEXT NOT NULL,
    activa            BOOLEAN DEFAULT TRUE,
    ultima_sync       DATETIME NULL,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── Flujos de Trabajo ────────────────────────────────────
CREATE TABLE IF NOT EXISTS flujos_trabajo (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    id_flujo_n8n   VARCHAR(100) NOT NULL,
    id_instancia   INT NOT NULL,
    id_usuario     INT NOT NULL,
    nombre         VARCHAR(255) NOT NULL,
    activo         BOOLEAN DEFAULT FALSE,
    estructura_json LONGTEXT,
    nodos_resumen  JSON,
    origen_comando TEXT,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_instancia) REFERENCES instancias_n8n(id_instancia),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
    INDEX idx_id_flujo_n8n (id_flujo_n8n),
    INDEX idx_usuario (id_usuario)
) ENGINE=InnoDB;

-- ── Comandos de Voz ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS comandos_voz (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT NOT NULL,
    url_audio       VARCHAR(500),
    texto_transcrito TEXT,
    json_generado   LONGTEXT,
    id_flujo_desplegado INT NULL,
    estado          ENUM('procesando','exito','error','cancelado') DEFAULT 'procesando',
    error_detalle   TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
    FOREIGN KEY (id_flujo_desplegado) REFERENCES flujos_trabajo(id) ON DELETE SET NULL,
    INDEX idx_usuario_fecha (id_usuario, created_at)
) ENGINE=InnoDB;

-- ── Credenciales API ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS credenciales_api (
    id_credencial   INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT NOT NULL,
    nombre_app      VARCHAR(100) NOT NULL,
    tipo            ENUM('oauth2','api_key','basic','token') DEFAULT 'api_key',
    token_cifrado   TEXT NOT NULL,
    metadata        JSON,
    activa          BOOLEAN DEFAULT TRUE,
    ultima_validacion DATETIME NULL,
    estado_conexion ENUM('valida','invalida','sin_probar') DEFAULT 'sin_probar',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    UNIQUE KEY unique_user_app (id_usuario, nombre_app)
) ENGINE=InnoDB;

-- ── Logs del Sistema ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS logs_sistema (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario  INT NULL,
    nivel       ENUM('info','warning','error','critical') DEFAULT 'info',
    modulo      VARCHAR(100),
    mensaje     TEXT NOT NULL,
    detalle     JSON,
    ip_origen   VARCHAR(45),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    INDEX idx_nivel_fecha (nivel, created_at),
    INDEX idx_usuario_fecha (id_usuario, created_at)
) ENGINE=InnoDB;

-- ── Sesiones ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sesiones (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario  INT NOT NULL,
    token_hash  VARCHAR(255) NOT NULL UNIQUE,
    ip_origen   VARCHAR(45),
    user_agent  TEXT,
    expira_en   DATETIME NOT NULL,
    activa      BOOLEAN DEFAULT TRUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    INDEX idx_token (token_hash)
) ENGINE=InnoDB;

-- ── Configuración del Sistema ────────────────────────────
CREATE TABLE IF NOT EXISTS configuracion (
    clave   VARCHAR(100) PRIMARY KEY,
    valor   TEXT NOT NULL,
    cifrado BOOLEAN DEFAULT FALSE,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Valores por defecto
INSERT IGNORE INTO configuracion (clave, valor) VALUES
  ('server_registration_key', 'CLAWFLOW2026'),
  ('max_failed_attempts', '3'),
  ('lockout_minutes', '3'),
  ('max_audio_duration_sec', '60'),
  ('llm_temperature', '0.1');

-- Usuario administrador por defecto (password: Admin@ClawFlow2026)
-- Hash generado con bcrypt rounds=12
INSERT IGNORE INTO usuarios (correo, nombre, hash_contrasena, acceso_admin) VALUES
  ('admin@clawflow.local', 'Administrador', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMlJBi.3d.GgYi1.C4XtJjYMwm', TRUE);
