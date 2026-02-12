import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def get_db_config(self):
        """Retorna configuração do banco de dados"""
        return {
            'host': os.environ.get('DB_HOST', 'postgres-service'),
            'port': int(os.environ.get('DB_PORT', 5432)),
            'database': os.environ.get('DB_NAME', 'currency_db'),
            'user': os.environ.get('DB_USER', 'currency_user'),
            'password': os.environ.get('DB_PASSWORD', 'changeme')
        }
    
    def connect(self):
        """Conecta ao banco de dados PostgreSQL"""
        try:
            config = self.get_db_config()
            self.connection = psycopg2.connect(**config)
            self.connection.autocommit = False
            logger.info("Conectado ao banco de dados PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ao banco: {str(e)}")
            return False
    
    def ensure_connection(self):
        """Garante que a conexão está ativa"""
        try:
            if self.connection is None or self.connection.closed:
                return self.connect()
            # Testa a conexão
            with self.connection.cursor() as cur:
                cur.execute('SELECT 1')
            return True
        except:
            return self.connect()
    
    def save_rates(self, rates_dict, source='exchangerate-api'):
        """
        Salva taxas de câmbio no banco de dados
        
        Args:
            rates_dict: Dict com {currency_code: rate_to_brl}
            source: Fonte dos dados
        """
        if not self.ensure_connection():
            logger.error("Não foi possível conectar ao banco de dados")
            return False
        
        try:
            with self.connection.cursor() as cur:
                recorded_at = datetime.now()
                
                for currency_code, rate in rates_dict.items():
                    cur.execute("""
                        INSERT INTO exchange_rates (currency_code, rate_to_brl, recorded_at, source)
                        VALUES (%s, %s, %s, %s)
                    """, (currency_code, rate, recorded_at, source))
                
                # Registra a atualização
                cur.execute("""
                    INSERT INTO rate_updates (currencies_updated, success)
                    VALUES (%s, %s)
                """, (len(rates_dict), True))
                
                self.connection.commit()
                logger.info(f"Salvou {len(rates_dict)} taxas no banco de dados")
                return True
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Erro ao salvar taxas: {str(e)}")
            
            # Registra falha
            try:
                with self.connection.cursor() as cur:
                    cur.execute("""
                        INSERT INTO rate_updates (currencies_updated, success, error_message)
                        VALUES (%s, %s, %s)
                    """, (0, False, str(e)))
                    self.connection.commit()
            except:
                pass
            
            return False
    
    def get_latest_rates(self):
        """Retorna as taxas mais recentes de cada moeda"""
        if not self.ensure_connection():
            return {}
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT currency_code, rate_to_brl, recorded_at
                    FROM latest_rates
                    ORDER BY currency_code
                """)
                
                results = cur.fetchall()
                return {
                    row['currency_code']: {
                        'rate': float(row['rate_to_brl']),
                        'recorded_at': row['recorded_at'].isoformat()
                    }
                    for row in results
                }
        except Exception as e:
            logger.error(f"Erro ao buscar taxas mais recentes: {str(e)}")
            return {}
    
    def get_historical_rates(self, currency_code, start_date, end_date):
        """
        Retorna histórico de taxas para uma moeda em um período
        
        Args:
            currency_code: Código da moeda (ex: USD)
            start_date: Data inicial (datetime ou string YYYY-MM-DD)
            end_date: Data final (datetime ou string YYYY-MM-DD)
        """
        if not self.ensure_connection():
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id,
                        currency_code,
                        rate_to_brl,
                        recorded_at,
                        source
                    FROM exchange_rates
                    WHERE currency_code = %s
                        AND recorded_at >= %s
                        AND recorded_at <= %s
                    ORDER BY recorded_at DESC
                """, (currency_code, start_date, end_date))
                
                results = cur.fetchall()
                return [
                    {
                        'id': row['id'],
                        'currency_code': row['currency_code'],
                        'rate_to_brl': float(row['rate_to_brl']),
                        'recorded_at': row['recorded_at'].isoformat(),
                        'source': row['source']
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {str(e)}")
            return []
    
    def get_daily_stats(self, currency_code, days=30):
        """
        Retorna estatísticas diárias para uma moeda
        
        Args:
            currency_code: Código da moeda
            days: Número de dias para retornar (padrão: 30)
        """
        if not self.ensure_connection():
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        date,
                        min_rate,
                        max_rate,
                        avg_rate,
                        sample_count
                    FROM daily_rate_stats
                    WHERE currency_code = %s
                        AND date >= CURRENT_DATE - INTERVAL '%s days'
                    ORDER BY date DESC
                """, (currency_code, days))
                
                results = cur.fetchall()
                return [
                    {
                        'date': row['date'].isoformat(),
                        'min_rate': float(row['min_rate']),
                        'max_rate': float(row['max_rate']),
                        'avg_rate': float(row['avg_rate']),
                        'sample_count': row['sample_count']
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas diárias: {str(e)}")
            return []
    
    def get_rate_at_date(self, currency_code, target_date):
        """
        Retorna a taxa mais próxima de uma data específica
        
        Args:
            currency_code: Código da moeda
            target_date: Data alvo (datetime ou string YYYY-MM-DD)
        """
        if not self.ensure_connection():
            return None
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        rate_to_brl,
                        recorded_at
                    FROM exchange_rates
                    WHERE currency_code = %s
                        AND DATE(recorded_at) = DATE(%s)
                    ORDER BY recorded_at DESC
                    LIMIT 1
                """, (currency_code, target_date))
                
                result = cur.fetchone()
                if result:
                    return {
                        'rate': float(result['rate_to_brl']),
                        'recorded_at': result['recorded_at'].isoformat()
                    }
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar taxa na data: {str(e)}")
            return None
    
    def close(self):
        """Fecha a conexão com o banco de dados"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Conexão com banco de dados fechada")
