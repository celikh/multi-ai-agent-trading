# Multi-Agent Kripto Trading Sistemi Araştırması

## 1. Multi-Agent Trading Sistemi Temel Yapısı

Medium makalesinden elde edilen bilgilere göre, multi-agent trading sistemi 5 ana agent'tan oluşur:

### Agent Türleri ve Görevleri:

1. **Market Selection Agent (Pazar Seçim Agent'ı)**
   - Makroekonomik faktörleri analiz eder
   - Piyasa duyarlılığını değerlendirir
   - En uygun piyasayı seçer (kripto, hisse senedi, altın veya hiçbiri)
   - Enflasyon oranı, faiz oranları, işsizlik oranı, GDP büyümesi gibi verileri kullanır

2. **Asset Prediction Agent (Varlık Tahmin Agent'ı)**
   - Seçilen piyasadaki en umut verici varlıkları belirler
   - Tahmine dayalı analiz ve geçmiş verileri kullanır
   - Kısa vadeli kazanç olasılığı, volatilite ve haber etkisi skorunu değerlendirir

3. **Entry Timing Agent (Giriş Zamanlaması Agent'ı)**
   - Piyasaya giriş için optimal zamanı belirler
   - Teknik analiz ve fiyat kalıplarını kullanır
   - RSI göstergesi ve destek seviyelerini analiz eder

4. **Monitoring Agent (İzleme Agent'ı)**
   - Seçilen varlığın performansını sürekli izler
   - Fiyat değişikliklerini, piyasa haberlerini ve teknik göstergeleri takip eder
   - Gerçek zamanlı veri akışı sağlar

5. **Decision Agent (Karar Agent'ı)**
   - Al, tut veya sat kararlarını verir
   - Varlığın performansına ve önceden tanımlanmış kurallara dayalı kararlar alır
   - Risk yönetimi stratejilerini uygular

## 2. Teknik Uygulama Detayları

### Market Selection Agent Örnek Kodu:
- Enflasyon < %2, faiz < %1.5, duyarlılık > 0.6, GDP büyümesi > %2 ise → Hisse senedi
- Duyarlılık > 0.7, volatilite < 20 ise → Kripto
- Enflasyon > %3 veya volatilite > 30 ise → Altın
- Diğer durumlar → Piyasa dışı

### Asset Prediction Agent Mantığı:
- Varlıkları şu formüle göre sıralar: (Kısa Vadeli Kazanç Olasılığı × Haber Etkisi Skoru) / Volatilite
- En yüksek skora sahip varlığı seçer

### Entry Timing Agent Kriterleri:
- RSI < 30 (aşırı satım bölgesi)
- Fiyat destek seviyesinin %5 üzerinde

### Decision Agent Stratejisi:
- %5 kazanç varsa → Sat
- %5 kayıp varsa → Tut
- Diğer durumlar → Daha fazla al

## 3. Kullanılan API'ler ve Teknolojiler
- Coinbase API (gerçek zamanlı fiyat verileri)
- C# programlama dili
- JSON veri işleme
- HTTP client entegrasyonu


## 4. LLM Tabanlı Multi-Agent Kripto Portföy Yönetimi (Arxiv Makalesi)

### Sistem Özeti:
Bu akademik çalışma, kripto para yatırımı için açıklanabilir, çok modlu, çok agent'lı bir framework önermektedir. Sistem, piyasa değeri en yüksek 30 kripto para için yatırım kararları almaktadır.

### Temel Zorluklar:
- Kripto paraların geleneksel varlıklara kıyasla daha kısa geçmişe sahip olması
- Çeşitli modalitelerden gelen büyük miktardaki veriyi entegre etme ihtiyacı
- Karmaşık muhakeme gereksinimleri
- LLM'lerin kripto para alanında sınırlı domain bilgisi

### Framework Bileşenleri:

#### Expert Training Modülü:
- Agent'ları çok modlu geçmiş veriler kullanarak fine-tune eder
- Profesyonel yatırım literatürünü kullanır
- Domain-spesifik bilgi kazandırır

#### Multi-Agent Investment Modülü:
- Gerçek zamanlı veri kullanarak bilinçli kripto para yatırım kararları alır
- Specialized agent'lar arasında işbirliği sağlar
- Veri analizi, literatür entegrasyonu ve yatırım karar verme süreçlerini yönetir

### İşbirliği Mekanizmaları:

#### Intra-team Collaboration (Takım İçi İşbirliği):
- Agent takımları içindeki güven seviyelerine göre nihai tahminleri ayarlar
- Tahmin doğruluğunu artırır

#### Inter-team Collaboration (Takımlar Arası İşbirliği):
- Takımlar arasında bilgi paylaşımını kolaylaştırır
- Kapsamlı analiz sağlar

### Performans Sonuçları:
- Kasım 2023 - Eylül 2024 verileri kullanılarak test edildi
- Tek agent modellerini ve piyasa benchmark'larını geçti
- Sınıflandırma, varlık fiyatlama, portföy ve açıklanabilirlik performansında üstün sonuçlar

### Teknik Özellikler:
- Multi-modal veri işleme (metin, sayısal veriler, görüntüler)
- Açıklanabilir AI yaklaşımı
- Gerçek zamanlı karar verme
- Top 30 kripto para odaklı portföy yönetimi

## 5. TradingAgents Framework

### Sistem Mimarisi:
TradingAgents, profesyonel bir ticaret firmasını simüle eden multi-agent framework'üdür. Sistem beş ana bileşenden oluşur:

**I. Analysts Team (Analist Takımı):** Dört analist eş zamanlı olarak ilgili piyasa bilgilerini toplar
**II. Research Team (Araştırma Takımı):** Toplanan verileri tartışır ve değerlendirir
**III. Trader (Tüccar):** Araştırmacıların analizine dayalı ticaret kararı verir
**IV. Risk Management Team (Risk Yönetim Takımı):** Kararı mevcut piyasa koşullarına karşı değerlendirerek riskleri azaltır
**V. Fund Manager (Fon Yöneticisi):** Ticareti onaylar ve yürütür

### Rol Uzmanlaşması:

#### Analyst Team (Analist Takımı):
- **Fundamental Analysts:** Şirket temellerini değerlendirerek düşük/yüksek değerli hisse senetlerini belirler
- **Sentiment Analysts:** Sosyal medya ve kamuoyu duyarlılığını analiz ederek piyasa ruh halini ölçer
- **News Analysts:** Haberleri ve makroekonomik göstergeleri değerlendirerek piyasa hareketlerini tahmin eder
- **Technical Analysts:** Teknik göstergeleri kullanarak fiyat trendlerini ve ticaret fırsatlarını öngörür

#### Research Team (Araştırma Takımı):
- **Bullish Researchers:** Pozitif piyasa göstergelerini ve büyüme potansiyelini vurgular
- **Bearish Researchers:** Risklere ve negatif piyasa sinyallerine odaklanır
- Diyalektik süreç ile dengeli analiz sağlar

#### Trader Agents (Tüccar Agent'ları):
- Analist ve araştırmacı önerilerini değerlendirir
- Ticaret zamanlaması ve boyutunu belirler
- Alım/satım emirlerini yürütür
- Portföyleri piyasa değişikliklerine göre ayarlar

#### Risk Management Team (Risk Yönetim Takımı):
- Piyasa volatilitesi ve likiditeyi değerlendirir
- Risk azaltma stratejileri uygular
- Tüccar Agent'larına risk maruziyeti konusunda tavsiyelerde bulunur
- Portföyü risk toleransıyla uyumlu hale getirir

### İletişim Protokolü:
- Yapılandırılmış raporlar ve diyagramlar kullanır
- Doğal dil diyalogu belirli etkileşimler için ayrılmıştır
- Bilgi kaybını minimize eder ve bağlamı korur

### Performans Sonuçları:
- AAPL, GOOGL ve AMZN üzerinde test edildi
- Tüm baseline stratejileri geçti
- Yüksek Sharpe Ratio ile risk-ayarlı getiri sağladı
- Düşük maksimum drawdown ile riski kontrol etti
- Şeffaf karar verme süreci ile açıklanabilirlik sağladı

## 6. Mevcut Multi-Agent Framework'leri

### En Popüler 5 Multi-Agent Framework:

#### 1. Agno (Eski adı Phidata)
**Özellikler:**
- Python tabanlı framework
- Büyük dil modellerini agent'lara dönüştürme
- OpenAI, Anthropic, Cohere, Ollama, Together AI desteği
- Veritabanı ve vektör depo desteği (Postgres, PgVector, Pinecone, LanceDb)
- Function calling, yapılandırılmış çıktı ve fine-tuning desteği
- Hazır agent UI'ı
- Yerel ve bulut deployment seçenekleri
- GitHub ve AWS entegrasyonu
- Ücretsiz, Pro ve Enterprise fiyatlandırma

#### 2. OpenAI Swarm
**Özellikler:**
- OpenAI tarafından geliştirilen experimental framework
- Hafif ve basit multi-agent koordinasyonu
- Agent'lar arası handoff mekanizması
- Minimal kod ile agent oluşturma

#### 3. CrewAI
**Özellikler:**
- Rol tabanlı agent oluşturma
- Yüksek seviye soyutlama
- İşbirlikçi AI agent takımları
- Karmaşık görevleri otomatik olarak gerçekleştirme
- Ölçeklenebilir yapı

#### 4. LangGraph
**Özellikler:**
- LangChain ekosisteminin parçası
- Graph tabanlı multi-agent workflow'ları
- Daha düşük seviye kontrol
- Karmaşık agent etkileşimleri için uygun
- State management ve memory desteği

#### 5. Microsoft Agent Framework
**Özellikler:**
- .NET ve Python desteği
- Açık kaynak geliştirme kiti
- Enterprise odaklı çözümler
- Microsoft ekosistemi entegrasyonu

### Framework Seçim Kriterleri:
- **Basitlik vs Kontrol:** CrewAI daha basit, LangGraph daha fazla kontrol sağlar
- **Ekosistem:** LangGraph LangChain ile entegre, Agno bağımsız
- **Deployment:** Agno hazır UI ve deployment araçları sunar
- **Maliyet:** Çoğu açık kaynak, enterprise özellikler ücretli

## 7. Kripto Exchange API'leri ve Mevcut Çözümler

### Major Exchange API'leri:

#### Binance API
**Özellikler:**
- En geniş varlık kapsamı
- Gelişmiş trading özellikleri (futures, options)
- Yüksek performans ve düşük latency
- REST ve WebSocket API desteği
- Spot, futures ve margin trading
- Yüksek frekanslı trading desteği
- Kapsamlı dokümantasyon

#### Coinbase API
**Özellikler:**
- Kullanıcı dostu ve güvenli
- Kurumsal müşteriler için özel çözümler
- Advanced Trade API
- Sandbox ortamı test için
- OAuth2 authentication
- Fiat para desteği
- ABD düzenlemelerine uygun

#### Kraken API
**Özellikler:**
- Yüksek güvenlik standartları
- Algoritmic ve high-frequency trading desteği
- Kurumsal API çözümleri
- Futures trading API
- WebSocket feeds
- Gelişmiş order türleri
- Avrupa merkezli

### Mevcut Trading Bot Platformları:

#### Ticari Platformlar:
- **Cryptohopper:** AI özellikleri, strateji marketplace
- **3Commas:** DCA botları, grid trading
- **Pionex:** Built-in trading botları
- **TradeSanta:** Bulut tabanlı botlar
- **Bitsgap:** Portfolio tracker ile entegre

#### Açık Kaynak Çözümler:
- **Gekko:** Node.js tabanlı
- **Freqtrade:** Python tabanlı
- **Zenbot:** Genetik algoritma desteği
- **Catalyst:** Quantitative analysis

### API Entegrasyon Gereksinimleri:

#### Temel Özellikler:
- Real-time market data
- Order placement ve management
- Account balance tracking
- Historical data access
- WebSocket connections
- Rate limiting handling

#### Güvenlik Gereksinimleri:
- API key management
- IP whitelisting
- Signature authentication
- SSL/TLS encryption
- Two-factor authentication

#### Performans Gereksinimleri:
- Low latency connections
- Rate limit optimization
- Error handling ve retry logic
- Connection pooling
- Async/await patterns
