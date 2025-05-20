'use client';

import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Select, DatePicker, Spin, Empty, Tabs, Button, Tooltip, message } from 'antd';
import { 
  ShoppingOutlined, 
  DollarOutlined, 
  RiseOutlined, 
  BarChartOutlined,
  ClockCircleOutlined,
  RollbackOutlined,
  InfoCircleOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import { useAuth } from '../../hooks/auth';
import { Chart as ChartJS, ArcElement, Tooltip as ChartTooltip, Legend, 
  CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title } from 'chart.js';
import { Bar, Pie } from 'react-chartjs-2';
import { getSellerStatistics, getTransactionsSummary, generateTransactionsReport } from '../../api/transaction';
import { SellerStatistics as SellerStatsType, TransactionSummary } from '../../types/transaction';

// Регистрируем необходимые компоненты Chart.js
ChartJS.register(
  ArcElement, 
  ChartTooltip, 
  Legend, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  BarElement, 
  Title
);

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TabPane } = Tabs;

const SalesStatistics: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<string>('month');
  const [dateRange, setDateRange] = useState<[Date, Date] | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<SellerStatsType | null>(null);
  const [gameDistribution, setGameDistribution] = useState<TransactionSummary[]>([]);

  // Получение статистики продаж
  useEffect(() => {
    if (!user?.id) return;
    
    const fetchStatistics = async () => {
      setLoading(true);
      try {
        // Получаем основную статистику
        const statsData = await getSellerStatistics(
          user.id,
          timeRange as any,
          dateRange ? dateRange[0] : undefined,
          dateRange ? dateRange[1] : undefined
        );
        
        setStats(statsData);
        
        // Получаем распределение по играм
        const gameData = await getTransactionsSummary(
          user.id,
          'game',
          timeRange as any,
          dateRange ? dateRange[0] : undefined,
          dateRange ? dateRange[1] : undefined
        );
        
        setGameDistribution(gameData);
      } catch (error) {
        console.error('Ошибка при получении статистики:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchStatistics();
  }, [user?.id, timeRange, dateRange]);

  // Обработчик изменения временного диапазона
  const handleTimeRangeChange = (value: string) => {
    setTimeRange(value);
    setDateRange(null);
  };

  // Обработчик изменения кастомного диапазона дат
  const handleDateRangeChange = (dates: any) => {
    if (dates && dates.length === 2) {
      setDateRange([dates[0].toDate(), dates[1].toDate()]);
      setTimeRange('custom');
    } else {
      setDateRange(null);
    }
  };

  // Данные для графика продаж по месяцам
  const salesBarChartData = {
    labels: stats?.monthlySales.map(item => item.month) || [],
    datasets: [
      {
        label: 'Продажи',
        data: stats?.monthlySales.map(item => item.sales) || [],
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      }
    ]
  };
  
  const revenueLineChartData = {
    labels: stats?.monthlySales.map(item => item.month) || [],
    datasets: [
      {
        label: 'Выручка (тыс. ₽)',
        data: stats?.monthlySales.map(item => item.revenue / 1000) || [],
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 2,
        tension: 0.4
      }
    ]
  };

  // Опции для графика продаж
  const monthlySalesOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Количество продаж'
        }
      }
    },
    plugins: {
      title: {
        display: true,
        text: 'Динамика продаж'
      },
      legend: {
        position: 'bottom' as const
      }
    }
  };

  // Данные для графика распределения по играм
  const gameDistributionChartData = {
    labels: gameDistribution.map(item => item.key),
    datasets: [
      {
        label: 'Доля продаж',
        data: gameDistribution.map(item => item.percentage),
        backgroundColor: [
          'rgba(54, 162, 235, 0.7)',
          'rgba(255, 99, 132, 0.7)',
          'rgba(255, 206, 86, 0.7)',
          'rgba(75, 192, 192, 0.7)',
          'rgba(153, 102, 255, 0.7)'
        ],
        borderWidth: 1
      }
    ]
  };

  // Опции для графика распределения по играм
  const gameDistributionOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const
      },
      title: {
        display: true,
        text: 'Распределение продаж по играм'
      }
    }
  };

  // Экспорт отчета о продажах
  const exportSalesReport = async () => {
    try {
      const blob = await generateTransactionsReport(
        user?.id,
        undefined,
        dateRange ? dateRange[0] : undefined,
        dateRange ? dateRange[1] : undefined,
        'excel'
      );
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `sales-report-${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      message.success('Отчет о продажах успешно сформирован и скачан');
    } catch (error) {
      console.error('Ошибка при экспорте отчета:', error);
      message.error('Не удалось экспортировать отчет');
    }
  };

  if (loading && !stats) {
    return (
      <div className="flex justify-center items-center py-10">
        <Spin size="large" tip="Загрузка статистики..." />
      </div>
    );
  }

  if (!stats) {
    return <Empty description="Статистика недоступна" />;
  }

  return (
    <div className="sales-statistics">
      <div className="mb-6 flex flex-wrap justify-between items-center">
        <div className="text-lg font-medium mb-2 sm:mb-0 text-gray-800">
          Статистика продаж
          <Tooltip title="Статистика обновляется ежедневно">
            <InfoCircleOutlined className="ml-2 text-gray-400" />
          </Tooltip>
        </div>
        
        <div className="flex flex-wrap gap-3">
          <Select 
            defaultValue="month" 
            style={{ width: 140 }} 
            onChange={handleTimeRangeChange}
            value={timeRange}
          >
            <Option value="week">За неделю</Option>
            <Option value="month">За месяц</Option>
            <Option value="quarter">За квартал</Option>
            <Option value="year">За год</Option>
            <Option value="all">За всё время</Option>
            <Option value="custom">Свой диапазон</Option>
          </Select>
          
          {timeRange === 'custom' && (
            <RangePicker 
              onChange={handleDateRangeChange}
              allowClear
            />
          )}
          
          <Button 
            icon={<DownloadOutlined />} 
            onClick={exportSalesReport}
          >
            Экспорт
          </Button>
        </div>
      </div>
      
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="shadow-sm">
            <Statistic 
              title={<span className="text-gray-600">Всего продаж</span>}
              value={stats.totalSales}
              prefix={<ShoppingOutlined />}
              className="sales-statistic"
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card className="shadow-sm">
            <Statistic 
              title={<span className="text-gray-600">Общая выручка</span>}
              value={stats.totalRevenue}
              prefix={<DollarOutlined />}
              suffix="₽"
              className="sales-statistic"
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card className="shadow-sm">
            <Statistic 
              title={<span className="text-gray-600">Средняя цена</span>}
              value={stats.averagePrice}
              prefix={<BarChartOutlined />}
              suffix="₽"
              precision={0}
              className="sales-statistic"
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card className="shadow-sm">
            <Statistic 
              title={<span className="text-gray-600">Процент закрытия</span>}
              value={stats.completionRate}
              prefix={<RiseOutlined />}
              suffix="%"
              className="sales-statistic"
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card className="shadow-sm">
            <Statistic 
              title={<span className="text-gray-600">Незавершенные сделки</span>}
              value={stats.pendingTransactions}
              prefix={<ClockCircleOutlined />}
              className="sales-statistic"
            />
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card className="shadow-sm">
            <Statistic 
              title={<span className="text-gray-600">Процент возвратов</span>}
              value={stats.returnRate}
              prefix={<RollbackOutlined />}
              suffix="%"
              precision={1}
              valueStyle={{ color: stats.returnRate > 5 ? '#cf1322' : 'inherit' }}
              className="sales-statistic"
            />
          </Card>
        </Col>
      </Row>
      
      <Tabs activeKey={activeTab} onChange={setActiveTab} className="mt-6">
        <TabPane tab="Обзор" key="overview">
          <Card className="mt-4 shadow-sm">
            <h3 className="text-lg font-medium mb-4 text-gray-800">Динамика продаж</h3>
            <div style={{ height: '300px' }}>
              <Bar 
                data={salesBarChartData} 
                options={monthlySalesOptions}
              />
            </div>
          </Card>
        </TabPane>
        
        <TabPane tab="По играм" key="games">
          <Card className="mt-4 shadow-sm">
            <h3 className="text-lg font-medium mb-4 text-gray-800">Распределение продаж по играм</h3>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <div style={{ height: '300px' }}>
                  <Pie 
                    data={gameDistributionChartData} 
                    options={gameDistributionOptions}
                  />
                </div>
              </Col>
              <Col xs={24} md={12}>
                <div className="mt-4 md:mt-0">
                  <h4 className="font-medium mb-2">Популярные игры</h4>
                  <ul className="space-y-2">
                    {gameDistribution.map((item, index) => (
                      <li key={index} className="flex justify-between items-center">
                        <span>{item.key}</span>
                        <span className="font-medium">{item.count} ({item.percentage}%)</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </Col>
            </Row>
          </Card>
        </TabPane>
        
        <TabPane tab="Подробный анализ" key="detailed">
          <Card className="mt-4 shadow-sm">
            <h3 className="text-lg font-medium mb-4 text-gray-800">Детальная аналитика</h3>
            <p className="text-gray-500 mb-4">
              Здесь будет расширенная аналитика с возможностью углубленного анализа продаж,
              включая сезонные тренды, сравнение с предыдущими периодами, предпочтения покупателей и т.д.
            </p>
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <div className="p-4 bg-gray-50 rounded text-center">
                  <BarChartOutlined style={{ fontSize: '32px', color: '#8c8c8c' }} />
                  <p className="mt-2 text-gray-500">Расширенная аналитика будет доступна в следующем обновлении</p>
                </div>
              </Col>
            </Row>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default SalesStatistics; 