from src.utils import env

CONFIGS_COLL = 'configs'
CONFIGS_OLD_COLL = 'configs_old'
BASE_CHAIN_COLL = 'base_chains'
GENERICS_COLL = 'generics'


REPLICA_SET_HOSTS = [env.DB_IP + ":" + env.DB_PORT]
REPLICA_SET_NAME = 'replica-set'