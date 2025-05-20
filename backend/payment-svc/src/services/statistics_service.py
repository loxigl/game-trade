"""
Сервис для управления статистикой продаж и транзакций
"""

import http
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, extract, case, text, literal, String
from datetime import datetime, timedelta, date
import calendar
from dateutil.relativedelta import relativedelta
import httpx

from ..config import get_settings
from ..models.transaction import Transaction, TransactionStatus, TransactionType
from ..models.core import Sale, SaleStatus
from ..models.statistics import SellerStatistics, BuyerStatistics, ProductStatistics

settings = get_settings()


class StatisticsService:
    """
    Сервис для получения и анализа статистики по продажам и транзакциям
    """
    def __init__(self, db: Session):
        self.db = db
        
    async def get_seller_statistics(
        self,
        seller_id: int,
        period: str = "month",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Получение статистики продаж для продавца
        
        Args:
            seller_id: ID продавца
            period: Период статистики (week, month, quarter, year, all)
            start_date: Начальная дата (опционально)
            end_date: Конечная дата (опционально)
            
        Returns:
            Статистика продаж для указанного продавца
        """
        # Определяем временной диапазон
        if not end_date:
            end_date = datetime.now()
            
        if not start_date:
            if period == "week":
                start_date = end_date - timedelta(days=7)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            elif period == "quarter":
                start_date = end_date - timedelta(days=90)
            elif period == "year":
                start_date = end_date - timedelta(days=365)
            else:  # all
                start_date = end_date - timedelta(days=365 * 2)  # за 2 года
        
        # Фильтр по продавцу и временному диапазону
        date_filter = and_(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date,
            Transaction.seller_id == seller_id,
            Transaction.type == TransactionType.PURCHASE  # Только продажи
        )

        # Получаем месячные продажи
        monthly_query = (
            self.db.query(
                func.date_trunc('month', Transaction.created_at).label('month'),
                func.count().label('sales'),
                func.sum(Transaction.amount).label('revenue')
            )
            .filter(date_filter)
            .group_by(func.date_trunc('month', Transaction.created_at))
            .order_by(func.date_trunc('month', Transaction.created_at))
        )
        
        monthly_results = monthly_query.all()
        monthly_sales = [
            {
                "month": month.strftime('%B %Y'),
                "sales": int(sales),
                "revenue": float(revenue) if revenue is not None else 0.0
            }
            for month, sales, revenue in monthly_results
        ]
        
        # Если нет данных, добавим пустой месяц
        if not monthly_sales:
            monthly_sales = [{
                "month": end_date.strftime('%B %Y'),
                "sales": 0,
                "revenue": 0.0
            }]
        
        transactions = self.db.query(Transaction).filter(date_filter).all()
        listing_ids = [transaction.listing_id for transaction in transactions]
        
        # Используем эндпоинт /statistics/listings/by-ids для получения информации о нескольких листингах сразу
        game_results = []
        try:
            api_url = f"{settings.MARKETPLACE_SERVICE_URL}/statistics/listings/by-ids"
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, params={"listing_ids": listing_ids})
                if response.status_code == 200:
                    result_data = response.json()
                    if "data" in result_data:
                        listings_data = result_data["data"]
                        # Преобразуем данные в формат [(game_name, sales_count), ...]
                        game_sales = {}
                        for listing in listings_data:
                            game_name = listing.get("game_name", "Неизвестно")
                            if game_name in game_sales:
                                game_sales[game_name] += 1
                            else:
                                game_sales[game_name] = 1
                        
                        game_results = [(game, count) for game, count in game_sales.items()]
                        # Сортируем по количеству продаж (убывание)
                        game_results.sort(key=lambda x: x[1], reverse=True)
                else:
                    # Если произошла ошибка, попробуем по старому способу (получаем данные по одному)
                    api_url = f"{settings.MARKETPLACE_SERVICE_URL}/statistics/listing"
                    for listing_id in listing_ids:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(f"{api_url}/{listing_id}")
                            if response.status_code == 200:
                                listing_data = response.json()
                                if "data" in listing_data:
                                    listing_info = listing_data["data"]
                                    game_name = listing_info.get("game", "Неизвестно")
                                    # Добавляем информацию об игре в результаты
                                    found = False
                                    for i, (name, count) in enumerate(game_results):
                                        if name == game_name:
                                            # Обновляем счетчик для существующей игры
                                            game_results[i] = (name, count + 1)
                                            found = True
                                            break
                                    
                                    if not found:
                                        # Добавляем новую игру
                                        game_results.append((game_name, 1))
        except Exception as e:
            # В случае ошибки, просто логируем и продолжаем
            print(f"Ошибка при получении данных из marketplace-svc: {str(e)}")
            
            # Как запасной вариант, используем старый метод
            api_url = f"{settings.MARKETPLACE_SERVICE_URL}/listings"
            for listing_id in listing_ids:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{api_url}/{listing_id}")
                        if response.status_code == 200:
                            game_results.append(response.json())
                except Exception as inner_e:
                    print(f"Ошибка при получении данных о листинге {listing_id}: {str(inner_e)}")
        
        # Если нет данных по играм, добавим пустые данные
        if not game_results:
            game_distribution = [{
                "game": "Нет данных",
                "sales": 0,
                "percentage": 100.0
            }]
            popular_game = "Нет данных"
        else:
            total_game_sales = sum(sales for _, sales in game_results)
            
            game_distribution = [
                {
                    "game": str(game),
                    "sales": int(sales),
                    "percentage": round((int(sales) / total_game_sales) * 100, 1) if total_game_sales > 0 else 0
                }
                for game, sales in game_results
            ]
            # Определяем самую популярную игру
            popular_game = game_results[0][0] if game_results else "Нет данных"
        
        # Общая статистика
        total_query = (
            self.db.query(
                func.count().label('total_sales'),
                func.sum(Transaction.amount).label('total_revenue')
            )
            .filter(date_filter)
        )
        
        total_result = total_query.first()
        total_sales = int(total_result.total_sales) if total_result.total_sales else 0
        total_revenue = float(total_result.total_revenue) if total_result.total_revenue else 0.0
        
        # Средняя цена
        average_price = round(total_revenue / total_sales if total_sales > 0 else 0, 2)
        
        # Процент завершенных транзакций
        completion_query = (
            self.db.query(
                func.count(case((Transaction.status == TransactionStatus.COMPLETED, 1), else_=0)).label('completed'),
                func.count().label('total')
            )
            .filter(
                Transaction.seller_id == seller_id,
                Transaction.created_at >= start_date,
                Transaction.created_at <= end_date,
                Transaction.type == TransactionType.PURCHASE
            )
        )
        
        completion_result = completion_query.first()
        logger
        completed = int(completion_result.completed) if completion_result.completed else 0
        total_tx = int(completion_result.total) if completion_result.total else 0
        completion_rate = round((completed / total_tx) * 100, 1) if total_tx > 0 else 0
        
        # Процент возвратов
        return_query = (
            self.db.query(
                func.count(case((Transaction.status == TransactionStatus.REFUNDED, 1), else_=0)).label('refunded'),
                func.count().label('total')
            )
            .filter(
                Transaction.seller_id == seller_id,
                Transaction.created_at >= start_date,
                Transaction.created_at <= end_date,
                Transaction.type == TransactionType.PURCHASE
            )
        )
        
        return_result = return_query.first()
        refunded = int(return_result.refunded) if return_result.refunded else 0
        return_rate = round((refunded / total_tx) * 100, 1) if total_tx > 0 else 0
        
        # Количество ожидающих транзакций
        pending_query = (
            self.db.query(func.count())
            .filter(
                Transaction.seller_id == seller_id,
                Transaction.status == TransactionStatus.PENDING,
                Transaction.type == TransactionType.PURCHASE
            )
        )
        
        pending_transactions = pending_query.scalar() or 0
        
        return {
            "totalSales": total_sales,
            "totalRevenue": total_revenue,
            "averagePrice": average_price,
            "popularGame": popular_game,
            "completionRate": completion_rate,
            "returnRate": return_rate,
            "pendingTransactions": int(pending_transactions),
            "monthlySales": monthly_sales,
            "gameDistribution": game_distribution
        }
    
    async def get_transaction_summary(
        self,
        seller_id: int,
        group_by: str = "month",
        period: str = "month",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение сводки по транзакциям продавца с группировкой
        
        Args:
            seller_id: ID продавца
            group_by: Параметр группировки (month, game, status, type)
            period: Период статистики (week, month, quarter, year, all)
            start_date: Начальная дата (опционально)
            end_date: Конечная дата (опционально)
            
        Returns:
            Сводка по транзакциям с группировкой
        """
        # Определяем временной диапазон
        if not end_date:
            end_date = datetime.now()
            
        if not start_date:
            if period == "week":
                start_date = end_date - timedelta(days=7)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            elif period == "quarter":
                start_date = end_date - timedelta(days=90)
            elif period == "year":
                start_date = end_date - timedelta(days=365)
            else:  # all
                start_date = end_date - timedelta(days=365 * 2)  # за 2 года
        
        # Базовый фильтр по продавцу и временному диапазону
        base_filter = and_(
            Transaction.seller_id == seller_id,
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        )
        
        summary = []
        
        if group_by == "month":
            # Запрос с группировкой по месяцам
            query = (
                self.db.query(
                    func.date_trunc('month', Transaction.created_at).label('key'),
                    func.count().label('count'),
                    func.sum(Transaction.amount).label('amount')
                )
                .filter(base_filter)
                .group_by(func.date_trunc('month', Transaction.created_at))
                .order_by(func.date_trunc('month', Transaction.created_at))
            )
            
            results = query.all()
            
            # Вычисляем общую сумму для процентов
            total_amount = sum(amount for _, _, amount in results) if results else 0
            
            for key_date, count, amount in results:
                month_name = key_date.strftime('%B %Y')
                percentage = round((amount / total_amount) * 100, 1) if total_amount > 0 else 0
                
                summary.append({
                    "key": month_name,
                    "count": int(count),
                    "amount": float(amount),
                    "percentage": percentage
                })
                
        elif group_by == "game":
            # Запрос с группировкой по играм
            query = (
                self.db.query(
                    func.cast(Transaction.extra_data.op('->>')('game_name'), String).label('key'),
                    func.count().label('count'),
                    func.sum(Transaction.amount).label('amount')
                )
                .filter(base_filter)
                .filter(Transaction.extra_data.op('->>')('game_name').isnot(None))
                .group_by(func.cast(Transaction.extra_data.op('->>')('game_name'), String))
                .order_by(desc('amount'))
            )
            
            results = query.all()
            
            # Если нет данных по играм, добавляем запись "Нет данных"
            if not results:
                summary.append({
                    "key": "Нет данных",
                    "count": 0,
                    "amount": 0.0,
                    "percentage": 100.0
                })
            else:
                # Вычисляем общую сумму для процентов
                total_amount = sum(amount for _, _, amount in results) if results else 0
                
                for game_name, count, amount in results:
                    percentage = round((amount / total_amount) * 100, 1) if total_amount > 0 else 0
                    
                    summary.append({
                        "key": game_name or "Не указано",
                        "count": int(count),
                        "amount": float(amount),
                        "percentage": percentage
                    })
                    
        elif group_by == "status":
            # Запрос с группировкой по статусам
            query = (
                self.db.query(
                    Transaction.status.label('key'),
                    func.count().label('count'),
                    func.sum(Transaction.amount).label('amount')
                )
                .filter(base_filter)
                .group_by(Transaction.status)
                .order_by(desc('amount'))
            )
            
            results = query.all()
            
            # Вычисляем общую сумму для процентов
            total_amount = sum(amount for _, _, amount in results) if results else 0
            
            for status, count, amount in results:
                percentage = round((amount / total_amount) * 100, 1) if total_amount > 0 else 0
                
                summary.append({
                    "key": status.value.upper(),
                    "count": int(count),
                    "amount": float(amount),
                    "percentage": percentage
                })
                
        elif group_by == "type":
            # Запрос с группировкой по типам транзакций
            query = (
                self.db.query(
                    Transaction.type.label('key'),
                    func.count().label('count'),
                    func.sum(Transaction.amount).label('amount')
                )
                .filter(base_filter)
                .group_by(Transaction.type)
                .order_by(desc('amount'))
            )
            
            results = query.all()
            
            # Вычисляем общую сумму для процентов
            total_amount = sum(amount for _, _, amount in results) if results else 0
            
            for tx_type, count, amount in results:
                percentage = round((amount / total_amount) * 100, 1) if total_amount > 0 else 0
                
                summary.append({
                    "key": tx_type.value.upper(),
                    "count": int(count),
                    "amount": float(amount),
                    "percentage": percentage
                })
        
        # Если в результате нет данных, вернем хотя бы один элемент
        if not summary:
            return [{
                "key": "Нет данных",
                "count": 0,
                "amount": 0.0,
                "percentage": 100.0
            }]
            
        return summary

    async def get_popular_games(
        self,
        period: str = "month",
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение списка популярных игр на основе статистики продаж
        
        Args:
            period: Период статистики (week, month, quarter, year, all)
            limit: Ограничение количества возвращаемых игр
            start_date: Начальная дата (опционально)
            end_date: Конечная дата (опционально)
            
        Returns:
            Список популярных игр с информацией о продажах
        """
        try:
            # Запрашиваем информацию из marketplace-service
            api_url = f"{settings.MARKETPLACE_SERVICE_URL}/statistics/popular-games"
            
            params = {
                "period": period,
                "limit": limit
            }
            
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
                
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, params=params)
                if response.status_code == 200:
                    result_data = response.json()
                    if "data" in result_data:
                        return result_data["data"]
                    
            # Если данные не получены, возвращаем пустой результат
            return [{
                "id": 0,
                "name": "Нет данных",
                "logo_url": None,
                "sales": 0
            }]
                
        except Exception as e:
            print(f"Ошибка при получении популярных игр из marketplace-svc: {str(e)}")
            # В случае ошибки возвращаем пустой список
            return [{
                "id": 0,
                "name": "Нет данных",
                "logo_url": None,
                "sales": 0
            }]

    async def record_sale_completion(
        self,
        sale_id: int,
        seller_id: int,
        buyer_id: int
    ) -> Dict[str, Any]:
        """
        Записать информацию о завершении продажи в статистику
        
        Args:
            sale_id: ID продажи
            seller_id: ID продавца
            buyer_id: ID покупателя
            
        Returns:
            Информация о записи в статистику
        """
        # Получаем продажу
        sale = self.db.query(Sale).filter(Sale.id == sale_id).first()
        if not sale:
            raise ValueError(f"Продажа с ID {sale_id} не найдена")
        
        # Получаем транзакцию
        transaction = self.db.query(Transaction).filter(
            Transaction.id == sale.transaction_id
        ).first()
        
        if not transaction:
            raise ValueError(f"Транзакция для продажи {sale_id} не найдена")
        
        # Создаем или обновляем статистику продавца
        seller_stats = self.db.query(SellerStatistics).filter(
            SellerStatistics.seller_id == seller_id
        ).first()
        
        current_date = datetime.now()
        current_month_start = datetime(current_date.year, current_date.month, 1)
        
        if not seller_stats:
            # Создаем новую запись статистики продавца
            seller_stats = SellerStatistics(
                seller_id=seller_id,
                total_sales=1,
                total_revenue=float(transaction.amount),
                completed_sales=1,
                cancelled_sales=0,
                disputed_sales=0,
                current_month_sales=1,
                current_month_revenue=float(transaction.amount),
                average_rating=0,
                rating_count=0,
                last_sale_date=current_date
            )
            self.db.add(seller_stats)
        else:
            # Обновляем существующую статистику
            seller_stats.total_sales += 1
            seller_stats.total_revenue += float(transaction.amount)
            seller_stats.completed_sales += 1
            seller_stats.last_sale_date = current_date
            
            # Обновляем текущую месячную статистику
            if seller_stats.current_month_start and seller_stats.current_month_start.month == current_date.month:
                seller_stats.current_month_sales += 1
                seller_stats.current_month_revenue += float(transaction.amount)
            else:
                # Это новый месяц, сбрасываем месячную статистику
                seller_stats.current_month_start = current_month_start
                seller_stats.current_month_sales = 1
                seller_stats.current_month_revenue = float(transaction.amount)
        
        # Обновляем статистику покупателя
        buyer_stats = self.db.query(BuyerStatistics).filter(
            BuyerStatistics.buyer_id == buyer_id
        ).first()
        
        if not buyer_stats:
            # Создаем новую запись статистики покупателя
            buyer_stats = BuyerStatistics(
                buyer_id=buyer_id,
                total_purchases=1,
                total_spent=float(transaction.amount),
                current_month_purchases=1,
                current_month_spent=float(transaction.amount),
                last_purchase_date=current_date
            )
            self.db.add(buyer_stats)
        else:
            # Обновляем существующую статистику
            buyer_stats.total_purchases += 1
            buyer_stats.total_spent += float(transaction.amount)
            buyer_stats.last_purchase_date = current_date
            
            # Обновляем текущую месячную статистику
            if buyer_stats.current_month_start and buyer_stats.current_month_start.month == current_date.month:
                buyer_stats.current_month_purchases += 1
                buyer_stats.current_month_spent += float(transaction.amount)
            else:
                # Это новый месяц, сбрасываем месячную статистику
                buyer_stats.current_month_start = current_month_start
                buyer_stats.current_month_purchases = 1
                buyer_stats.current_month_spent = float(transaction.amount)
        
        # Сохраняем изменения
        self.db.commit()
        
        return {
            "status": "success",
            "sale_id": sale_id,
            "seller_stats_updated": True,
            "buyer_stats_updated": True
        }

def get_statistics_service(db: Session) -> StatisticsService:
    """
    Функция-провайдер для получения экземпляра StatisticsService
    """
    return StatisticsService(db) 