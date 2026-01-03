
# Остановка предыдущих процессов
echo ""
echo "🔄 Остановка предыдущих процессов..."
pkill -f "python3 server.py" 2>/dev/null
pkill -f "python3 router.py" 2>/dev/null
sleep 1

# Запуск Backend
echo ""
echo "Запуск Backend сервера (порт 8001)..."
cd myserver
python3 server.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..
sleep 2

# Проверка запуска Backend
if ps -p $BACKEND_PID > /dev/null; then
    echo "Backend запущен (PID: $BACKEND_PID)"
else
    echo "Ошибка запуска Backend. Проверьте backend.log"
    exit 1
fi

# Запуск Frontend
echo ""
echo "Запуск Frontend сервера (порт 8000)..."
cd frontend
python3 router.py > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
sleep 1

# Проверка запуска Frontend
if ps -p $FRONTEND_PID > /dev/null; then
    echo "Frontend запущен (PID: $FRONTEND_PID)"
else
    echo "Ошибка запуска Frontend. Проверьте frontend.log"
    kill $BACKEND_PID
    exit 1
fi

echo ""
echo "=========================================="
echo " Приложение успешно запущено!"
echo "=========================================="
echo ""
echo " Frontend: http://localhost:8000"
echo " Backend API: http://localhost:8001"
echo ""
echo " Для остановки: ./stop.sh или Ctrl+C"
echo ""
echo " Логи:"
echo "   Backend: tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""

# Ожидание прерывания
trap "echo ''; echo ' Остановка серверов...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# Держим скрипт запущенным
wait
