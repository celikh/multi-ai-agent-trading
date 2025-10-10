# 🐰 RabbitMQ Erişim Bilgileri

## 🌐 Web Management Console

### Erişim URL'si
```
http://192.168.1.150:15672
veya
http://mac-mini:15672
```

## 🔐 Giriş Bilgileri

### Yöntem 1: Trading Kullanıcısı (Önerilen)
```
Username: trading
Password: trading123
```

### Yöntem 2: Guest Kullanıcısı (Alternatif)
```
Username: guest
Password: guest
```

## ✅ Kullanıcı Yetkileri

Her iki kullanıcı da **administrator** yetkilerine sahiptir:
- ✅ Tam erişim (configure, write, read)
- ✅ Queue oluşturma/silme
- ✅ Exchange yönetimi
- ✅ Kullanıcı yönetimi
- ✅ Virtual host yönetimi
- ✅ Policy yönetimi

## 📊 Ne Göreceksiniz?

### Ana Sayfa (Overview)
- Toplam bağlantı sayısı
- Queue sayısı ve durumu
- Message rate grafikleri
- Node bilgileri

### Queues Sekmesi
```
Trading System Queue'ları:

market.data           - Market verileri
technical.signals     - Technical analysis sinyalleri
strategy.decisions    - Strategy agent kararları
risk.assessments      - Risk değerlendirmeleri
execution.orders      - Execution emirleri
```

### Exchanges Sekmesi
```
amq.direct           - Direct exchange
amq.fanout           - Fanout exchange
amq.topic            - Topic exchange
amq.headers          - Headers exchange
```

### Connections Sekmesi
- Aktif agent bağlantıları
- Bağlantı detayları
- Channel bilgileri

## 🔧 Kullanışlı Özellikler

### Queue İzleme
1. **Queues** sekmesine gidin
2. İzlemek istediğiniz queue'ya tıklayın
3. "Get messages" ile mesajları görüntüleyin

### Message Gönderme (Test)
1. **Queues** sekmesinde queue seçin
2. "Publish message" bölümüne gidin
3. Payload yazın ve "Publish message" tıklayın

### Monitoring
1. **Overview** sekmesinde grafikleri izleyin
2. Message rates, Publish/Deliver rates
3. Queue depths ve Consumer counts

## 🚨 Sorun Giderme

### Giriş Yapamıyorum
```bash
# Şifreyi sıfırla
ssh mac-mini
docker exec trading_rabbitmq rabbitmqctl change_password trading trading123

# Yetkileri kontrol et
docker exec trading_rabbitmq rabbitmqctl list_users
docker exec trading_rabbitmq rabbitmqctl list_permissions -p /
```

### Port Erişemiyor
```bash
# RabbitMQ durumunu kontrol et
docker ps | grep rabbitmq

# Port mapping kontrol et
docker port trading_rabbitmq

# Beklenen çıktı:
# 15672/tcp -> 0.0.0.0:15672
# 5672/tcp -> 0.0.0.0:5672
```

### Management Plugin Aktif Değil
```bash
# Plugin'leri listele
docker exec trading_rabbitmq rabbitmq-plugins list

# Management plugin'i aktifleştir
docker exec trading_rabbitmq rabbitmq-plugins enable rabbitmq_management

# RabbitMQ'yu yeniden başlat
docker-compose -f docker-compose.production.yml restart trading_rabbitmq
```

## 📱 API Erişimi

### REST API Endpoint
```
http://192.168.1.150:15672/api
```

### Temel Auth
```bash
# Örnek: Queue'ları listele
curl -u trading:trading123 http://192.168.1.150:15672/api/queues

# Örnek: Specific queue bilgisi
curl -u trading:trading123 http://192.168.1.150:15672/api/queues/%2F/market.data
```

### Python ile Erişim
```python
import requests
from requests.auth import HTTPBasicAuth

url = "http://192.168.1.150:15672/api/queues"
auth = HTTPBasicAuth('trading', 'trading123')

response = requests.get(url, auth=auth)
queues = response.json()

for queue in queues:
    print(f"Queue: {queue['name']}, Messages: {queue['messages']}")
```

## 🔒 Güvenlik Notları

### Mevcut Konfigürasyon
⚠️ **Development/Test ortamı için yapılandırılmıştır**

Production için:
1. Güçlü şifreler kullanın
2. SSL/TLS aktifleştirin
3. Firewall kuralları ayarlayın
4. Guest kullanıcısını devre dışı bırakın
5. VPN üzerinden erişim zorunlu tutun

### Şifre Değiştirme
```bash
# Trading kullanıcısı şifresi
ssh mac-mini
docker exec trading_rabbitmq rabbitmqctl change_password trading YeniGüçlüŞifre123!

# Guest kullanıcısını devre dışı bırak (production için)
docker exec trading_rabbitmq rabbitmqctl delete_user guest
```

## 📊 Agent Bağlantılarını İzleme

### Connections Sekmesi
Agent'lar çalıştığında göreceğiniz bağlantılar:
```
- technical_analysis_agent (1 connection, N channels)
- strategy_agent (1 connection, N channels)
- risk_manager_agent (1 connection, N channels)
- execution_agent (1 connection, N channels)
```

### Normal Queue Depth'leri
```
market.data:          0-100 messages (hızlı işlenir)
technical.signals:    0-50 messages
strategy.decisions:   0-20 messages
risk.assessments:     0-10 messages
execution.orders:     0-5 messages (anında işlenir)
```

### Alarm Durumları
⚠️ Dikkat edilecekler:
- Queue depth > 1000: Tüketici yavaş veya durmuş
- No consumers: Agent çalışmıyor
- High message rate but no delivery: Bağlantı sorunu

## 🎯 Özet

### ✅ Başarıyla Yapılandırıldı
- [x] RabbitMQ management console aktif
- [x] Port 15672 erişilebilir
- [x] Trading kullanıcısı: **trading / trading123**
- [x] Guest kullanıcısı: **guest / guest**
- [x] Her iki kullanıcı administrator yetkisine sahip
- [x] Tüm izinler verildi (configure, write, read)

### 🌐 Erişim
```
URL:      http://192.168.1.150:15672
Login 1:  trading / trading123 ✅
Login 2:  guest / guest ✅
```

### 📱 İlk Giriş
1. Tarayıcıda http://192.168.1.150:15672 açın
2. Username: **trading**, Password: **trading123**
3. Overview sekmesinde sistem durumunu görün
4. Queues sekmesinde queue'ları izleyin

**Artık giriş yapabilirsiniz!** 🎉

---

*RabbitMQ Version: 3.13.7*
*Management Plugin: ✅ Enabled*
*Access: http://192.168.1.150:15672*
