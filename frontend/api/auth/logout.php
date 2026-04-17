<?php
require_once __DIR__ . '/../../includes/AuthService.php';
$auth = new AuthService();
$auth->logout();
header('Location: /index.php');
exit;
