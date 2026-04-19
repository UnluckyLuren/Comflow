<?php
require_once __DIR__ . '/includes/AuthService.php';

$auth = new AuthService();

// --- DESTRUIR SESIÓN SI EXPIRÓ ---
if (isset($_GET['expired']) && $_GET['expired'] == '1') {
    $auth->logout();
    setcookie("cf_uid", "", time() - 3600, "/"); // Borrar el puente
    header("Location: /index.php");
    exit;
}

// Redirect if already logged in
if ($auth->isAuthenticated()) {
    header('Location: /dashboard.php');
    exit;
}

$error   = '';
$success = '';
$tab     = 'login';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? 'login';

    if ($action === 'login') {
        $tab    = 'login';
        $result = $auth->login($_POST['correo'] ?? '', $_POST['password'] ?? '');
        if ($result['success']) {
            header('Location: /dashboard.php');
            exit;
        }
        $error = $result['message'];
    } elseif ($action === 'register') {
        $tab    = 'register';
        $result = $auth->register(
            $_POST['correo']     ?? '',
            $_POST['nombre']     ?? '',
            $_POST['password']   ?? '',
            $_POST['server_key'] ?? ''
        );
        if ($result['success']) {
            $success = $result['message'];
            $tab = 'login';
        } else {
            $error = $result['message'];
        }
    }
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ClawFlow — Iniciar Sesión</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
<div class="grid-bg" aria-hidden="true"></div>

<div class="auth-page">
  <div class="auth-card fade-in">
    <div class="auth-logo">
      <span style="color:var(--accent)">CLAW</span><span>FLOW</span>
    </div>
    <div class="auth-tagline">Automation OS · Voice-Driven</div>

    <!-- Tabs -->
    <div class="auth-tabs">
      <button class="auth-tab <?= $tab === 'login'    ? 'active' : '' ?>" data-tab="login">Iniciar Sesión</button>
      <button class="auth-tab <?= $tab === 'register' ? 'active' : '' ?>" data-tab="register">Registrar Admin</button>
    </div>

    <!-- Messages -->
    <?php if ($error): ?>
    <div class="auth-error visible"><?= htmlspecialchars($error) ?></div>
    <?php endif; ?>
    <?php if ($success): ?>
    <div class="auth-success visible"><?= htmlspecialchars($success) ?></div>
    <?php endif; ?>
    <?php if (isset($_GET['expired'])): ?>
    <div class="auth-error visible">Tu sesión expiró. Inicia sesión nuevamente.</div>
    <?php endif; ?>

    <!-- Login Form -->
    <form method="POST" class="auth-form <?= $tab === 'login' ? 'active' : '' ?>" id="loginForm">
      <input type="hidden" name="action" value="login">
      <div class="form-group">
        <label class="form-label">Correo electrónico</label>
        <input type="email" name="correo" class="form-control"
               placeholder="admin@clawflow.local" required
               value="<?= htmlspecialchars($_POST['correo'] ?? '') ?>">
      </div>
      <div class="form-group">
        <label class="form-label">Contraseña</label>
        <input type="password" name="password" class="form-control"
               placeholder="••••••••" required>
      </div>
      <button type="submit" class="btn btn-primary full-width" style="justify-content:center;margin-top:8px">
        Iniciar Sesión
      </button>
      <p style="text-align:center;margin-top:16px;font-size:12px;color:var(--text-muted)">
        Usuario demo: <span style="color:var(--accent)">admin@clawflow.local</span> / <span style="color:var(--accent)">Admin@ClawFlow2026</span>
      </p>
    </form>

    <!-- Register Form -->
    <form method="POST" class="auth-form <?= $tab === 'register' ? 'active' : '' ?>" id="registerForm">
      <input type="hidden" name="action" value="register">
      <div class="form-group">
        <label class="form-label">Nombre</label>
        <input type="text" name="nombre" class="form-control" placeholder="Tu nombre" required>
      </div>
      <div class="form-group">
        <label class="form-label">Correo electrónico</label>
        <input type="email" name="correo" class="form-control" placeholder="tu@dominio.com" required>
      </div>
      <div class="form-group">
        <label class="form-label">Contraseña</label>
        <input type="password" name="password" class="form-control" placeholder="Mínimo 8 caracteres" required minlength="8">
      </div>
      <div class="form-group">
        <label class="form-label">Clave de servidor</label>
        <input type="text" name="server_key" class="form-control" placeholder="CLAWFLOW2026" required>
      </div>
      <button type="submit" class="btn btn-primary full-width" style="justify-content:center;margin-top:8px">
        Registrar Administrador
      </button>
    </form>
  </div>
</div>

<script>
document.querySelectorAll('.auth-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.auth-tab, .auth-form').forEach(el => el.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab + 'Form').classList.add('active');
  });
});
</script>
</body>
</html>
