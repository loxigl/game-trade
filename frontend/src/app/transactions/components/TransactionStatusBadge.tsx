import React from 'react';
import { Badge } from 'antd';
import { TransactionStatus } from '../../types/transaction';

interface TransactionStatusBadgeProps {
  status: TransactionStatus;
}

const TransactionStatusBadge: React.FC<TransactionStatusBadgeProps> = ({ status }) => {
  let color: string;
  let text: string;

  switch (status) {
    case TransactionStatus.PENDING:
      color = 'blue';
      text = 'В ожидании';
      break;
    case TransactionStatus.ESCROW_HELD:
    case 'escrow_held':
      color = 'purple';
      text = 'В Escrow';
      break;
    case TransactionStatus.COMPLETED:
      color = 'green';
      text = 'Завершена';
      break;
    case TransactionStatus.REFUNDED:
      color = 'orange';
      text = 'Возврат';
      break;
    case TransactionStatus.DISPUTED:
    case 'disputed':
      color = 'red';
      text = 'Спор';
      break;
    case TransactionStatus.RESOLVED:
    case 'resolved':
      color = 'cyan';
      text = 'Разрешена';
      break;
    case TransactionStatus.CANCELED:
      color = 'gray';
      text = 'Отменена';
      break;
    default:
      // Если получен необработанный строковый статус
      if (typeof status === 'string') {
        if (status.includes('escrow')) {
          color = 'purple';
          text = 'В Escrow';
        } else if (status.includes('complet')) {
          color = 'green';
          text = 'Завершена';
        } else if (status.includes('pend')) {
          color = 'blue';
          text = 'В ожидании';
        } else if (status.includes('refund')) {
          color = 'orange';
          text = 'Возврат';
        } else if (status.includes('cancel')) {
          color = 'gray';
          text = 'Отменена';
        } else if (status.includes('disput')) {
          color = 'red';
          text = 'Спор';
        } else {
          color = 'default';
          text = status;
        }
      } else {
        color = 'default';
        text = 'Неизвестно';
      }
  }

  return <Badge color={color} text={text} />;
};

export default TransactionStatusBadge; 