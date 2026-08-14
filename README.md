# 🛰️ Ayyıldız Sentinel Pro

**Siber Güvenlik, Sistem Bakımı ve Otomatik Sorun Giderme Süiti** — Windows için geliştirilmiş, Python/Tkinter tabanlı açık kaynak bir masaüstü uygulaması.

![Platform](https://img.shields.io/badge/platform-Windows-blue) ![Python](https://img.shields.io/badge/python-3.9%2B-yellow) ![License](https://img.shields.io/badge/license-MIT-green)

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Ekran Görüntüleri](#-ekran-görüntüleri)
- [Hızlı Kurulum (Tek Komut)](#-hızlı-kurulum-tek-komut)
- [Manuel Kurulum](#-manuel-kurulum)
- [Kullanım](#-kullanım)
- [Gereksinimler](#-gereksinimler)
- [Güvenlik Notu](#-güvenlik-notu)
- [Katkıda Bulunma](#-katkıda-bulunma)
- [Lisans](#-lisans)

---

## ✨ Özellikler

### 🛡️ Süreçler & Güvenlik
- Gerçek zamanlı işlem (process) izleme: CPU, RAM, ağ kullanımı
- Şüpheli / sahte `explorer.exe` gibi süreçleri otomatik tespit etme
- SHA-256 hash hesaplama ve VirusTotal üzerinde arama
- Sağ tık menüsü ile işlem sonlandırma, dosya konumu açma

### 🌐 Ağ & DNS
- Tüm aktif ağ bağlantılarının canlı listesi
- Tek tıkla Cloudflare / Google DNS değiştirme
- Winsock & IP sıfırlama

### ⚡ Bakım & Telemetry
- Derin geçici dosya temizliği, Geri Dönüşüm Kutusu boşaltma
- Telemetry (veri toplama) servisini kapatma
- Nihai Performans güç planını etkinleştirme
- Sistem Geri Yükleme noktası oluşturma/yönetme

### 🩺 Sistem Tanılama & Otomatik Sorun Giderme
Sistemi tarayıp aşağıdaki gibi yaygın sorunları tespit eder ve **tek tek ya da toplu** olarak düzeltir:
- Düşük disk alanı, aşırı geçici dosya birikimi
- Windows Update servisinin kapalı olması
- Bekleyen yeniden başlatma (pending reboot)
- Windows Defender gerçek zamanlı korumanın kapalı olması
- Windows Güvenlik Duvarı'nın devre dışı olması
- Sistem Geri Yükleme'nin kapalı olması
- Aşırı başlangıç programı yükü
- Sürücü (driver) hataları
- Kritik RAM kullanımı
- DNS çözümleme sorunları
- Uzun süredir güncelleme yapılmamış olması

Sonuçlar CSV olarak dışa aktarılabilir.

### 🔑 Lisans & Başlangıç
- `slmgr` ile Windows lisans/etkinleştirme durumunu sorgulama
- Resmi Windows etkinleştirme ayarlarına, ürün anahtarı sihirbazına ve Microsoft satın alma sayfasına hızlı erişim
- Registry başlangıç (autorun) öğelerini tarama ve kaldırma

### 📊 Disk & Rapor
- Sistem durum raporunu `.txt` olarak dışa aktarma
- C:\ sürücüsünde en büyük 15 dosyayı bulan tarayıcı

### ℹ️ Hakkında & Güncelleme
- Uygulama içi sistem bilgisi paneli (CPU, GPU, BIOS, anakart)
- GitHub üzerinden otomatik sürüm/güncelleme kontrolü
- Tüm kritik işlemlerin kaydedildiği işlem günlüğü (audit log)

> **Not:** Bu proje herhangi bir yazılım lisansı/etkinleştirme kırma (crack/activation bypass) aracı **içermez ve içermeyecektir**. Lisans sekmesi yalnızca Microsoft'un resmi araçlarına yönlendirme yapar.

---

## 📸 Ekran Görüntüleri

> _Ekran görüntülerinizi buraya ekleyin: `docs/screenshot-1.png` vb._

---

## 🚀 Hızlı Kurulum (Tek Komut)

Windows PowerShell'i açın (yönetici olması gerekmez) ve aşağıdaki komutu çalıştırın:

```powershell
irm https://raw.githubusercontent.com/mert478/optimizasyon/main/install.ps1 | iex
```

Bu betik sırasıyla:
1. Sisteminizde Python 3 olup olmadığını kontrol eder (yoksa resmi python.org sayfasına yönlendirir).
2. Gerekli Python paketini (`psutil`) kurar.
3. Uygulamanın en güncel sürümünü GitHub'dan indirir.
4. Uygulamayı başlatır ve isteğe bağlı olarak Başlat Menüsü kısayolu oluşturur.

> ⚠️ **Herhangi bir `irm | iex` komutunu çalıştırmadan önce her zaman betiğin içeriğini incelemeniz önerilir.** Betiğin tam içeriğini repo kökündeki [`install.ps1`](./install.ps1) dosyasından inceleyebilirsiniz.

---

## 🔧 Manuel Kurulum

```bash
git clone https://github.com/mert478/optimizasyon.git
cd optimizasyon
pip install -r requirements.txt
python sentinel_pro.py
```

---

## 🖱️ Kullanım

Uygulama açıldığında 6 sekme ile karşılaşırsınız. Sistem üzerinde değişiklik yapan işlemler (kayıt defteri düzenleme, servis durdurma, DNS değiştirme vb.) her zaman bir **onay penceresi** gösterir ve gerektiğinde Windows'un kendi Yönetici (UAC) izin isteğini tetikler — uygulama arka planda sessizce yetki yükseltmez.

Tüm kritik işlemler `%LOCALAPPDATA%\SentinelPro\sentinel_islem_gunlugu.txt` dosyasına kaydedilir; **ℹ️ Hakkında & Güncelleme** sekmesinden görüntülenebilir.

---

## 📦 Gereksinimler

- Windows 10 / 11 (bazı özellikler Windows'a özeldir: `winreg`, `winver`, `slmgr` vb.)
- Python 3.9 veya üzeri
- `psutil` kütüphanesi

---

## 🔒 Güvenlik Notu

Bu araç, sistem düzeyinde değişiklikler yapabilen güçlü fonksiyonlar içerir (süreç sonlandırma, kayıt defteri düzenleme, servis yönetimi, güvenlik duvarı ayarları vb.). Kaynağını doğrulamadığınız derlenmiş `.exe` sürümlerini **çalıştırmayın**; her zaman kaynak kodunu inceleyin veya bu depodan doğrudan çalıştırın.

---

## 🤝 Katkıda Bulunma

Pull request'ler ve issue'lar memnuniyetle karşılanır. Büyük değişiklikler için önce bir issue açarak neyi değiştirmek istediğinizi tartışmanızı öneririz.

---

## 📄 Lisans

Bu proje [MIT Lisansı](./LICENSE) ile lisanslanmıştır.
