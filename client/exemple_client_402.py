import os
import asyncio
import httpx
import base64
import json
from dotenv import load_dotenv
import base58
from solders.keypair import Keypair

# Импорты для x402 v2.5.0
from x402 import x402Client, parse_payment_required
from x402.mechanisms.svm.exact import ExactSvmClientScheme

# Загружаем настройки
load_dotenv()

# Используем CLIENT_PRIVATE_KEY для Solana
PRIVATE_KEY = os.getenv("CLIENT_PRIVATE_KEY")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:3333/v1/search")

async def run_client():
    if not PRIVATE_KEY:
        print("❌ ОШИБКА: Пожалуйста, установите CLIENT_PRIVATE_KEY в .env")
        return

    try:
        # Создаем Keypair из массива байт (формат в .env)
        import json
        key_data = json.loads(PRIVATE_KEY)
        keypair = Keypair.from_bytes(key_data)
        print(f"🔹 Используем Solana кошелек: {keypair.pubkey()}")
    except Exception as e:
        print(f"❌ ОШИБКА при чтении приватного ключа: {e}")
        return

    # 1. Создаем клиент x402 и регистрируем SVM (Solana) схему
    class SignerWrapper:
        def __init__(self, keypair):
            self._keypair = keypair
        @property
        def address(self) -> str:
            return str(self._keypair.pubkey())
        @property
        def keypair(self):
            return self._keypair

    client = x402Client()
    client.register("solana:*", ExactSvmClientScheme(SignerWrapper(keypair)))

    async with httpx.AsyncClient() as http_client:
        print(f"🚀 Делаем запрос к {SERVER_URL}...")
        
        # Запрос для поиска (POST)
        search_query = {"query": "best burgers", "limit": 3}
        
        # Шаг 1: Первый запрос
        response = await http_client.post(SERVER_URL, json=search_query)
        
        if response.status_code == 402:
            print("🔹 Получен ответ 402 (Payment Required). Начинаем процесс оплаты на Solana...")
            
            # Шаг 2: Извлекаем заголовок payment-required
            pr_base64 = response.headers.get("payment-required")
            if not pr_base64:
                print("❌ ОШИБКА: Заголовок 'payment-required' не найден.")
                return
            
            # Декодируем и парсим требования к платежу
            pr_data = base64.b64decode(pr_base64)
            payment_required = parse_payment_required(pr_data)
            
            # Шаг 3: Генерируем платежный payload (подпись транзакции Solana)
            print("✍️  Подписываем транзакцию Solana через x402...")
            try:
                payload = await client.create_payment_payload(payment_required)
                
                # Сериализуем payload в base64 для отправки в заголовке
                payload_json = payload.model_dump_json()
                payload_base64 = base64.b64encode(payload_json.encode()).decode()
                
                # Шаг 4: Повторяем запрос с заголовком payment-signature
                print("📤 Отправляем повторный запрос с подписью Solana...")
                headers = {"payment-signature": payload_base64}
                retry_response = await http_client.post(SERVER_URL, json=search_query, headers=headers)
                
                if retry_response.status_code == 200:
                    print("✅ УСПЕХ! Доступ получен:")
                    print(json.dumps(retry_response.json(), indent=2, ensure_ascii=False))
                else:
                    print(f"⚠️ Ошибка при повторном запросе: {retry_response.status_code}")
                    print(retry_response.text)
            except Exception as e:
                print(f"❌ ОШИБКА в процессе оплаты: {e}")
                
        elif response.status_code == 200:
            print("💡 Запрос уже оплачен или не требовал оплаты:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"⚠️ Сервер вернул код {response.status_code}: {response.text}")

if __name__ == "__main__":
    asyncio.run(run_client())
