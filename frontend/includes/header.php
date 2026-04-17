<?php
require_once __DIR__ . '/AuthService.php';
$auth = new AuthService();
$auth->requireAuth();
$user = $auth->getCurrentUser();

$currentPage = basename($_SERVER['PHP_SELF'], '.php');
$navItems = [
    'dashboard'      => ['label' => 'Dashboard',        'icon' => 'grid'],
    'workflows'      => ['label' => 'Flujos',            'icon' => 'git-merge'],
    'infrastructure' => ['label' => 'Infraestructura',   'icon' => 'server'],
    'credentials'    => ['label' => 'Credenciales',      'icon' => 'key'],
    'logs'           => ['label' => 'Logs',              'icon' => 'terminal'],
];
?>
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ClawFlow — <?= htmlspecialchars($pageTitle ?? 'Dashboard') ?></title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/style.css">
  <script src="https://unpkg.com/feather-icons@4.29.1/dist/feather.min.js" defer></script>
</head>
<body>

<!-- Animated grid background -->
<div class="grid-bg" aria-hidden="true"></div>

<!-- Sidebar Nav -->
<aside class="sidebar" id="sidebar">
  <div class="sidebar-logo">
    <span class="logo-claw">CLAW</span><span class="logo-flow">FLOW</span>
  </div>
  <div class="sidebar-subtitle">Automation OS</div>

  <nav class="sidebar-nav">
    <?php foreach ($navItems as $page => $item): ?>
    <a href="/<?= $page ?>.php"
       class="nav-item <?= $currentPage === $page ? 'active' : '' ?>">
      <i data-feather="<?= $item['icon'] ?>"></i>
      <span><?= $item['label'] ?></span>
    </a>
    <?php endforeach; ?>
  </nav>

  <div class="sidebar-footer">
    <div class="user-badge">
      <div class="user-avatar"><?= strtoupper(substr($user['name'], 0, 1)) ?></div>
      <div class="user-info">
        <span class="user-name"><?= htmlspecialchars($user['name']) ?></span>
        <?php if ($user['is_admin']): ?>
        <span class="user-role">Admin</span>
        <?php endif; ?>
      </div>
    </div>
    <a href="/api/auth/logout.php" class="nav-item logout-btn">
      <i data-feather="log-out"></i>
      <span>Salir</span>
    </a>
  </div>
</aside>

<!-- Main Content Wrapper -->
<main class="main-content" id="main-content">
  <div class="topbar">
    <button class="sidebar-toggle" id="sidebarToggle" aria-label="Toggle sidebar">
      <i data-feather="menu"></i>
    </button>
    <h1 class="page-title"><?= htmlspecialchars($pageTitle ?? 'Dashboard') ?></h1>
    <div class="topbar-right">
      <div class="status-indicator" id="statusIndicator">
        <span class="status-dot" id="n8nStatusDot"></span>
        <span id="n8nStatusLabel">Verificando n8n...</span>
      </div>
    </div>
  </div>

  <div class="page-body">
