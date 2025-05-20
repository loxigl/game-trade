#!/bin/bash

# Выход при любой ошибке
set -e

# Переменные окружения для тестов
export TESTING=1
export SECRET_KEY="test_secret_key_for_testing_purposes_only"
export DATABASE_URL="sqlite:///./test.db"
export REDIS_URL=""
export ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES=30
export REFRESH_TOKEN_EXPIRE_DAYS=7
export EMAIL_FROM="test@example.com"
export SMTP_HOST="localhost"
export SMTP_PORT=25
export SMTP_USER=""
export SMTP_PASSWORD=""
export FRONTEND_URL="http://localhost:3000"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для запуска тестов
run_tests() {
    echo -e "${BLUE}Запуск тестов с параметрами: $@${NC}"
    python -m pytest "$@"
    local result=$?
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}Тесты успешно пройдены!${NC}"
    else
        echo -e "${RED}Тесты завершились с ошибкой!${NC}"
        exit $result
    fi
}

# Каталог для сохранения HTML-отчетов
REPORT_DIR="test-reports"
mkdir -p $REPORT_DIR

# Помощь по использованию скрипта
show_help() {
    echo "Использование: ./run_tests.sh [опции]"
    echo "Доступные опции:"
    echo "  -h, --help       Показать справку"
    echo "  -v, --verbose    Подробный вывод при выполнении тестов"
    echo "  -c, --coverage   Запустить с отчетом о покрытии кода"
    echo "  -r, --report     Создать HTML-отчет"
    echo "  -u, --unit       Запустить только модульные тесты"
    echo "  -i, --integration Запустить только интеграционные тесты"
    echo "  -a, --api        Запустить только тесты API"
    echo "  -k, --keyword    Запустить только тесты, содержащие указанное ключевое слово"
    echo "  -x, --xvs        Остановить выполнение при первой ошибке"
    echo -e "\nПримеры:"
    echo "  ./run_tests.sh -u               # Запустить только модульные тесты"
    echo "  ./run_tests.sh -c -r            # Запустить все тесты с отчетом о покрытии и HTML-отчетом"
    echo "  ./run_tests.sh -k password      # Запустить тесты, связанные с паролями"
    echo "  ./run_tests.sh -k 'auth and not slow' # Запустить быстрые тесты аутентификации"
}

# Параметры запуска по умолчанию
PYTEST_ARGS=""

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            PYTEST_ARGS="$PYTEST_ARGS -v"
            shift
            ;;
        -c|--coverage)
            PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=term --cov-report=html:$REPORT_DIR/coverage"
            shift
            ;;
        -r|--report)
            PYTEST_ARGS="$PYTEST_ARGS --html=$REPORT_DIR/report.html --self-contained-html"
            shift
            ;;
        -u|--unit)
            PYTEST_ARGS="$PYTEST_ARGS -m unit"
            shift
            ;;
        -i|--integration)
            PYTEST_ARGS="$PYTEST_ARGS -m integration"
            shift
            ;;
        -a|--api)
            PYTEST_ARGS="$PYTEST_ARGS -m api"
            shift
            ;;
        -k|--keyword)
            PYTEST_ARGS="$PYTEST_ARGS -k '$2'"
            shift 2
            ;;
        -x|--xvs)
            PYTEST_ARGS="$PYTEST_ARGS -x"
            shift
            ;;
        *)
            echo "Неизвестный параметр: $1"
            show_help
            exit 1
            ;;
    esac
done

# Запуск тестов с указанными параметрами
if [ -z "$PYTEST_ARGS" ]; then
    # Если параметры не указаны, запускаем все тесты
    run_tests
else
    run_tests $PYTEST_ARGS
fi 