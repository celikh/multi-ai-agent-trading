# RabbitMQ CLI Monitoring Guide

Web UI kullanılamadığı için, RabbitMQ'yu CLI üzerinden monitor etme rehberi.

## 🚀 Hızlı Başlangıç

```bash
# Mac-mini'ye SSH
ssh mac-mini

# Veya local'den direkt komut çalıştır
ssh mac-mini "docker exec trading_rabbitmq rabbitmqctl list_queues"
```

## 📊 Temel Monitoring Komutları

### 1. Genel Durum
```bash
# RabbitMQ durumu
docker exec trading_rabbitmq rabbitmq-diagnostics status

# Cluster durumu
docker exec trading_rabbitmq rabbitmqctl cluster_status

# Node health check
docker exec trading_rabbitmq rabbitmq-diagnostics check_running
```

### 2. Queue Monitoring
```bash
# Tüm queue'lar
docker exec trading_rabbitmq rabbitmqctl list_queues

# Detaylı queue bilgisi
docker exec trading_rabbitmq rabbitmqctl list_queues name messages consumers memory

# Belirli queue'nun durumu
docker exec trading_rabbitmq rabbitmqctl list_queues name messages | grep ticks.raw
```

### 3. Exchange Monitoring
```bash
# Tüm exchange'ler
docker exec trading_rabbitmq rabbitmqctl list_exchanges

# Detaylı exchange bilgisi
docker exec trading_rabbitmq rabbitmqctl list_exchanges name type durable auto_delete
```

### 4. Connection & Channel Monitoring
```bash
# Aktif bağlantılar
docker exec trading_rabbitmq rabbitmqctl list_connections

# Channel'lar
docker exec trading_rabbitmq rabbitmqctl list_channels

# Detaylı connection bilgisi
docker exec trading_rabbitmq rabbitmqctl list_connections name peer_host peer_port state
```

### 5. Bindings
```bash
# Queue-Exchange bindings
docker exec trading_rabbitmq rabbitmqctl list_bindings

# Belirli queue için bindings
docker exec trading_rabbitmq rabbitmqctl list_bindings | grep ticks.raw
```

### 6. Consumer Monitoring
```bash
# Tüm consumer'lar
docker exec trading_rabbitmq rabbitmqctl list_consumers

# Queue bazlı consumer sayısı
docker exec trading_rabbitmq rabbitmqctl list_queues name consumers
```

## 🔍 Trading System Spesifik Monitoring

### Agent Communication Check
```bash
# Trading queues durumu
docker exec trading_rabbitmq rabbitmqctl list_queues | grep -E 'ticks|signals|trade|execution'

# Beklenen çıktı:
# ticks.raw        X       Y
# signals.tech     X       Y
# trade.intent     X       Y
# trade.order      X       Y
# execution.report X       Y
```

### Message Flow Tracking
```bash
# Son 1 dakikadaki mesaj akışı
watch -n 5 'ssh mac-mini "docker exec trading_rabbitmq rabbitmqctl list_queues name messages"'

# Veya polling script:
while true; do
  ssh mac-mini "docker exec trading_rabbitmq rabbitmqctl list_queues name messages"
  sleep 5
done
```

### Performance Metrics
```bash
# Memory kullanımı
docker exec trading_rabbitmq rabbitmqctl status | grep -A 10 memory

# Rate istatistikleri (eğer varsa)
docker exec trading_rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

## 🛠️ Troubleshooting Komutları

### 1. Queue Problemi
```bash
# Queue sil
docker exec trading_rabbitmq rabbitmqctl delete_queue <queue_name>

# Queue purge (mesajları temizle)
docker exec trading_rabbitmq rabbitmqctl purge_queue <queue_name>

# Queue declare (yeniden oluştur)
docker exec trading_rabbitmq rabbitmqctl eval 'rabbit_amqqueue:declare({resource, <<"/">>, queue, <<"queue_name">>}, true, false, [], none, <<"user">>).'
```

### 2. Connection Problemi
```bash
# Tüm connection'ları kapat
docker exec trading_rabbitmq rabbitmqctl close_all_connections "Maintenance"

# Belirli connection'ı kapat
docker exec trading_rabbitmq rabbitmqctl close_connection "<connection_name>" "reason"
```

### 3. Dead Letter Queue Check
```bash
# DLQ'leri kontrol et
docker exec trading_rabbitmq rabbitmqctl list_queues | grep dlq

# DLQ mesajlarını say
docker exec trading_rabbitmq rabbitmqctl list_queues name messages | grep dlq
```

## 📈 Monitoring Scripts

### Queue Monitor Script
```bash
#!/bin/bash
# queue_monitor.sh

echo "=== RabbitMQ Queue Status ==="
echo "Time: $(date)"
echo ""

ssh mac-mini "docker exec trading_rabbitmq rabbitmqctl list_queues name messages consumers" | \
  awk '{printf "%-30s Messages: %-6s Consumers: %s\n", $1, $2, $3}'

echo ""
echo "=== Connection Count ==="
ssh mac-mini "docker exec trading_rabbitmq rabbitmqctl list_connections" | wc -l
```

### Alert Script
```bash
#!/bin/bash
# rabbitmq_alert.sh

THRESHOLD=1000

MESSAGES=$(ssh mac-mini "docker exec trading_rabbitmq rabbitmqctl list_queues" | \
  awk '{sum+=$2} END {print sum}')

if [ "$MESSAGES" -gt "$THRESHOLD" ]; then
  echo "⚠️ ALERT: Total messages ($MESSAGES) exceeds threshold ($THRESHOLD)"
  # Send notification
fi
```

## 🔄 Automation ile Grafana Entegrasyonu

RabbitMQ CLI çıktılarını Prometheus'a export etmek için:

### 1. Prometheus Exporter
```python
# rabbitmq_exporter.py
import subprocess
from prometheus_client import Gauge, start_http_server

queue_messages = Gauge('rabbitmq_queue_messages', 'Messages in queue', ['queue'])

def collect_metrics():
    result = subprocess.run(
        ['ssh', 'mac-mini', 'docker', 'exec', 'trading_rabbitmq',
         'rabbitmqctl', 'list_queues', 'name', 'messages'],
        capture_output=True, text=True
    )

    for line in result.stdout.strip().split('\n')[1:]:  # Skip header
        queue, messages = line.split()
        queue_messages.labels(queue=queue).set(int(messages))

if __name__ == '__main__':
    start_http_server(8001)
    while True:
        collect_metrics()
        time.sleep(10)
```

### 2. Grafana Dashboard Query
```
# Prometheus query for RabbitMQ metrics
rabbitmq_queue_messages{queue="ticks.raw"}
```

## 📱 Quick Reference Card

| İhtiyaç | Komut |
|---------|-------|
| Genel durum | `rabbitmq-diagnostics status` |
| Queue listesi | `rabbitmqctl list_queues` |
| Bağlantılar | `rabbitmqctl list_connections` |
| Consumer'lar | `rabbitmqctl list_consumers` |
| Exchange'ler | `rabbitmqctl list_exchanges` |
| Memory | `rabbitmqctl status \| grep memory` |
| Cluster | `rabbitmqctl cluster_status` |

## 🎯 Trading System Check Checklist

- [ ] Tüm queue'lar mevcut (ticks.raw, signals.tech, trade.intent, etc.)
- [ ] Her queue'da en az 1 consumer var
- [ ] Message akışı devam ediyor (messages count değişiyor)
- [ ] Connection count = 5 (her agent için 1)
- [ ] Memory kullanımı normal (<1GB)
- [ ] Dead letter queue'larda mesaj yok

## 💡 Pro Tips

1. **Alias Oluştur**:
```bash
# ~/.bashrc veya ~/.zshrc
alias rmq='ssh mac-mini "docker exec trading_rabbitmq rabbitmqctl"'

# Kullanım:
rmq list_queues
rmq list_connections
```

2. **Watch Kullan**:
```bash
watch -n 5 'ssh mac-mini "docker exec trading_rabbitmq rabbitmqctl list_queues"'
```

3. **JSON Output**:
```bash
docker exec trading_rabbitmq rabbitmqctl list_queues --formatter json
```

4. **Prometheus Metrics**:
```bash
# RabbitMQ Prometheus endpoint
curl http://192.168.1.150:15692/metrics
```

## 📞 Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| Queue mesajları birikiryor | Consumer çalışmıyor, agent'ı restart et |
| Connection yok | Agent başlatılmamış, servisleri kontrol et |
| Memory yüksek | Queue'ları purge et veya consumer ekle |
| Dead letter queue dolu | Hatalı mesajları incele ve düzelt |

---

**Son Güncelleme**: 2025-10-10
**Durum**: Web UI kullanılamıyor, CLI ile full monitoring aktif
