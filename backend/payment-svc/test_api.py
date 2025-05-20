import requests
import json

def test_initiate_payment():
    """
    Тестирование инициирования платежа с переводом на эскроу
    """
    api_url = "http://localhost:8002"
    token = input("Введите токен авторизации: ")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Параметры для тестирования
    sale_id = int(input("Введите ID продажи: "))
    wallet_id = int(input("Введите ID кошелька: "))
    
    # Запрос на инициирование платежа
    payment_url = f"{api_url}/sales/{sale_id}/initiate-payment?wallet_id={wallet_id}"
    
    try:
        response = requests.post(payment_url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2))
            
            # Проверяем, есть ли эскроу информация
            if "transaction" in result.get("data", {}) and "extra_data" in result["data"]["transaction"]:
                extra_data = result["data"]["transaction"]["extra_data"]
                if extra_data and "escrow_funded" in extra_data:
                    print(f"\nЭскроу-информация:")
                    print(f"Эскроу создан: {extra_data.get('escrow_funded')}")
                    print(f"Время создания: {extra_data.get('escrow_funded_at')}")
                    print(f"ID эскроу-кошелька: {extra_data.get('escrow_wallet_id')}")
                else:
                    print("\nИнформация об эскроу отсутствует в ответе")
        else:
            print(f"Ошибка: {response.text}")
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    test_initiate_payment() 