from src.models.wallet import Wallet, WalletStatus
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

def check_escrow():
    engine = create_engine('postgresql://postgres:postgres@localhost:5432/payments')
    session = Session(bind=engine)
    
    print('Checking for escrow wallet:')
    escrow_wallet = session.query(Wallet).filter(Wallet.user_id == 0).first()
    print(f'Escrow wallet exists: {escrow_wallet is not None}')
    
    if escrow_wallet:
        print(f'Escrow wallet ID: {escrow_wallet.id}, Status: {escrow_wallet.status}')
        print(f'Balances: {escrow_wallet.balances}')

if __name__ == '__main__':
    check_escrow() 