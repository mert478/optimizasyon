import os
import sys
import psutil
import hashlib
import threading
import time
import webbrowser
import subprocess
import base64
import winreg
import shutil
import socket
import json
import csv
import platform
import urllib.request
import urllib.error
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_VERSION = "1.1.0"
GITHUB_REPO_OWNER = "mert478"      # <-- GitHub kullanıcı adınızla değiştirin
GITHUB_REPO_NAME = "optimizasyon"  # <-- Repo adınızla değiştirin
GITHUB_REPO_URL = f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"

class SentinelProGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ayyıldız Sentinel Pro - Siber Güvenlik & Optimizasyon Süiti")
        self.root.geometry("1200x880")
        self.root.minsize(980, 720)
        self.root.configure(bg="#121212")

        # Sıralama Durumları
        self.sort_state = {
            "procs": {"col": "ram", "reverse": True},
            "net": {"col": "status", "reverse": False}
        }

        self.suspicious_dirs = [
            os.path.expanduser("~\\AppData\\Local\\Temp").lower(),
            "c:\\windows\\temp",
            os.path.expanduser("~\\Downloads").lower()
        ]

        # Tanılama Modülü: iid -> sorun sözlüğü eşlemesi
        self.issues_map = {}

        # İşlem Günlüğü (Audit Log)
        log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SentinelPro")
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            log_dir = os.path.expanduser("~")
        self.log_file_path = os.path.join(log_dir, "sentinel_islem_gunlugu.txt")

        self.setup_styles()
        self.create_widgets()
        self.create_context_menu()

        # Canlı Güncelleme Döngüsü
        self.is_running = True
        self.refresh_thread = threading.Thread(target=self.live_update_loop, daemon=True)
        self.refresh_thread.start()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        BG_COLOR = "#1e1e1e"
        FG_COLOR = "#ffffff"

        self.style.configure(".", background=BG_COLOR, foreground=FG_COLOR, font=("Segoe UI", 9))
        
        # Notebook Stili
        self.style.configure("TNotebook", background="#121212", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#2b2b2b", foreground="#aaaaaa", padding=[12, 6], font=("Segoe UI", 9, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", "#005c99")], foreground=[("selected", "#ffffff")])

        # Treeview Stili
        self.style.configure("Treeview", 
                             background="#181818", 
                             fieldbackground="#181818", 
                             foreground="#ffffff", 
                             rowheight=26,
                             font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", 
                             background="#2b2b2b", 
                             foreground="#00e676", 
                             font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", "#005c99")])

    def create_widgets(self):
        # --- ÜST PANEL: Metrikler ---
        top_frame = tk.Frame(self.root, bg="#1a1a1a", pady=10, padx=15)
        top_frame.pack(fill="x", side="top")

        self.lbl_cpu = tk.Label(top_frame, text="CPU: %0.0", font=("Segoe UI", 11, "bold"), fg="#00e676", bg="#1a1a1a")
        self.lbl_cpu.pack(side="left", padx=10)

        self.lbl_ram = tk.Label(top_frame, text="RAM: %0.0", font=("Segoe UI", 11, "bold"), fg="#00b0ff", bg="#1a1a1a")
        self.lbl_ram.pack(side="left", padx=10)

        self.lbl_procs = tk.Label(top_frame, text="Aktif İşlem: 0", font=("Segoe UI", 10), fg="#e0e0e0", bg="#1a1a1a")
        self.lbl_procs.pack(side="left", padx=10)

        # Filtreleme Kutusu
        search_frame = tk.Frame(top_frame, bg="#1a1a1a")
        search_frame.pack(side="right", padx=10)

        tk.Label(search_frame, text="Filtrele:", fg="#aaaaaa", bg="#1a1a1a", font=("Segoe UI", 9)).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.apply_filter())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg="#2a2a2a", fg="#ffffff", insertbackground="white", bd=1, relief="flat", width=20)
        search_entry.pack(side="left", ipady=3)

        # --- ORTA PANEL: SEKMELER ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # TAB 1: Süreçler & Güvenlik
        self.tab_procs = tk.Frame(self.notebook, bg="#121212")
        self.notebook.add(self.tab_procs, text=" 🛡️ Süreçler & Güvenlik ")
        self.setup_process_tab()

        # TAB 2: Ağ & DNS Optimizer
        self.tab_network = tk.Frame(self.notebook, bg="#121212")
        self.notebook.add(self.tab_network, text=" 🌐 Ağ & DNS ")
        self.setup_network_tab()

        # TAB 3: Sistem Bakımı & Telemetry
        self.tab_opt = tk.Frame(self.notebook, bg="#121212")
        self.notebook.add(self.tab_opt, text=" ⚡ Bakım & Telemetry ")
        self.setup_optimization_tab()

        # TAB 4: Lisans & Başlangıç (Autorun)
        self.tab_autorun = tk.Frame(self.notebook, bg="#121212")
        self.notebook.add(self.tab_autorun, text=" 🔑 Lisans & Başlangıç ")
        self.setup_autorun_license_tab()

        # TAB 5: Disk & Raporlama
        self.tab_disk = tk.Frame(self.notebook, bg="#121212")
        self.notebook.add(self.tab_disk, text=" 📊 Disk & Rapor ")
        self.setup_disk_analyzer_tab()

        # TAB 6: Hakkında & Güncelleme
        self.tab_about = tk.Frame(self.notebook, bg="#121212")
        self.notebook.add(self.tab_about, text=" ℹ️ Hakkında & Güncelleme ")
        self.setup_about_tab()

        # --- ALT PANEL: Detay Çubuğu ---
        bottom_frame = tk.Frame(self.root, bg="#1a1a1a", pady=8, padx=15)
        bottom_frame.pack(fill="x", side="bottom")

        self.lbl_details = tk.Label(bottom_frame, text="Sistem aktif. İşlemleri incelemek için sağ tıklama menüsünü kullanabilirsiniz.", fg="#888888", bg="#1a1a1a", font=("Segoe UI", 9), anchor="w")
        self.lbl_details.pack(side="left", fill="x", expand=True)

    # --- TAB 1: SÜREÇLER ---
    def setup_process_tab(self):
        columns = ("pid", "name", "status", "cpu", "ram", "network", "path")
        self.tree_procs = ttk.Treeview(self.tab_procs, columns=columns, show="headings", selectmode="browse")

        headers = {
            "pid": "PID", "name": "İşlem Adı", "status": "Güvenlik Durumu",
            "cpu": "CPU (%)", "ram": "RAM (MB)", "network": "Ağ", "path": "Çalıştırma Yolu"
        }

        for col, text in headers.items():
            self.tree_procs.heading(col, text=text, command=lambda _col=col: self.on_header_click("procs", self.tree_procs, _col))

        self.tree_procs.column("pid", width=65, stretch=False)
        self.tree_procs.column("name", width=160, stretch=False)
        self.tree_procs.column("status", width=170, stretch=False)
        self.tree_procs.column("cpu", width=70, anchor="center", stretch=False)
        self.tree_procs.column("ram", width=80, anchor="center", stretch=False)
        self.tree_procs.column("network", width=90, anchor="center", stretch=False)
        self.tree_procs.column("path", width=400, stretch=True)

        scrollbar = ttk.Scrollbar(self.tab_procs, orient="vertical", command=self.tree_procs.yview)
        self.tree_procs.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree_procs.pack(fill="both", expand=True)

        self.tree_procs.tag_configure("CRITICAL", foreground="#ff5252", background="#2a1212")
        self.tree_procs.tag_configure("SUSPICIOUS", foreground="#ffd700", background="#2a2412")
        self.tree_procs.tag_configure("NORMAL", foreground="#e0e0e0")

        self.tree_procs.bind("<<TreeviewSelect>>", self.on_select_item)
        self.tree_procs.bind("<Button-3>", self.show_context_menu)

    # --- TAB 2: AĞ & DNS ---
    def setup_network_tab(self):
        top_net_frame = tk.Frame(self.tab_network, bg="#1e1e1e", padx=10, pady=10)
        top_net_frame.pack(fill="x", side="top", padx=5, pady=5)

        tk.Label(top_net_frame, text="⚡ Hızlı Ağ & DNS Araçları:", fg="#00b0ff", bg="#1e1e1e", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)

        btn_cloudflare = tk.Button(top_net_frame, text="Cloudflare DNS (1.1.1.1)", command=lambda: self.set_dns("1.1.1.1", "1.0.0.1"), bg="#00838f", fg="white", bd=0, padx=8, pady=4, cursor="hand2")
        btn_cloudflare.pack(side="left", padx=5)

        btn_google = tk.Button(top_net_frame, text="Google DNS (8.8.8.8)", command=lambda: self.set_dns("8.8.8.8", "8.8.4.4"), bg="#0288d1", fg="white", bd=0, padx=8, pady=4, cursor="hand2")
        btn_google.pack(side="left", padx=5)

        btn_reset_winsock = tk.Button(top_net_frame, text="Winsock & IP Reset", command=self.reset_winsock, bg="#d32f2f", fg="white", bd=0, padx=8, pady=4, cursor="hand2")
        btn_reset_winsock.pack(side="left", padx=5)

        columns = ("pid", "name", "local", "remote", "status")
        self.tree_net = ttk.Treeview(self.tab_network, columns=columns, show="headings", selectmode="browse")

        headers = {
            "pid": "PID", "name": "İşlem Adı", "local": "Yerel Adres / Port",
            "remote": "Uzak Bağlantı (IP:Port)", "status": "Durum"
        }

        for col, text in headers.items():
            self.tree_net.heading(col, text=text, command=lambda _col=col: self.on_header_click("net", self.tree_net, _col))

        self.tree_net.column("pid", width=70, stretch=False)
        self.tree_net.column("name", width=180, stretch=False)
        self.tree_net.column("local", width=220, stretch=False)
        self.tree_net.column("remote", width=250, stretch=False)
        self.tree_net.column("status", width=120, anchor="center", stretch=True)

        scrollbar = ttk.Scrollbar(self.tab_network, orient="vertical", command=self.tree_net.yview)
        self.tree_net.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree_net.pack(fill="both", expand=True)

    # --- TAB 3: OPTİMİZASYON & TELEMETRY ---
    def setup_optimization_tab(self):
        container = tk.Frame(self.tab_opt, bg="#121212", padx=20, pady=10)
        container.pack(fill="both", expand=True)

        # Geri Yükleme
        card0 = tk.LabelFrame(container, text=" 🛡️ Güvenlik & Geri Düzeltme Önlemi ", bg="#1e1e1e", fg="#00e676", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        card0.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        tk.Label(card0, text="Sistem değişikliklerinden önce geri dönüş noktası oluşturun.", fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 8)).pack(anchor="w", pady=2)
        btn_restore_frame = tk.Frame(card0, bg="#1e1e1e")
        btn_restore_frame.pack(fill="x", pady=3)
        tk.Button(btn_restore_frame, text="📌 Geri Yükleme Noktası Oluştur", command=self.create_restore_point, bg="#2e7d32", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_restore_frame, text="⏪ Geri Yükleme Noktalarını Yönet", command=self.open_system_restore_gui, bg="#00838f", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=5)

        # Temizlik
        card1 = tk.LabelFrame(container, text=" 🧹 Disk & Derin Temizlik ", bg="#1e1e1e", fg="#00b0ff", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        card1.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        tk.Button(card1, text="Derin Temp Temizliği Başlat", command=self.clean_temp_files, bg="#0288d1", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(anchor="w", pady=5)

        # Geri Dönüşüm
        card2 = tk.LabelFrame(container, text=" 🗑️ Geri Dönüşüm Kutusu ", bg="#1e1e1e", fg="#ff9800", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        card2.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        tk.Button(card2, text="Geri Dönüşüm Kutusunu Boşalt", command=self.empty_recycle_bin, bg="#f57c00", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(anchor="w", pady=5)

        # Telemetry & Performans
        card3 = tk.LabelFrame(container, text=" 🔒 Telemetry (Gizlilik) & Performans Modu ", bg="#1e1e1e", fg="#ab47bc", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        card3.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        tk.Label(card3, text="Windows'un arka plan veri toplama servislerini kapatarak işlemci yükünü azaltın.", fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 8)).pack(anchor="w", pady=2)
        btn_telem_frame = tk.Frame(card3, bg="#1e1e1e")
        btn_telem_frame.pack(fill="x", pady=3)

        tk.Button(btn_telem_frame, text="🚫 Telemetry Veri Toplamayı Kapat", command=self.disable_telemetry, bg="#7b1fa2", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_telem_frame, text="🚀 Nihai Performans Modunu Aç", command=self.enable_ultimate_performance, bg="#c2185b", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=5)

        # Tanılama & Otomatik Sorun Giderme
        card4 = tk.LabelFrame(container, text=" 🩺 Sistem Tanılama & Otomatik Sorun Giderme ", bg="#1e1e1e", fg="#00e5ff", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        card4.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        container.grid_rowconfigure(3, weight=1)

        tk.Label(card4, text="Sistemi tarayarak disk, ağ, güvenlik ve performansla ilgili yaygın sorunları tespit edin; tek tek veya toplu olarak düzeltin.", fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 8), wraplength=900, justify="left").pack(anchor="w", pady=2)

        btn_diag_frame = tk.Frame(card4, bg="#1e1e1e")
        btn_diag_frame.pack(fill="x", pady=5)

        self.btn_scan_issues = tk.Button(btn_diag_frame, text="🔍 Sistemi Tara (Sorunları Tespit Et)", command=self.scan_system_issues, bg="#0288d1", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2")
        self.btn_scan_issues.pack(side="left", padx=5)

        self.btn_fix_all = tk.Button(btn_diag_frame, text="🛠️ Tümünü Düzelt", command=self.fix_all_issues, bg="#2e7d32", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2")
        self.btn_fix_all.pack(side="left", padx=5)

        self.btn_export_csv = tk.Button(btn_diag_frame, text="📄 CSV'ye Aktar", command=self.export_issues_csv, bg="#455a64", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2")
        self.btn_export_csv.pack(side="left", padx=5)

        self.lbl_diag_status = tk.Label(btn_diag_frame, text="Henüz tarama yapılmadı.", fg="#888888", bg="#1e1e1e", font=("Segoe UI", 8, "italic"))
        self.lbl_diag_status.pack(side="left", padx=15)

        columns = ("severity", "title", "description", "category")
        self.tree_issues = ttk.Treeview(card4, columns=columns, show="headings", selectmode="extended", height=8)
        self.tree_issues.heading("severity", text="Önem")
        self.tree_issues.heading("title", text="Sorun")
        self.tree_issues.heading("description", text="Açıklama")
        self.tree_issues.heading("category", text="Kategori")

        self.tree_issues.column("severity", width=80, anchor="center", stretch=False)
        self.tree_issues.column("title", width=220, stretch=False)
        self.tree_issues.column("description", width=430, stretch=True)
        self.tree_issues.column("category", width=120, anchor="center", stretch=False)

        self.tree_issues.tag_configure("Yüksek", foreground="#ff5252", background="#2a1212")
        self.tree_issues.tag_configure("Orta", foreground="#ffd700", background="#2a2412")
        self.tree_issues.tag_configure("Düşük", foreground="#80d8ff", background="#122228")

        self.tree_issues.pack(fill="both", expand=True, pady=5)
        self.tree_issues.bind("<Button-3>", self.show_issue_context_menu)
        self.tree_issues.bind("<Double-1>", lambda e: self.fix_selected_issues())

        self.issue_context_menu = tk.Menu(self.root, tearoff=0, bg="#2a2a2a", fg="#ffffff", activebackground="#005c99", activeforeground="#ffffff", bd=0)
        self.issue_context_menu.add_command(label="🛠️ Bu Sorunu/Sorunları Düzelt", command=self.fix_selected_issues)
        self.issue_context_menu.add_command(label="ℹ️ Detayları Göster", command=self.show_issue_details)
        self.issue_context_menu.add_separator()
        self.issue_context_menu.add_command(label="🗑️ Listeden Kaldır (Yoksay)", command=self.dismiss_selected_issues)

        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

    # --- TAB 4: LİSANS & BAŞLANGIÇ (AUTORUN) ---
    def setup_autorun_license_tab(self):
        container = tk.Frame(self.tab_autorun, bg="#121212", padx=15, pady=10)
        container.pack(fill="both", expand=True)

        # Lisans Denetleyici & Resmi Aktivasyon Araçları
        lic_frame = tk.LabelFrame(container, text=" 🔑 Windows & Office Lisanslama Aracı ", bg="#1e1e1e", fg="#00e676", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        lic_frame.pack(fill="x", pady=5)

        tk.Label(lic_frame, text="Mevcut lisans/etkinleştirme durumunuzu sorgulayabilir veya Windows'un resmi etkinleştirme ve lisans yönetim araçlarını açabilirsiniz.", fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 8)).pack(anchor="w", pady=2)

        btn_lic_frame = tk.Frame(lic_frame, bg="#1e1e1e")
        btn_lic_frame.pack(fill="x", pady=5)

        tk.Button(btn_lic_frame, text="🔍 Lisans Durumunu Sorgula (slmgr)", command=self.check_license_status, bg="#2e7d32", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=5, pady=3)

        btn_lic_frame2 = tk.Frame(lic_frame, bg="#1e1e1e")
        btn_lic_frame2.pack(fill="x", pady=2)

        tk.Button(btn_lic_frame2, text="⚙️ Windows Etkinleştirme Ayarlarını Aç", command=self.open_activation_settings, bg="#0288d1", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=5, pady=3)
        tk.Button(btn_lic_frame2, text="🔑 Ürün Anahtarı Sihirbazını Aç (slui)", command=self.open_slui_wizard, bg="#00838f", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=5, pady=3)
        tk.Button(btn_lic_frame2, text="🌐 Microsoft Lisans Satın Alma Sayfası", command=self.open_ms_purchase_page, bg="#7b1fa2", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=5, pady=3)

        btn_lic_frame3 = tk.Frame(lic_frame, bg="#1e1e1e")
        btn_lic_frame3.pack(fill="x", pady=2)

        tk.Button(btn_lic_frame3, text="📊 Sistem Bilgisi (winver)", command=self.open_winver, bg="#455a64", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=5, pady=3)
        tk.Button(btn_lic_frame3, text="🖥️ Office Hesap & Etkinleştirme (Office)", command=self.open_office_activation, bg="#455a64", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(side="left", padx=5, pady=3)

        # Registry Başlangıç Öğeleri (Autorun)
        auto_frame = tk.LabelFrame(container, text=" 🚀 Registry Başlangıç Öğeleri (Autorun) ", bg="#1e1e1e", fg="#00b0ff", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        auto_frame.pack(fill="both", expand=True, pady=5)

        btn_auto_top = tk.Frame(auto_frame, bg="#1e1e1e")
        btn_auto_top.pack(fill="x", pady=3)

        tk.Button(btn_auto_top, text="🔄 Başlangıç Öğelerini Tara", command=self.scan_registry_startup, bg="#0288d1", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=4, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_auto_top, text="🗑️ Seçili Başlangıç Kaydını Sil", command=self.delete_selected_startup_entry, bg="#d32f2f", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=4, cursor="hand2").pack(side="left", padx=5)

        columns = ("name", "path", "location")
        self.tree_autorun = ttk.Treeview(auto_frame, columns=columns, show="headings", selectmode="browse")
        self.tree_autorun.heading("name", text="Program Adı")
        self.tree_autorun.heading("path", text="Çalıştırılan Komut / Yol")
        self.tree_autorun.heading("location", text="Registry Konumu")

        self.tree_autorun.column("name", width=180, stretch=False)
        self.tree_autorun.column("path", width=450, stretch=True)
        self.tree_autorun.column("location", width=200, stretch=False)

        self.tree_autorun.pack(fill="both", expand=True, pady=5)

    # --- TAB 5: DİSK & RAPORLAMA ---
    def setup_disk_analyzer_tab(self):
        container = tk.Frame(self.tab_disk, bg="#121212", padx=15, pady=10)
        container.pack(fill="both", expand=True)

        # Raporlama
        rep_frame = tk.LabelFrame(container, text=" 📄 Sistem Durum Raporu ", bg="#1e1e1e", fg="#ff9800", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        rep_frame.pack(fill="x", pady=5)

        tk.Label(rep_frame, text="Tüm aktif süreçlerin ve sistem performansının özet raporunu masaüstüne kaydedin.", fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 8)).pack(anchor="w", pady=2)
        tk.Button(rep_frame, text="💾 Sistem Bakım Raporunu Kaydet (.txt)", command=self.export_system_report, bg="#f57c00", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2").pack(anchor="w", pady=5)

        # Büyük Dosya Analizörü
        disk_frame = tk.LabelFrame(container, text=" 🔍 Büyük Dosya Analizörü (Diskte Yer Açın) ", bg="#1e1e1e", fg="#ab47bc", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        disk_frame.pack(fill="both", expand=True, pady=5)

        btn_disk_top = tk.Frame(disk_frame, bg="#1e1e1e")
        btn_disk_top.pack(fill="x", pady=3)

        tk.Button(btn_disk_top, text="📁 C:\\ Sürücüsünü Tara (İlk 15 Büyük Dosya)", command=self.start_large_file_scan, bg="#7b1fa2", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=4, cursor="hand2").pack(side="left", padx=5)

        columns = ("size", "path")
        self.tree_disk = ttk.Treeview(disk_frame, columns=columns, show="headings", selectmode="browse")
        self.tree_disk.heading("size", text="Dosya Boyutu (MB)")
        self.tree_disk.heading("path", text="Dosya Yolu")

        self.tree_disk.column("size", width=140, anchor="center", stretch=False)
        self.tree_disk.column("path", width=650, stretch=True)

        self.tree_disk.pack(fill="both", expand=True, pady=5)

    # --- TAB 6: HAKKINDA & GÜNCELLEME ---
    def setup_about_tab(self):
        container = tk.Frame(self.tab_about, bg="#121212", padx=20, pady=15)
        container.pack(fill="both", expand=True)

        # Uygulama Bilgisi & Güncelleme
        info_frame = tk.LabelFrame(container, text=" 🛰️ Ayyıldız Sentinel Pro ", bg="#1e1e1e", fg="#00e676", font=("Segoe UI", 11, "bold"), padx=15, pady=10)
        info_frame.pack(fill="x", pady=5)

        tk.Label(info_frame, text=f"Sürüm: {APP_VERSION}", fg="#e0e0e0", bg="#1e1e1e", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Siber Güvenlik, Sistem Bakımı ve Otomatik Sorun Giderme Süiti.", fg="#aaaaaa", bg="#1e1e1e", font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 8))

        btn_row = tk.Frame(info_frame, bg="#1e1e1e")
        btn_row.pack(fill="x", pady=3)
        tk.Button(btn_row, text="🔄 Güncellemeleri Kontrol Et", command=self.check_for_updates, bg="#0288d1", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_row, text="🐙 GitHub Reposunu Aç", command=lambda: webbrowser.open(GITHUB_REPO_URL), bg="#333333", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_row, text="🐞 Hata / Öneri Bildir", command=lambda: webbrowser.open(GITHUB_REPO_URL + "/issues"), bg="#333333", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=5)

        self.lbl_update_status = tk.Label(info_frame, text="", fg="#888888", bg="#1e1e1e", font=("Segoe UI", 8, "italic"))
        self.lbl_update_status.pack(anchor="w", pady=(4, 0))

        # Sistem Bilgisi
        sys_frame = tk.LabelFrame(container, text=" 🖥️ Sistem Bilgisi ", bg="#1e1e1e", fg="#00b0ff", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        sys_frame.pack(fill="both", expand=True, pady=5)

        tk.Button(sys_frame, text="🔍 Sistem Bilgisini Yenile", command=self.gather_system_info, bg="#0288d1", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=4, cursor="hand2").pack(anchor="w", pady=3)

        self.txt_sysinfo = tk.Text(sys_frame, bg="#181818", fg="#e0e0e0", font=("Consolas", 9), height=10, wrap="word", relief="flat", padx=8, pady=8)
        self.txt_sysinfo.pack(fill="both", expand=True, pady=5)
        self.txt_sysinfo.insert("1.0", "Bilgileri görmek için 'Sistem Bilgisini Yenile' düğmesine basın.")
        self.txt_sysinfo.config(state="disabled")

        # İşlem Günlüğü
        log_frame = tk.LabelFrame(container, text=" 📜 İşlem Günlüğü (Audit Log) ", bg="#1e1e1e", fg="#ff9800", font=("Segoe UI", 10, "bold"), padx=15, pady=8)
        log_frame.pack(fill="x", pady=5)

        tk.Label(log_frame, text="Uygulama üzerinden yapılan tüm kritik işlemler (temizlik, düzeltme, silme vb.) burada kayıt altına alınır.", fg="#cccccc", bg="#1e1e1e", font=("Segoe UI", 8)).pack(anchor="w", pady=2)
        btn_log_row = tk.Frame(log_frame, bg="#1e1e1e")
        btn_log_row.pack(fill="x", pady=3)
        tk.Button(btn_log_row, text="📖 Günlüğü Görüntüle", command=self.view_action_log, bg="#455a64", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=4, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_log_row, text="📂 Günlük Dosyasını Aç", command=self.open_log_file_location, bg="#455a64", fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, pady=4, cursor="hand2").pack(side="left", padx=5)

    def log_action(self, message):
        """Kritik işlemleri zaman damgasıyla günlük dosyasına yazar."""
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass

    def view_action_log(self):
        if not os.path.exists(self.log_file_path):
            messagebox.showinfo("Günlük Boş", "Henüz kaydedilmiş bir işlem bulunmuyor.")
            return
        try:
            with open(self.log_file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Hata", f"Günlük okunamadı: {e}")
            return

        log_win = tk.Toplevel(self.root)
        log_win.title("İşlem Günlüğü")
        log_win.geometry("700x500")
        log_win.configure(bg="#121212")
        txt = tk.Text(log_win, bg="#181818", fg="#e0e0e0", font=("Consolas", 9), wrap="word", padx=10, pady=10)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", content if content.strip() else "Günlük boş.")
        txt.config(state="disabled")

    def open_log_file_location(self):
        if os.path.exists(self.log_file_path):
            subprocess.run(f'explorer /select,"{self.log_file_path}"')
        else:
            messagebox.showinfo("Bulunamadı", "Günlük dosyası henüz oluşturulmadı.")

    def check_for_updates(self):
        self.lbl_update_status.config(text="Kontrol ediliyor...", fg="#888888")
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self):
        try:
            req = urllib.request.Request(GITHUB_API_LATEST_RELEASE, headers={"User-Agent": "AyyildizSentinelPro"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latest_tag = data.get("tag_name", "").lstrip("v")
            release_url = data.get("html_url", GITHUB_REPO_URL)

            def parse_ver(v):
                try:
                    return tuple(int(x) for x in v.split("."))
                except Exception:
                    return (0,)

            if latest_tag and parse_ver(latest_tag) > parse_ver(APP_VERSION):
                self.root.after(0, lambda: self._show_update_available(latest_tag, release_url))
            else:
                self.root.after(0, lambda: self.lbl_update_status.config(text=f"En güncel sürümü kullanıyorsunuz (v{APP_VERSION}).", fg="#00e676"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.root.after(0, lambda: self.lbl_update_status.config(text="Henüz yayınlanmış bir sürüm bulunamadı (repo boş olabilir).", fg="#888888"))
            else:
                self.root.after(0, lambda: self.lbl_update_status.config(text=f"Güncelleme kontrolü başarısız: HTTP {e.code}", fg="#ff5252"))
        except Exception as e:
            self.root.after(0, lambda: self.lbl_update_status.config(text=f"Güncelleme kontrolü başarısız: {e}", fg="#ff5252"))

    def _show_update_available(self, latest_tag, release_url):
        self.lbl_update_status.config(text=f"Yeni sürüm mevcut: v{latest_tag}", fg="#ffab40")
        if messagebox.askyesno("Güncelleme Mevcut", f"Yeni sürüm bulundu: v{latest_tag}\nMevcut sürümünüz: v{APP_VERSION}\n\nİndirme sayfası açılsın mı?"):
            webbrowser.open(release_url)

    def gather_system_info(self):
        self.txt_sysinfo.config(state="normal")
        self.txt_sysinfo.delete("1.0", "end")
        self.txt_sysinfo.insert("1.0", "Sistem bilgisi toplanıyor, lütfen bekleyin...")
        self.txt_sysinfo.config(state="disabled")
        threading.Thread(target=self._gather_system_info_worker, daemon=True).start()

    def _gather_system_info_worker(self):
        lines = []
        try:
            lines.append(f"İşletim Sistemi : {platform.platform()}")
            lines.append(f"Bilgisayar Adı  : {platform.node()}")
            lines.append(f"İşlemci (CPU)   : {platform.processor() or 'Bilinmiyor'}")
            lines.append(f"Çekirdek Sayısı : {psutil.cpu_count(logical=False)} Fiziksel / {psutil.cpu_count(logical=True)} Mantıksal")
            ram_total = round(psutil.virtual_memory().total / (1024**3), 1)
            lines.append(f"Toplam RAM      : {ram_total} GB")
            total, used, free = shutil.disk_usage("C:\\")
            lines.append(f"C: Disk Toplam  : {round(total/(1024**3),1)} GB  |  Boş: {round(free/(1024**3),1)} GB")
        except Exception as e:
            lines.append(f"Temel bilgiler alınamadı: {e}")

        try:
            stdout, _ = self._run_ps_capture(
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name", timeout=8)
            gpu_names = [n.strip() for n in stdout.splitlines() if n.strip()]
            if gpu_names:
                lines.append(f"Ekran Kartı     : {', '.join(gpu_names)}")
        except Exception:
            pass

        try:
            stdout, _ = self._run_ps_capture(
                "(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion", timeout=8)
            bios = stdout.strip()
            if bios:
                lines.append(f"BIOS Sürümü     : {bios}")
        except Exception:
            pass

        try:
            stdout, _ = self._run_ps_capture(
                "(Get-CimInstance Win32_BaseBoard).Product", timeout=8)
            board = stdout.strip()
            if board:
                lines.append(f"Anakart         : {board}")
        except Exception:
            pass

        self.root.after(0, self._display_system_info, "\n".join(lines))

    def _display_system_info(self, text):
        self.txt_sysinfo.config(state="normal")
        self.txt_sysinfo.delete("1.0", "end")
        self.txt_sysinfo.insert("1.0", text)
        self.txt_sysinfo.config(state="disabled")

    # --- YARDIMCI METOTLAR VE EYLEMLER ---
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#2a2a2a", fg="#ffffff", activebackground="#005c99", activeforeground="#ffffff", bd=0)
        self.context_menu.add_command(label="📂 Dosya Konumunu Aç", command=self.open_file_location)
        self.context_menu.add_command(label="📋 SHA-256 Hash Kopyala", command=self.copy_hash)
        self.context_menu.add_command(label="🌐 VirusTotal'de İncele", command=self.search_virustotal)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Programı Kaldır", command=self.uninstall_program)
        self.context_menu.add_command(label="🛑 Görevi Sonlandır", command=self.kill_selected_process)

    def show_context_menu(self, event):
        item = self.tree_procs.identify_row(event.y)
        if item:
            self.tree_procs.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def on_header_click(self, tab_key, tree, col):
        current_col = self.sort_state[tab_key]["col"]
        current_rev = self.sort_state[tab_key]["reverse"]

        if current_col == col:
            self.sort_state[tab_key]["reverse"] = not current_rev
        else:
            self.sort_state[tab_key]["col"] = col
            self.sort_state[tab_key]["reverse"] = False

        self.sort_tree_data(tree, tab_key)

    def sort_tree_data(self, tree, tab_key):
        col = self.sort_state[tab_key]["col"]
        reverse = self.sort_state[tab_key]["reverse"]

        items = [(tree.set(k, col), k) for k in tree.get_children('')]

        def parse_value(val):
            clean = str(val).replace('%', '').replace(' MB', '').replace('AKTİF', '').strip()
            try:
                return float(clean)
            except ValueError:
                return str(val).lower()

        items.sort(key=lambda t: parse_value(t[0]), reverse=reverse)

        for index, (val, k) in enumerate(items):
            tree.move(k, '', index)

    def analyze_path(self, name, exe_path):
        if not exe_path:
            if name.lower() in ["system idle process", "system", "registry", "memory compression"]:
                return "Güvenli (Çekirdek)", "NORMAL"
            return "Yol Alınamadı", "NORMAL"

        p_lower = exe_path.lower()
        n_lower = name.lower()

        if n_lower == "explorer.exe":
            if p_lower in [r"c:\windows\explorer.exe", r"c:\windows\syswow64\explorer.exe"]:
                return "Güvenli (Explorer)", "NORMAL"
            else:
                return "SAHTE EXPLORER!", "CRITICAL"

        for s_dir in self.suspicious_dirs:
            if p_lower.startswith(s_dir):
                return "Şüpheli Dizin (Temp/Downloads)", "SUSPICIOUS"

        return "Güvenli", "NORMAL"

    def live_update_loop(self):
        while self.is_running:
            try:
                cpu_usage = psutil.cpu_percent(interval=None)
                ram_usage = psutil.virtual_memory().percent
                
                procs_data = []
                net_data = []

                for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_info']):
                    try:
                        p_info = proc.info
                        pid = p_info['pid']
                        name = p_info['name'] or "Bilinmeyen"
                        exe = p_info['exe'] or ""
                        cpu = p_info['cpu_percent'] or 0.0
                        
                        mem_bytes = p_info['memory_info'].rss if p_info['memory_info'] else 0
                        ram_mb = round(mem_bytes / (1024 * 1024), 1)

                        status_text, tag = self.analyze_path(name, exe)

                        try:
                            conns = proc.net_connections(kind='inet')
                            has_net = f"AKTİF ({len(conns)})" if len(conns) > 0 else "Yok"
                            for c in conns:
                                laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-"
                                raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "LISTEN"
                                net_data.append({
                                    "pid": pid, "name": name, "local": laddr, "remote": raddr, "status": c.status
                                })
                        except Exception:
                            has_net = "Yok"

                        procs_data.append({
                            "pid": pid, "name": name, "status": status_text, "tag": tag,
                            "cpu": f"%{cpu:.1f}", "ram": ram_mb, "net": has_net, "path": exe
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                self.root.after(0, self.update_ui, cpu_usage, ram_usage, procs_data, net_data)

            except Exception as e:
                print(f"Hata: {e}")

            time.sleep(2.0)

    def update_ui(self, cpu, ram, procs_data, net_data):
        self.lbl_cpu.config(text=f"CPU: %{cpu:.1f}")
        self.lbl_ram.config(text=f"RAM: %{ram:.1f}")
        self.lbl_procs.config(text=f"Aktif İşlem: {len(procs_data)}")

        self.current_procs_data = procs_data
        self.current_net_data = net_data

        self.apply_filter()

    def apply_filter(self):
        query = self.search_var.get().lower().strip()
        
        for item in self.tree_procs.get_children():
            self.tree_procs.delete(item)

        if hasattr(self, 'current_procs_data'):
            for p in self.current_procs_data:
                if query in str(p['pid']) or query in p['name'].lower() or query in p['path'].lower():
                    self.tree_procs.insert("", "end", values=(
                        p['pid'], p['name'], p['status'], p['cpu'], p['ram'], p['net'], p['path']
                    ), tags=(p['tag'],))

        self.sort_tree_data(self.tree_procs, "procs")

        for item in self.tree_net.get_children():
            self.tree_net.delete(item)

        if hasattr(self, 'current_net_data'):
            for n in self.current_net_data:
                if query in str(n['pid']) or query in n['name'].lower() or query in n['remote'].lower():
                    self.tree_net.insert("", "end", values=(
                        n['pid'], n['name'], n['local'], n['remote'], n['status']
                    ))

        self.sort_tree_data(self.tree_net, "net")

    def on_select_item(self, event):
        selected = self.tree_procs.selection()
        if selected:
            vals = self.tree_procs.item(selected[0])["values"]
            self.lbl_details.config(text=f"Seçili: {vals[1]} (PID: {vals[0]}) | Yol: {vals[6] if vals[6] else 'N/A'}")

    # --- RESMİ WINDOWS ETKİNLEŞTİRME / LİSANS YÖNLENDİRMELERİ ---
    def open_activation_settings(self):
        """Windows Ayarlar > Etkinleştirme sayfasını açar (resmi sistem ayarı)."""
        try:
            os.system("start ms-settings:activation")
        except Exception as e:
            messagebox.showerror("Hata", f"Etkinleştirme ayarları açılamadı: {e}")

    def open_slui_wizard(self):
        """Windows'un yerleşik Ürün Anahtarı Değiştirme Sihirbazını (slui.exe) açar."""
        try:
            subprocess.run(["slui.exe"], shell=False)
        except Exception as e:
            messagebox.showerror("Hata", f"Ürün anahtarı sihirbazı açılamadı: {e}")

    def open_ms_purchase_page(self):
        """Microsoft'un resmi lisans satın alma / etkinleştirme yardım sayfasını tarayıcıda açar."""
        webbrowser.open("https://www.microsoft.com/software-download/windows11")

    def open_winver(self):
        """Sistem sürüm bilgisini gösteren winver aracını açar."""
        try:
            subprocess.run(["winver.exe"], shell=False)
        except Exception as e:
            messagebox.showerror("Hata", f"Sistem bilgisi açılamadı: {e}")

    def open_office_activation(self):
        """Office hesap ve etkinleştirme durumu sayfasını (resmi Office uygulaması) açmayı dener,
        yoksa Microsoft hesap sayfasını tarayıcıda açar."""
        try:
            subprocess.run(["start", "ms-officeapp:account"], shell=True)
        except Exception:
            webbrowser.open("https://account.microsoft.com/services")

    # --- LİSANS SORGULAMA METODU ---
    def check_license_status(self):
        try:
            raw_output = subprocess.check_output(
                "cscript //nologo %systemroot%\\system32\\slmgr.vbs /dli", 
                shell=True, 
                stderr=subprocess.STDOUT
            )
            res = None
            for enc in ('cp857', 'cp1254', 'cp850', 'utf-8'):
                try:
                    res = raw_output.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if res is None:
                res = raw_output.decode('utf-8', errors='replace')

            messagebox.showinfo("Windows Lisans Durumu", res if res.strip() else "Lisans bilgisi alınamadı.")
        except subprocess.CalledProcessError as e:
            try:
                err_msg = e.output.decode('cp857', errors='replace')
            except Exception:
                err_msg = str(e)
            messagebox.showerror("Hata", f"Lisans sorgulanırken hata oluştu:\n{err_msg}")
        except Exception as e:
            messagebox.showerror("Hata", f"Lisans sorgulanamadı: {e}")

    def open_file_location(self):
        selected = self.tree_procs.selection()
        if not selected: return
        path = self.tree_procs.item(selected[0])["values"][6]
        if path and os.path.exists(path):
            subprocess.run(f'explorer /select,"{path}"')
        else:
            messagebox.showwarning("Bulunamadı", "Dosya yolu mevcut değil.")

    def copy_hash(self):
        selected = self.tree_procs.selection()
        if not selected: return
        path = self.tree_procs.item(selected[0])["values"][6]
        if path and os.path.exists(path):
            try:
                hasher = hashlib.sha256()
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        hasher.update(chunk)
                h_val = hasher.hexdigest()
                self.root.clipboard_clear()
                self.root.clipboard_append(h_val)
                messagebox.showinfo("Kopyalandı", f"SHA-256 Hash Panoya Kopyalandı:\n{h_val}")
            except Exception as e:
                messagebox.showerror("Hata", f"Hash hesaplanamadı: {e}")

    def search_virustotal(self):
        selected = self.tree_procs.selection()
        if not selected: return
        path = self.tree_procs.item(selected[0])["values"][6]
        if path and os.path.exists(path):
            try:
                hasher = hashlib.sha256()
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        hasher.update(chunk)
                webbrowser.open(f"https://www.virustotal.com/gui/file/{hasher.hexdigest()}")
            except Exception:
                webbrowser.open(f"https://www.virustotal.com/gui/search/{self.tree_procs.item(selected[0])['values'][1]}")

    def uninstall_program(self):
        try:
            os.system("start ms-settings:appsfeatures")
        except Exception:
            os.system("control appwiz.cpl")

    def kill_selected_process(self):
        selected = self.tree_procs.selection()
        if not selected: return
        vals = self.tree_procs.item(selected[0])["values"]
        if messagebox.askyesno("Görevi Sonlandır", f"'{vals[1]}' işlemini kapatmak istediğinize emin misiniz?"):
            try:
                psutil.Process(vals[0]).kill()
                self.log_action(f"Süreç sonlandırıldı: {vals[1]} (PID: {vals[0]})")
                messagebox.showinfo("Başarılı", f"{vals[1]} işlemi sonlandırıldı.")
            except Exception as e:
                messagebox.showerror("Hata", f"İşlem kapatılamadı: {e}")

    def create_restore_point(self):
        if messagebox.askyesno("Geri Yükleme Noktası", "Sistem Geri Yükleme Noktası oluşturulsun mu?"):
            try:
                ps_script = "Enable-ComputerRestore -Drive 'C:\\'; Checkpoint-Computer -Description 'Ayyildiz_Sentinel_Pro_Bakim' -RestorePointType 'MODIFY_SETTINGS'"
                encoded_script = base64.b64encode(ps_script.encode('utf-16le')).decode('utf-8')
                cmd = f'powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList \'-NoExit -EncodedCommand {encoded_script}\'"'
                subprocess.run(cmd, shell=True)
                self.log_action("Sistem Geri Yükleme Noktası oluşturma komutu gönderildi.")
                messagebox.showinfo("Bilgi", "Yönetici izni istendi. PowerShell penceresindeki işlemin bitmesini bekleyin.")
            except Exception as e:
                messagebox.showerror("Hata", f"İşlem başarısız: {e}")

    def open_system_restore_gui(self):
        try:
            cmd = 'powershell -Command "Start-Process rstrui.exe -Verb RunAs"'
            subprocess.run(cmd, shell=True)
        except Exception as e:
            messagebox.showerror("Hata", f"Arayüz açılamadı: {e}")

    def clean_temp_files(self):
        deleted_bytes = 0
        temp_paths = [os.path.expanduser("~\\AppData\\Local\\Temp"), "C:\\Windows\\Temp", "C:\\Windows\\Prefetch"]
        for t_path in temp_paths:
            if os.path.exists(t_path):
                for root_dir, dirs, files in os.walk(t_path):
                    for f in files:
                        try:
                            f_path = os.path.join(root_dir, f)
                            deleted_bytes += os.path.getsize(f_path)
                            os.remove(f_path)
                        except Exception: continue
        mb_cleaned = round(deleted_bytes / (1024 * 1024), 2)
        self.log_action(f"Geçici dosya temizliği yapıldı: {mb_cleaned} MB temizlendi.")
        messagebox.showinfo("Temizlik Tamamlandı", f"Başarıyla {mb_cleaned} MB geçici dosya temizlendi!")

    def empty_recycle_bin(self):
        try:
            subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"], capture_output=True)
            self.log_action("Geri Dönüşüm Kutusu boşaltıldı.")
            messagebox.showinfo("Başarılı", "Geri Dönüşüm Kutusu boşaltıldı.")
        except Exception as e:
            messagebox.showerror("Hata", f"İşlem başarısız: {e}")

    def set_dns(self, primary, secondary):
        if messagebox.askyesno("DNS Değiştir", f"DNS adresiniz {primary} ve {secondary} olarak ayarlansın mı?"):
            try:
                cmd = f'powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList \'-Command Set-DnsClientServerAddress -InterfaceAlias Wi-Fi -ServerAddresses (\\\"{primary}\\\",\\\"{secondary}\\\")\'"'
                subprocess.run(cmd, shell=True)
                self.log_action(f"DNS adresleri değiştirildi: {primary}, {secondary}")
                messagebox.showinfo("Başarılı", "DNS değiştirme komutu gönderildi!")
            except Exception as e:
                messagebox.showerror("Hata", f"DNS değiştirilemedi: {e}")

    def reset_winsock(self):
        if messagebox.askyesno("Winsock Reset", "Ağ ayarlarınız ve IP yapısı sıfırlansın mı? (Yönetici yetkisi gerektirir)"):
            try:
                subprocess.run('start cmd /k "netsh winsock reset && netsh int ip reset"', shell=True)
                self.log_action("Winsock ve IP yapılandırması sıfırlandı.")
            except Exception as e:
                messagebox.showerror("Hata", f"Winsock sıfırlanamadı: {e}")

    def disable_telemetry(self):
        if messagebox.askyesno("Telemetry Kapat", "Windows Veri Toplama servisi (DiagTrack) kapatılsın mı?"):
            try:
                cmd = 'powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList \'-Command Stop-Service DiagTrack; Set-Service DiagTrack -StartupType Disabled\'"'
                subprocess.run(cmd, shell=True)
                self.log_action("Telemetry (DiagTrack) servisi durduruldu ve devre dışı bırakıldı.")
                messagebox.showinfo("Başarılı", "Telemetry servisi durduruldu ve devre dışı bırakıldı.")
            except Exception as e:
                messagebox.showerror("Hata", f"İşlem başarısız: {e}")

    def enable_ultimate_performance(self):
        try:
            subprocess.run("powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61", shell=True)
            messagebox.showinfo("Nihai Performans", "Nihai Performans Modu Güç Seçeneklerine eklendi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Güç planı eklenemedi: {e}")

    # =====================================================================
    # SİSTEM TANILAMA & OTOMATİK SORUN GİDERME MODÜLÜ
    # =====================================================================

    def scan_system_issues(self):
        self.btn_scan_issues.config(state="disabled", text="🔄 Taranıyor...")
        self.lbl_diag_status.config(text="Tarama sürüyor, lütfen bekleyin...")
        threading.Thread(target=self._diagnostic_scan_worker, daemon=True).start()

    def _diagnostic_scan_worker(self):
        issues = []
        checks = [
            self._check_disk_space,
            self._check_temp_files,
            self._check_recycle_bin,
            self._check_windows_update_service,
            self._check_pending_reboot,
            self._check_defender_status,
            self._check_system_restore,
            self._check_startup_load,
            self._check_driver_errors,
            self._check_high_ram,
            self._check_dns_resolution,
            self._check_system_file_integrity_hint,
            self._check_firewall_status,
            self._check_last_update_date,
        ]
        for check in checks:
            try:
                result = check()
                if result:
                    issues.extend(result if isinstance(result, list) else [result])
            except Exception:
                continue

        self.root.after(0, self.populate_issues, issues)

    def populate_issues(self, issues):
        for item in self.tree_issues.get_children():
            self.tree_issues.delete(item)
        self.issues_map = {}

        sev_order = {"Yüksek": 0, "Orta": 1, "Düşük": 2}
        issues.sort(key=lambda x: sev_order.get(x["severity"], 3))

        for issue in issues:
            iid = self.tree_issues.insert("", "end", values=(
                issue["severity"], issue["title"], issue["description"], issue["category"]
            ), tags=(issue["severity"],))
            self.issues_map[iid] = issue

        self.btn_scan_issues.config(state="normal", text="🔍 Sistemi Tara (Sorunları Tespit Et)")
        if issues:
            self.lbl_diag_status.config(text=f"Tarama tamamlandı: {len(issues)} sorun bulundu.", fg="#ffab40")
        else:
            self.lbl_diag_status.config(text="Tarama tamamlandı: Herhangi bir sorun bulunamadı. ✅", fg="#00e676")

    def export_issues_csv(self):
        if not self.issues_map:
            messagebox.showinfo("Bilgi", "Dışa aktarılacak bir tarama sonucu bulunmuyor.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Dosyası", "*.csv")], initialfile="Sentinel_Tanilama_Raporu.csv")
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Önem", "Sorun", "Açıklama", "Kategori", "Önerilen Çözüm"])
                for issue in self.issues_map.values():
                    writer.writerow([issue["severity"], issue["title"], issue["description"], issue["category"], issue.get("fix_desc", "")])
            self.log_action(f"Tanılama raporu CSV olarak dışa aktarıldı: {file_path}")
            messagebox.showinfo("Başarılı", f"Rapor kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"CSV dışa aktarılamadı: {e}")

    def show_issue_context_menu(self, event):
        item = self.tree_issues.identify_row(event.y)
        if item:
            if item not in self.tree_issues.selection():
                self.tree_issues.selection_set(item)
            self.issue_context_menu.post(event.x_root, event.y_root)

    def show_issue_details(self):
        selected = self.tree_issues.selection()
        if not selected: return
        issue = self.issues_map.get(selected[0])
        if issue:
            messagebox.showinfo(f"Detay: {issue['title']}", f"Kategori: {issue['category']}\nÖnem: {issue['severity']}\n\n{issue['description']}\n\nÖnerilen Çözüm: {issue.get('fix_desc', 'Belirtilmedi')}")

    def dismiss_selected_issues(self):
        selected = self.tree_issues.selection()
        for iid in selected:
            self.tree_issues.delete(iid)
            self.issues_map.pop(iid, None)

    def fix_selected_issues(self):
        selected = self.tree_issues.selection()
        if not selected:
            messagebox.showwarning("Seçim Yok", "Lütfen düzeltmek istediğiniz sorunu/sorunları seçin.")
            return
        issues_to_fix = [self.issues_map[iid] for iid in selected if iid in self.issues_map]
        self._run_fixes(issues_to_fix, list(selected))

    def fix_all_issues(self):
        all_iids = list(self.issues_map.keys())
        if not all_iids:
            messagebox.showinfo("Bilgi", "Önce sistemi tarayın veya düzeltilecek sorun bulunmuyor.")
            return
        if not messagebox.askyesno("Tümünü Düzelt", f"Tespit edilen {len(all_iids)} sorunun tümü için önerilen düzeltmeler uygulansın mı?\n\nBazı işlemler yönetici izni isteyebilir."):
            return
        issues_to_fix = [self.issues_map[iid] for iid in all_iids]
        self._run_fixes(issues_to_fix, all_iids)

    def _run_fixes(self, issues_to_fix, iids):
        results = []
        for issue, iid in zip(issues_to_fix, iids):
            fix_func = self.FIX_DISPATCH.get(issue["fix_key"])
            if fix_func:
                try:
                    fix_func(self)
                    results.append(f"✔ {issue['title']}")
                    self.tree_issues.delete(iid)
                    self.issues_map.pop(iid, None)
                except Exception as e:
                    results.append(f"✘ {issue['title']} - Hata: {e}")
            else:
                results.append(f"➜ {issue['title']} - Manuel işlem başlatıldı.")

        messagebox.showinfo("Düzeltme Sonucu", "\n".join(results))

    # --- TESPİT (CHECK) FONKSİYONLARI ---

    def _check_disk_space(self):
        try:
            total, used, free = shutil.disk_usage("C:\\")
            free_pct = (free / total) * 100
            if free_pct < 15:
                sev = "Yüksek" if free_pct < 7 else "Orta"
                return {
                    "title": "Düşük Disk Alanı",
                    "description": f"C: sürücüsünde yalnızca %{free_pct:.1f} boş alan kaldı ({round(free/1024/1024/1024,1)} GB).",
                    "category": "Disk", "severity": sev, "fix_key": "disk_space",
                    "fix_desc": "Geçici dosyalar temizlenir ve Geri Dönüşüm Kutusu boşaltılır."
                }
        except Exception:
            return None

    def _check_temp_files(self):
        try:
            total_size = 0
            for t_path in [os.path.expanduser("~\\AppData\\Local\\Temp"), "C:\\Windows\\Temp"]:
                if os.path.exists(t_path):
                    for root_dir, dirs, files in os.walk(t_path):
                        for f in files:
                            try:
                                total_size += os.path.getsize(os.path.join(root_dir, f))
                            except Exception:
                                continue
            size_mb = total_size / (1024 * 1024)
            if size_mb > 500:
                return {
                    "title": "Aşırı Geçici Dosya Birikimi",
                    "description": f"Geçici dosya klasörlerinde yaklaşık {round(size_mb)} MB birikmiş.",
                    "category": "Disk", "severity": "Orta" if size_mb < 2000 else "Yüksek", "fix_key": "temp_files",
                    "fix_desc": "Geçici dosyalar (Temp/Prefetch) temizlenir."
                }
        except Exception:
            return None

    def _check_recycle_bin(self):
        try:
            import ctypes
            class SHQUERYRBINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint32), ("i64Size", ctypes.c_int64), ("i64NumItems", ctypes.c_int64)]
            info = SHQUERYRBINFO()
            info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
            ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
            size_mb = info.i64Size / (1024 * 1024)
            if size_mb > 1000:
                return {
                    "title": "Dolu Geri Dönüşüm Kutusu",
                    "description": f"Geri Dönüşüm Kutusu yaklaşık {round(size_mb)} MB yer kaplıyor.",
                    "category": "Disk", "severity": "Düşük", "fix_key": "recycle_bin",
                    "fix_desc": "Geri Dönüşüm Kutusu boşaltılır."
                }
        except Exception:
            return None

    def _check_windows_update_service(self):
        try:
            svc = psutil.win_service_get("wuauserv")
            info = svc.as_dict()
            if info.get("status") == "stopped" and info.get("start_type") == "disabled":
                return {
                    "title": "Windows Update Servisi Devre Dışı",
                    "description": "Windows Update servisi (wuauserv) durdurulmuş ve devre dışı bırakılmış durumda. Bu, güvenlik güncellemelerinin alınmasını engeller.",
                    "category": "Güvenlik", "severity": "Yüksek", "fix_key": "wu_service",
                    "fix_desc": "Servis Manuel başlangıç tipine alınıp başlatılır."
                }
        except Exception:
            return None

    def _check_pending_reboot(self):
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            try:
                winreg.QueryValueEx(key, "PendingFileRenameOperations")
                pending = True
            except FileNotFoundError:
                pending = False
            winreg.CloseKey(key)
            if pending:
                return {
                    "title": "Bekleyen Yeniden Başlatma",
                    "description": "Sistemde tamamlanmayı bekleyen dosya işlemleri var; bilgisayarın yeniden başlatılması gerekiyor.",
                    "category": "Sistem", "severity": "Orta", "fix_key": "pending_reboot",
                    "fix_desc": "Kullanıcı onayıyla sistem yeniden başlatılır."
                }
        except Exception:
            return None

    def _run_ps_capture(self, ps_command, timeout=10):
        """PowerShell çıktısını sistem yerel kod sayfasından (cp1254 vb.) bağımsız,
        güvenli şekilde UTF-8 olarak yakalar. Kod sayfası uyuşmazlığından kaynaklanan
        UnicodeDecodeError hatalarını önler."""
        full_cmd = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + ps_command
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", full_cmd],
            capture_output=True, timeout=timeout
        )
        stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
        stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        return stdout, stderr

    def _check_defender_status(self):
        try:
            stdout, _ = self._run_ps_capture("(Get-MpComputerStatus).RealTimeProtectionEnabled", timeout=8)
            output = stdout.strip().lower()
            if output == "false":
                return {
                    "title": "Gerçek Zamanlı Koruma Kapalı",
                    "description": "Windows Defender gerçek zamanlı koruma özelliği şu anda devre dışı.",
                    "category": "Güvenlik", "severity": "Yüksek", "fix_key": "defender",
                    "fix_desc": "Gerçek zamanlı koruma yeniden etkinleştirilir."
                }
        except Exception:
            return None

    def _check_system_restore(self):
        try:
            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            try:
                val, _ = winreg.QueryValueEx(key, "RPSessionInterval")
                disabled = (val == 0)
            except FileNotFoundError:
                disabled = False
            winreg.CloseKey(key)
            if disabled:
                return {
                    "title": "Sistem Geri Yükleme Kapalı",
                    "description": "Sistem Geri Yükleme (System Restore) özelliği etkin değil; olası bir sorunda geri dönüş noktası olmayabilir.",
                    "category": "Güvenlik", "severity": "Orta", "fix_key": "system_restore",
                    "fix_desc": "Sistem Geri Yükleme etkinleştirilir ve bir kontrol noktası oluşturulur."
                }
        except Exception:
            return None

    def _check_startup_load(self):
        try:
            count = 0
            for hkey, subkey in [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]:
                try:
                    key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
                    i = 0
                    while True:
                        try:
                            winreg.EnumValue(key, i)
                            count += 1
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception:
                    continue
            if count > 12:
                return {
                    "title": "Aşırı Başlangıç Programı",
                    "description": f"Sistem açılışında {count} program otomatik başlıyor; bu açılış süresini uzatabilir.",
                    "category": "Performans", "severity": "Düşük", "fix_key": "startup_load",
                    "fix_desc": "İncelemeniz için Lisans & Başlangıç sekmesindeki başlangıç listesi açılır."
                }
        except Exception:
            return None

    def _check_driver_errors(self):
        try:
            stdout, _ = self._run_ps_capture(
                "Get-CimInstance Win32_PnPEntity | Where-Object { $_.ConfigManagerErrorCode -ne 0 } | Select-Object -ExpandProperty Name",
                timeout=10
            )
            names = [n.strip() for n in stdout.splitlines() if n.strip()]
            if names:
                return {
                    "title": "Sürücü Hatası Tespit Edildi",
                    "description": f"{len(names)} donanım biriminde sürücü hatası var: {', '.join(names[:3])}{'...' if len(names) > 3 else ''}",
                    "category": "Donanım", "severity": "Orta", "fix_key": "driver_error",
                    "fix_desc": "Aygıt Yöneticisi (devmgmt.msc) açılır, sürücüler manuel incelenmelidir."
                }
        except Exception:
            return None

    def _check_high_ram(self):
        try:
            ram = psutil.virtual_memory().percent
            if ram > 90:
                return {
                    "title": "Kritik RAM Kullanımı",
                    "description": f"Sistem belleği %{ram:.1f} oranında dolu. Bu performans sorunlarına yol açabilir.",
                    "category": "Performans", "severity": "Yüksek", "fix_key": "high_ram",
                    "fix_desc": "İncelemeniz için Süreçler sekmesi RAM'e göre sıralanmış olarak açılır."
                }
        except Exception:
            return None

    def _check_dns_resolution(self):
        try:
            socket.setdefaulttimeout(3)
            socket.gethostbyname("www.microsoft.com")
        except Exception:
            return {
                "title": "DNS Çözümleme Sorunu",
                "description": "Alan adı çözümlemesi başarısız oluyor; internet bağlantınızda veya DNS ayarlarınızda sorun olabilir.",
                "category": "Ağ", "severity": "Orta", "fix_key": "dns_issue",
                "fix_desc": "DNS önbelleği temizlenir (ipconfig /flushdns)."
            }
        return None

    def _check_system_file_integrity_hint(self):
        return {
            "title": "Periyodik Sistem Dosyası Kontrolü",
            "description": "Sistem dosyası bütünlüğü uzun süredir kontrol edilmemiş olabilir. Düzenli SFC/DISM taraması önerilir.",
            "category": "Bakım", "severity": "Düşük", "fix_key": "sfc_scan",
            "fix_desc": "Yönetici olarak sfc /scannow ve DISM RestoreHealth çalıştırılır."
        }

    def _check_firewall_status(self):
        try:
            stdout, _ = self._run_ps_capture(
                "Get-NetFirewallProfile | ForEach-Object { \"$($_.Name):$($_.Enabled)\" }", timeout=8)
            disabled_profiles = [line.split(":")[0] for line in stdout.splitlines() if line.strip().endswith("False")]
            if disabled_profiles:
                return {
                    "title": "Güvenlik Duvarı Kapalı",
                    "description": f"Şu ağ profillerinde Windows Güvenlik Duvarı devre dışı: {', '.join(disabled_profiles)}.",
                    "category": "Güvenlik", "severity": "Yüksek", "fix_key": "firewall_off",
                    "fix_desc": "Tüm profillerde Windows Güvenlik Duvarı yeniden etkinleştirilir."
                }
        except Exception:
            return None

    def _check_last_update_date(self):
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\Results\Install"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            try:
                last_success, _ = winreg.QueryValueEx(key, "LastSuccessTime")
            except FileNotFoundError:
                last_success = None
            winreg.CloseKey(key)
            if last_success:
                last_date = datetime.strptime(last_success.split(".")[0], "%Y-%m-%d %H:%M:%S")
                days_since = (datetime.now() - last_date).days
                if days_since > 60:
                    return {
                        "title": "Uzun Süredir Güncelleme Yapılmamış",
                        "description": f"Son başarılı Windows güncellemesi {days_since} gün önce yapılmış. Güvenlik yamaları eksik olabilir.",
                        "category": "Güvenlik", "severity": "Orta", "fix_key": "wu_check",
                        "fix_desc": "Windows Update ayarları açılır, güncellemeler manuel kontrol edilmelidir."
                    }
        except Exception:
            return None



    def _fix_disk_space(self):
        self.clean_temp_files()
        self.empty_recycle_bin()
        self.log_action("Tanılama: Düşük disk alanı sorunu için temp temizliği ve geri dönüşüm boşaltma uygulandı.")

    def _fix_temp_files(self):
        self.clean_temp_files()
        self.log_action("Tanılama: Geçici dosyalar temizlendi.")

    def _fix_recycle_bin(self):
        self.empty_recycle_bin()
        self.log_action("Tanılama: Geri Dönüşüm Kutusu boşaltıldı.")

    def _fix_wu_service(self):
        cmd = 'powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList \'-Command Set-Service wuauserv -StartupType Manual; Start-Service wuauserv\'"'
        subprocess.run(cmd, shell=True)
        self.log_action("Tanılama: Windows Update servisi başlatıldı ve Manuel başlangıç tipine ayarlandı.")

    def _fix_pending_reboot(self):
        if messagebox.askyesno("Yeniden Başlat", "Bekleyen işlemleri tamamlamak için bilgisayar şimdi yeniden başlatılsın mı? (60 saniye içinde)"):
            subprocess.run("shutdown /r /t 60", shell=True)
            self.log_action("Tanılama: Bekleyen yeniden başlatma için sistem yeniden başlatma zamanlandı (60sn).")
            messagebox.showinfo("Bilgi", "Yeniden başlatma 60 saniye içinde gerçekleşecek. İptal etmek için 'shutdown /a' komutunu çalıştırabilirsiniz.")

    def _fix_defender(self):
        cmd = 'powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList \'-Command Set-MpPreference -DisableRealtimeMonitoring $false\'"'
        subprocess.run(cmd, shell=True)
        self.log_action("Tanılama: Windows Defender gerçek zamanlı koruma yeniden etkinleştirildi.")

    def _fix_system_restore(self):
        self.create_restore_point()
        self.log_action("Tanılama: Sistem Geri Yükleme etkinleştirme/kontrol noktası işlemi başlatıldı.")

    def _fix_startup_load(self):
        self.notebook.select(self.tab_autorun)
        self.scan_registry_startup()
        self.log_action("Tanılama: Aşırı başlangıç programı uyarısı için Başlangıç sekmesi açıldı.")

    def _fix_driver_error(self):
        subprocess.run(["devmgmt.msc"], shell=True)
        self.log_action("Tanılama: Sürücü hatası incelemesi için Aygıt Yöneticisi açıldı.")

    def _fix_high_ram(self):
        self.notebook.select(self.tab_procs)
        self.sort_state["procs"] = {"col": "ram", "reverse": True}
        self.sort_tree_data(self.tree_procs, "procs")
        self.log_action("Tanılama: Kritik RAM kullanımı için Süreçler sekmesi RAM'e göre sıralandı.")

    def _fix_dns_issue(self):
        subprocess.run("ipconfig /flushdns", shell=True)
        self.log_action("Tanılama: DNS önbelleği temizlendi (ipconfig /flushdns).")

    def _fix_sfc_scan(self):
        cmd = 'powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList \'/k sfc /scannow && DISM /Online /Cleanup-Image /RestoreHealth\'"'
        subprocess.run(cmd, shell=True)
        self.log_action("Tanılama: Yönetici CMD üzerinden sfc /scannow ve DISM RestoreHealth başlatıldı.")

    def _fix_firewall_off(self):
        cmd = 'powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList \'-Command Set-NetFirewallProfile -All -Enabled True\'"'
        subprocess.run(cmd, shell=True)
        self.log_action("Tanılama: Windows Güvenlik Duvarı tüm profillerde yeniden etkinleştirildi.")

    def _fix_wu_check(self):
        os.system("start ms-settings:windowsupdate")
        self.log_action("Tanılama: Uzun süredir güncelleme yapılmamış uyarısı için Windows Update ayarları açıldı.")

    FIX_DISPATCH = {
        "disk_space": _fix_disk_space,
        "temp_files": _fix_temp_files,
        "recycle_bin": _fix_recycle_bin,
        "wu_service": _fix_wu_service,
        "pending_reboot": _fix_pending_reboot,
        "defender": _fix_defender,
        "system_restore": _fix_system_restore,
        "startup_load": _fix_startup_load,
        "driver_error": _fix_driver_error,
        "high_ram": _fix_high_ram,
        "dns_issue": _fix_dns_issue,
        "sfc_scan": _fix_sfc_scan,
        "firewall_off": _fix_firewall_off,
        "wu_check": _fix_wu_check,
    }

    def scan_registry_startup(self):
        for item in self.tree_autorun.get_children():
            self.tree_autorun.delete(item)

        reg_keys = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run")
        ]

        for hkey, subkey, loc_name in reg_keys:
            try:
                key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, i)
                        self.tree_autorun.insert("", "end", values=(name, val, loc_name))
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                continue

    def delete_selected_startup_entry(self):
        selected = self.tree_autorun.selection()
        if not selected: return
        vals = self.tree_autorun.item(selected[0])["values"]
        name, loc_name = vals[0], vals[2]

        if messagebox.askyesno("Kayıt Sil", f"'{name}' başlangıç maddesi Registry'den kalıcı olarak silinsin mi?"):
            try:
                hkey = winreg.HKEY_CURRENT_USER if "HKCU" in loc_name else winreg.HKEY_LOCAL_MACHINE
                key = winreg.OpenKey(hkey, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, name)
                winreg.CloseKey(key)
                self.log_action(f"Başlangıç kaydı silindi: {name} ({loc_name})")
                messagebox.showinfo("Başarılı", f"'{name}' başlangıçtan kaldırıldı.")
                self.scan_registry_startup()
            except Exception as e:
                messagebox.showerror("Hata", f"Silinirken hata oluştu (Yönetici yetkisi gerekebilir): {e}")

    def export_system_report(self):
        try:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text File", "*.txt")], initialfile="Ayyildiz_Sentinel_Sistem_Raporu.txt")
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("=== AYYILDIZ SENTINEL PRO - SİSTEM RAPORU ===\n\n")
                    f.write(f"Rapor Tarihi: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"CPU Kullanımı: %{psutil.cpu_percent()}\n")
                    f.write(f"RAM Kullanımı: %{psutil.virtual_memory().percent}\n\n")
                    f.write("--- AKTİF ÇALIŞAN SÜREÇLER ---\n")
                    if hasattr(self, 'current_procs_data'):
                        for p in self.current_procs_data:
                            f.write(f"PID: {p['pid']} | Ad: {p['name']} | RAM: {p['ram']}MB | Yol: {p['path']}\n")
                messagebox.showinfo("Başarılı", f"Rapor kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Rapor oluşturulamadı: {e}")

    def start_large_file_scan(self):
        def scan_worker():
            for item in self.tree_disk.get_children():
                self.tree_disk.delete(item)

            file_list = []
            target_dir = "C:\\"
            count = 0
            for root_dir, dirs, files in os.walk(target_dir):
                for f in files:
                    try:
                        f_path = os.path.join(root_dir, f)
                        size_mb = os.path.getsize(f_path) / (1024 * 1024)
                        if size_mb > 100: # 100 MB üstü dosyalar
                            file_list.append((round(size_mb, 1), f_path))
                    except Exception:
                        continue
                count += 1
                if count > 8000: break

            file_list.sort(key=lambda x: x[0], reverse=True)

            for size, path in file_list[:15]:
                self.tree_disk.insert("", "end", values=(size, path))

        threading.Thread(target=scan_worker, daemon=True).start()
        messagebox.showinfo("Tarama Başlatıldı", "C:\\ sürücüsündeki büyük dosyalar arka planda taranıyor, sonuçlar az sonra listede görünecektir.")

    def on_close(self):
        self.is_running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SentinelProGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
