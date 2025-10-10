# Multi-Agent Kripto Trading Sistemi: Uygulama Stratejisi ve Adım Adım Rehber

## Giriş

Bu rehber, daha önce hazırlanan teknik mimari dokümanını temel alarak, multi-agent kripto trading sisteminin Python ve CrewAI framework'ü kullanılarak nasıl geliştirileceğini adım adım açıklamaktadır. Rehber, geliştirme ortamının kurulumundan başlayarak agent'ların oluşturulması, görevlerin tanımlanması ve sistemin çalıştırılmasına kadar tüm süreci kapsamaktadır.

## Adım 1: Geliştirme Ortamının Kurulumu

İlk adım, projenin geliştirileceği ortamı hazırlamaktır. Bu, Python'un kurulumunu, sanal bir ortamın oluşturulmasını ve gerekli kütüphanelerin yüklenmesini içerir.

**1.1. Gerekli Kütüphanelerin Kurulumu:**

Aşağıdaki komutları terminalde çalıştırarak gerekli Python kütüphanelerini kurun:

```bash
# Sanal ortam oluşturma ve aktive etme
python3 -m venv venv
source venv/bin/activate

# Gerekli kütüphaneleri yükleme
pip install crewai python-dotenv langchain-openai requests beautifulsoup4 pandas numpy scikit-learn ccxt
```

- **crewai:** Multi-agent sistemini oluşturmak için ana framework.
- **python-dotenv:** API anahtarları gibi hassas bilgileri yönetmek için.
- **langchain-openai:** OpenAI'nin LLM'lerini kullanmak için.
- **requests, beautifulsoup4:** Web'den veri kazıma için.
- **pandas, numpy, scikit-learn:** Veri analizi ve makine öğrenmesi için.
- **ccxt:** Kripto para borsaları ile etkileşim için standart bir kütüphane.

**1.2. API Anahtarlarının Ayarlanması:**

Proje ana dizininde `.env` adında bir dosya oluşturun ve kullanacağınız API anahtarlarını bu dosyaya ekleyin. Örneğin, OpenAI API anahtarınız için:

```
OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## Adım 2: CrewAI ile Agent'ların Tanımlanması

Bu adımda, teknik mimaride belirtilen rollere sahip agent'ları CrewAI kullanarak tanımlayacağız. Her agent, bir rol, bir hedef (goal), bir geçmiş hikayesi (backstory) ve kullanabileceği araçlar (tools) ile tanımlanır.

**2.1. Araçların (Tools) Tanımlanması:**

Agent'ların görevlerini yerine getirebilmesi için özel araçlar oluşturabiliriz. Örneğin, piyasa verilerini almak için bir araç:

```python
from langchain.tools import tool
import ccxt

class MarketDataTools:
    @tool("Get Market Data")
    def get_market_data(symbol: str):
        """Belirtilen sembol için piyasa verilerini (OHLCV) alır."""
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=100)
        return ohlcv
```

**2.2. Agent'ların Oluşturulması:**

Araçları tanımladıktan sonra, bu araçları kullanacak agent'ları oluşturabiliriz.

```python
from crewai import Agent
from langchain_openai import ChatOpenAI

# LLM'i tanımla
llm = ChatOpenAI(model="gpt-4.1-mini")

# Teknik Analiz Agent'ı
technical_analyst = Agent(
    role='Teknik Analist',
    goal='Kripto para piyasa verilerini analiz ederek alım-satım sinyalleri üretmek.',
    backstory='Finans piyasalarında yılların deneyimine sahip bir teknik analiz uzmanı.',
    tools=[MarketDataTools.get_market_data],
    llm=llm,
    verbose=True
)

# Diğer agent'lar da benzer şekilde tanımlanır...
# fundamental_analyst, sentiment_analyst, strategy_agent, risk_manager, execution_agent
```

## Adım 3: Görevlerin (Tasks) Tanımlanması

Agent'ları tanımladıktan sonra, bu agent'ların yerine getireceği görevleri oluşturmalıyız. Her görev, bir tanım (description) ve görevi yapacak agent'ı içerir.

```python
from crewai import Task

# Veri analizi görevi
task_analyze_data = Task(
    description='BTC/USDT için piyasa verilerini topla ve teknik analiz yap.',
    expected_output='Teknik göstergelere dayalı bir alım, satım veya tutma önerisi.',
    agent=technical_analyst
)

# Diğer görevler de benzer şekilde tanımlanır...
```

## Adım 4: Crew'in Oluşturulması ve Çalıştırılması

Son adım, agent'ları ve görevleri bir araya getirerek bir "Crew" (ekip) oluşturmak ve bu ekibi çalıştırmaktır.

```python
from crewai import Crew, Process

# Crew'i oluştur
crypto_trading_crew = Crew(
    agents=[technical_analyst, ...], # Diğer agent'ları ekle
    tasks=[task_analyze_data, ...], # Diğer görevleri ekle
    process=Process.SEQUENTIAL, # Görevlerin sırayla yapılacağını belirtir
    verbose=2
)

# Crew'i çalıştır
result = crypto_trading_crew.kickoff()

print("######################")
print(result)
```

## Adım 5: Test ve İterasyon

- **Backtesting:** Geliştirdiğiniz stratejiyi geçmiş veriler üzerinde test ederek performansını ölçün.
- **Paper Trading:** Stratejinizi gerçek zamanlı piyasa verileriyle ancak sanal para ile test ederek canlı piyasa koşullarındaki performansını gözlemleyin.
- **İterasyon:** Test sonuçlarına göre agent'ların hedeflerini, araçlarını ve stratejilerini geliştirin.

Bu rehber, multi-agent kripto trading sisteminizi geliştirmeye başlamanız için temel bir çerçeve sunmaktadır. Her adımı kendi ihtiyaçlarınıza ve hedeflerinize göre özelleştirebilir ve genişletebilirsiniz.
