from src.utils import env

CONFIGS_COLL = 'configs'
CONFIGS_OLD_COLL = 'configs_old'
BASE_CHAIN_COLL = 'base_chains'
GENERICS_COLL = 'generics'


REPLICA_SET_HOSTS = ["{}:{}".format(env.DB_IP, env.DB_PORT)]
REPLICA_SET_NAME = 'replica-set'
DB_USERNAME = env.DB_USERNAME
DB_PASSWORD = env.DB_PASSWORD