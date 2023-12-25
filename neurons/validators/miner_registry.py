import os
import traceback

from sqlalchemy import create_engine, Column, String, DateTime, func, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import bittensor as bt


Base = declarative_base()


class MinerRegistry(Base):
    __tablename__ = "miner_registry"

    hot_key = Column(String, primary_key=True)
    ip_address = Column(String)
    network = Column(String)
    model_type = Column(String)
    response_time = Column(Float)
    score = Column(Float)
    run_id = Column(String)
    updated = Column(DateTime, default=datetime.datetime.utcnow)

class MinerBlockRegistry(Base):
    __tablename__ = "miner_block_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hot_key = Column(String)
    network = Column(String)
    model_type = Column(String)
    block_height = Column(Integer)
    updated = Column(DateTime, default=datetime.datetime.utcnow)

class MinerRegistryManager:
    def __init__(self):
        self.engine = create_engine("sqlite:////data/miner_registry.db")
        Base.metadata.create_all(self.engine)

    def store_miner_metadata(self, hot_key, ip_address, network, model_type, response_time, score, run_id):
        session = sessionmaker(bind=self.engine)()
        try:
            existing_miner = (
                session.query(MinerRegistry).filter_by(hot_key=hot_key).first()
            )

            if existing_miner:
                existing_miner.network = network
                existing_miner.ip_address = ip_address
                existing_miner.model_type = model_type
                existing_miner.response_time = response_time
                existing_miner.updated = datetime.datetime.utcnow()
                existing_miner.score = score
                existing_miner.run_id = run_id
            else:
                new_miner = MinerRegistry(
                    ip_address=ip_address,
                    hot_key=hot_key,
                    network=network,
                    model_type=model_type,
                    response_time=response_time,
                    score=score,
                    run_id=run_id,
                )
                session.add(new_miner)

            session.commit()
        except Exception as e:
            session.rollback()
            bt.logging.error(f"Error occurred: {traceback.format_exc()}")
        finally:
            session.close()

    def store_miner_block_height(self, hot_key, network, model_type, block_height, bitcoin_cheat_factor_sample_size):
        session = sessionmaker(bind=self.engine)()
        try:
            new_miner = MinerBlockRegistry(
                hot_key=hot_key,
                network=network,
                model_type=model_type,
                block_height=block_height
            )
            session.add(new_miner)
            session.commit()

            # Count the number of records for the given hot_key
            count = session.query(MinerBlockRegistry).filter_by(hot_key=hot_key).count()

            # If count exceeds bitcoin_cheat_factor_sample_size, delete the oldest records
            if count > bitcoin_cheat_factor_sample_size:
                # Find the oldest records to delete
                oldest_records = session.query(MinerBlockRegistry) \
                    .filter_by(hot_key=hot_key) \
                    .order_by(MinerBlockRegistry.block_height.asc()) \
                    .limit(count - bitcoin_cheat_factor_sample_size)

                for record in oldest_records:
                    session.delete(record)

                session.commit()

        except Exception as e:
            session.rollback()
            bt.logging.error(f"Error occurred: {traceback.format_exc()}")
        finally:
            session.close()

    def clear_block_heights(self, hot_key, network, model_type):
        session = sessionmaker(bind=self.engine)()
        try:
            session.query(MinerBlockRegistry).filter_by(
                hot_key=hot_key, network=network, model_type=model_type
            ).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            bt.logging.error(f"Error occurred: {traceback.format_exc()}")
        finally:
            session.close()

    def calculate_cheat_factor(self, hot_key, network, model_type, sample_size=256):
        session = sessionmaker(bind=self.engine)()
        try:
            entries = (
                session.query(MinerBlockRegistry.block_height)
                .filter(
                    MinerBlockRegistry.hot_key == hot_key,
                    MinerBlockRegistry.network == network,
                    MinerBlockRegistry.model_type == model_type
                )
                .order_by(MinerBlockRegistry.updated.desc())
                .limit(sample_size)
                .all()
            )

            if len(entries) < sample_size:
                return 0

            block_heights = [entry[0] for entry in entries]
            from collections import Counter
            counts = Counter(block_heights)
            repeats = sum(count - 1 for count in counts.values() if count > 1)
            total = len(block_heights)
            cheat_factor = repeats / total
            return cheat_factor

        except Exception as e:
            bt.logging.error(f"Error occurred: {traceback.format_exc()}")
            return 0
        finally:
            session.close()

    def get_miner_distribution(self, all_networks):
        session = sessionmaker(bind=self.engine)()
        try:
            # Initialize distribution with 1 for each network
            miner_distribution = {network: 1 for network in all_networks}

            # Query MinerRegistry, group by network, and count the number of miners in each group
            distribution_query = (
                session.query(MinerRegistry.network, func.count(MinerRegistry.network))
                .group_by(MinerRegistry.network)
                .all()
            )

            # Update the counts in miner_distribution based on the query results
            for network, count in distribution_query:
                miner_distribution[network] = max(count, 1)  # Ensures a minimum count of 1

            return miner_distribution

        except Exception as e:
            bt.logging.error(f"Error occurred: {traceback.format_exc()}")
            return {}
        finally:
            session.close()

    def detect_multiple_ip_usage(self, hot_key, period_hours=24):
        session = sessionmaker(bind=self.engine)()
        try:
            # Current time
            current_time = datetime.datetime.utcnow()

            # Time 24 hours ago (or the specified period)
            past_time = current_time - datetime.timedelta(hours=period_hours)

            # Query for repeated IP addresses (without ports) within the last 24 hours
            repeated_ips = (
                session.query(
                    MinerRegistry.ip_address.label('ip'),
                    func.count(MinerRegistry.ip_address)
                )

                .filter(
                    MinerRegistry.hot_key == hot_key,
                    MinerRegistry.updated >= past_time
                )
                .group_by('ip')
                .having(func.count('ip') > 1)
                .all()
            )

            # Print the repeated IP addresses
            for ip, count in repeated_ips:
                bt.logging.info(f"IP Address {ip} is used {count} times in the last {period_hours} hours.")

            if len(repeated_ips) == 0:
                return False
            return True

        except Exception as e:
            bt.logging.error(f"Error occurred: {traceback.format_exc()}")
            return False
        finally:
            session.close()

    def detect_multiple_run_id(self, run_id, allowed_num =8):
        session = sessionmaker(bind=self.engine)()
        try:
            repeated_run_id = (
                session.query(
                    MinerRegistry.run_id.label('run_id'),
                    func.count(MinerRegistry.run_id)
                )
                .filter(
                    MinerRegistry.run_id == run_id
                )
                .group_by('run_id')
                .having(func.count('run_id') > allowed_num)
                .all()
            )

            for run_id, count in repeated_run_id:
                bt.logging.info(f"run_id {run_id} is used {count} times. allowed_num is max {allowed_num}")

            if len(repeated_run_id) == 0:
                return False

            return True

        except Exception as e:
            bt.logging.error(f"Error occurred: {traceback.format_exc()}")
            return False
        finally:
            session.close()