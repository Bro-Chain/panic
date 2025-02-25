import json
import logging
import unittest
from datetime import timedelta, datetime
from unittest import mock

import pika
from freezegun import freeze_time
from parameterized import parameterized
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from src.data_store.mongo import MongoApi
from src.data_store.redis import RedisApi, Keys
from src.data_store.stores.network.cosmos import CosmosNetworkStore
from src.message_broker.rabbitmq import RabbitMQApi
from src.utils import env
from src.utils.constants.cosmos import (PROPOSAL_STATUS_PASSED,
                                        PROPOSAL_STATUS_REJECTED)
from src.utils.constants.mongo import REPLICA_SET_HOSTS, REPLICA_SET_NAME, DB_USERNAME, DB_PASSWORD
from src.utils.constants.rabbitmq import (
    HEARTBEAT_OUTPUT_WORKER_ROUTING_KEY,
    COSMOS_NETWORK_TRANSFORMED_DATA_ROUTING_KEY, HEALTH_CHECK_EXCHANGE,
    STORE_EXCHANGE, COSMOS_NETWORK_STORE_INPUT_QUEUE_NAME)
from src.utils.exceptions import PANICException, MessageWasNotDeliveredException
from src.utils.types import convert_to_float
from test.test_utils.utils import (connect_to_rabbit, delete_queue_if_exists,
                                   delete_exchange_if_exists,
                                   disconnect_from_rabbit)


class TestCosmosNetworkStore(unittest.TestCase):
    def setUp(self) -> None:
        # Dummy objects
        self.dummy_logger = logging.getLogger('Dummy')
        self.dummy_logger.disabled = True
        self.connection_check_time_interval = timedelta(seconds=0)

        # Rabbit instance
        self.rabbit_ip = env.RABBIT_IP
        self.rabbitmq = RabbitMQApi(
            self.dummy_logger, self.rabbit_ip,
            connection_check_time_interval=self.connection_check_time_interval)

        # Redis instance
        self.redis_db = env.REDIS_DB
        self.redis_host = env.REDIS_IP
        self.redis_port = env.REDIS_PORT
        self.redis_namespace = env.UNIQUE_ALERTER_IDENTIFIER
        self.redis = RedisApi(self.dummy_logger, self.redis_db,
                              self.redis_host, self.redis_port, '',
                              self.redis_namespace,
                              self.connection_check_time_interval)

        # Mongo instance
        self.mongo_db = env.DB_NAME
        self.mongo_port = env.DB_PORT
        self.mongo = MongoApi(logger=self.dummy_logger.getChild(
            MongoApi.__name__),
            db_name=self.mongo_db, host=REPLICA_SET_HOSTS,
            username=DB_USERNAME, password=DB_PASSWORD,
            replicaSet=REPLICA_SET_NAME)

        # Test store object
        self.test_store_name = 'store name'
        self.test_store = CosmosNetworkStore(self.test_store_name,
                                             self.dummy_logger, self.rabbitmq)

        # Dummy data
        self.heartbeat_routing_key = HEARTBEAT_OUTPUT_WORKER_ROUTING_KEY
        self.input_routing_key = COSMOS_NETWORK_TRANSFORMED_DATA_ROUTING_KEY
        self.test_queue_name = 'test queue'
        self.test_data_str = 'test data'
        self.test_exception = PANICException('test_exception', 1)
        self.parent_id = 'test_parent_id'
        self.chain_name = 'test_chain'

        # Some metrics

        self.test_proposal_id_1 = 1
        self.test_proposal_title_1 = 'test_proposal_1'
        self.test_proposal_description_1 = 'description_1'
        self.test_proposal_status_1 = PROPOSAL_STATUS_PASSED
        self.test_proposal_final_tally_result_1 = {
            'yes': 100.0,
            'abstain': 60.0,
            'no': 20.0,
            'no_with_veto': 10.0,
        }
        self.test_proposal_submit_time_1 = datetime(2012, 1, 1).timestamp()
        self.test_proposal_deposit_end_time_1 = datetime(2012, 1, 1).timestamp()
        self.test_proposal_total_deposit_1 = [
            {
                'denom': 'btc',
                'amount': 100.0
            }
        ]
        self.test_proposal_voting_start_time_1 = \
            datetime(2012, 1, 1).timestamp()
        self.test_proposal_voting_end_time_1 = datetime(2012, 1, 1).timestamp()
        self.test_proposal_1 = {
            'proposal_id': self.test_proposal_id_1,
            'title': self.test_proposal_title_1,
            'description': self.test_proposal_description_1,
            'status': self.test_proposal_status_1,
            'final_tally_result': self.test_proposal_final_tally_result_1,
            'submit_time': self.test_proposal_submit_time_1,
            'deposit_end_time': self.test_proposal_deposit_end_time_1,
            'total_deposit': self.test_proposal_total_deposit_1,
            'voting_start_time': self.test_proposal_voting_start_time_1,
            'voting_end_time': self.test_proposal_voting_end_time_1,
        }
        self.test_proposal_id_2 = 2
        self.test_proposal_title_2 = 'test_proposal_2'
        self.test_proposal_description_2 = 'description_2'
        self.test_proposal_status_2 = PROPOSAL_STATUS_REJECTED
        self.test_proposal_final_tally_result_2 = {
            'yes': 200.0,
            'abstain': 120.0,
            'no': 40.0,
            'no_with_veto': 20.0,
        }
        self.test_proposal_submit_time_2 = datetime(2012, 1, 1).timestamp()
        self.test_proposal_deposit_end_time_2 = datetime(2012, 1, 1).timestamp()
        self.test_proposal_total_deposit_2 = [
            {
                'denom': 'atom',
                'amount': 100.0
            },
            {
                'denom': 'link',
                'amount': 20.0
            }
        ]
        self.test_proposal_voting_start_time_2 = \
            datetime(2012, 1, 1).timestamp()
        self.test_proposal_voting_end_time_2 = datetime(2012, 1, 1).timestamp()
        self.test_proposal_2 = {
            'proposal_id': self.test_proposal_id_2,
            'title': self.test_proposal_title_2,
            'description': self.test_proposal_description_2,
            'status': self.test_proposal_status_2,
            'final_tally_result': self.test_proposal_final_tally_result_2,
            'submit_time': self.test_proposal_submit_time_2,
            'deposit_end_time': self.test_proposal_deposit_end_time_2,
            'total_deposit': self.test_proposal_total_deposit_2,
            'voting_start_time': self.test_proposal_voting_start_time_2,
            'voting_end_time': self.test_proposal_voting_end_time_2,
        }

        self.test_proposals = [
            self.test_proposal_1,
            self.test_proposal_2,
        ]
        self.test_last_monitored_cosmos_rest = datetime(2012, 1, 1).timestamp()

        self.network_data_optionals_enabled = {
            "cosmos_rest": {
                "result": {
                    "meta_data": {
                        "parent_id": self.parent_id,
                        "chain_name": self.chain_name,
                        "last_monitored": self.test_last_monitored_cosmos_rest,
                    },
                    "data": {
                        "proposals": self.test_proposals,
                    }
                }
            },
        }

        self.network_data_error = {
            "cosmos_rest": {
                "error": {
                    "meta_data": {
                        "parent_id": self.parent_id,
                        "chain_name": self.chain_name,
                        "last_monitored": self.test_last_monitored_cosmos_rest,
                    },
                    'message': self.test_exception.message,
                    'code': self.test_exception.code,
                }
            },
        }

    def tearDown(self) -> None:
        connect_to_rabbit(self.rabbitmq)
        delete_queue_if_exists(self.rabbitmq,
                               COSMOS_NETWORK_STORE_INPUT_QUEUE_NAME)
        delete_queue_if_exists(self.rabbitmq, self.test_queue_name)
        delete_exchange_if_exists(self.rabbitmq, STORE_EXCHANGE)
        delete_exchange_if_exists(self.rabbitmq, HEALTH_CHECK_EXCHANGE)
        disconnect_from_rabbit(self.rabbitmq)

        self.redis.delete_all_unsafe()
        self.mongo.drop_collection(self.parent_id)
        self.redis = None
        self.rabbitmq = None
        self.mongo = None
        self.dummy_logger = None
        self.connection_check_time_interval = None
        self.test_store._mongo = None
        self.test_store._redis = None
        self.test_store = None
        self.network_data_optionals_enabled = None

    def test__str__returns_name_correctly(self) -> None:
        self.assertEqual(self.test_store_name, str(self.test_store))

    def test_name_returns_store_name(self) -> None:
        self.assertEqual(self.test_store_name, self.test_store.name)

    def test_mongo_db_returns_mongo_db(self) -> None:
        self.assertEqual(self.mongo_db, self.test_store.mongo_db)

    def test_mongo_port_returns_mongo_port(self) -> None:
        self.assertEqual(self.mongo_port, self.test_store.mongo_port)

    def test_redis_returns_redis_instance(self) -> None:
        # Need to re-set redis object due to initialisation in the constructor
        self.test_store._redis = self.redis
        self.assertEqual(self.redis, self.test_store.redis)

    def test_mongo_returns_mongo_instance(self) -> None:
        # Need to re-set mongo object due to initialisation in the constructor
        self.test_store._mongo = self.mongo
        self.assertEqual(self.mongo, self.test_store.mongo)

    def test_initialise_rabbitmq_initialises_everything_as_expected(
            self) -> None:
        # To make sure that the exchanges have not already been declared
        connect_to_rabbit(self.rabbitmq)
        delete_exchange_if_exists(self.rabbitmq, STORE_EXCHANGE)
        delete_exchange_if_exists(self.rabbitmq, HEALTH_CHECK_EXCHANGE)
        disconnect_from_rabbit(self.rabbitmq)

        self.test_store._initialise_rabbitmq()

        # Perform checks that the connection has been opened, marked as open
        # and that the delivery confirmation variable is set.
        self.assertTrue(self.test_store.rabbitmq.is_connected)
        self.assertTrue(self.test_store.rabbitmq.connection.is_open)
        self.assertTrue(
            self.test_store.rabbitmq.channel._delivery_confirmation)

        # Check whether the producing exchanges have been created by using
        # passive=True. If this check fails an exception is raised
        # automatically.
        self.test_store.rabbitmq.exchange_declare(HEALTH_CHECK_EXCHANGE,
                                                  passive=True)

        # Check whether the consuming exchange has been creating by sending
        # messages to it. If this fails an exception is raised, hence the test
        # fails.
        self.test_store.rabbitmq.basic_publish_confirm(
            exchange=STORE_EXCHANGE,
            routing_key=COSMOS_NETWORK_TRANSFORMED_DATA_ROUTING_KEY,
            body=self.test_data_str, is_body_dict=False,
            properties=pika.BasicProperties(delivery_mode=2), mandatory=False)

        # Re-declare queue to get the number of messages
        res = self.test_store.rabbitmq.queue_declare(
            COSMOS_NETWORK_STORE_INPUT_QUEUE_NAME, False, True, False, False)

        self.assertEqual(1, res.method.message_count)

        # Check that the message received is actually the HB
        _, _, body = self.test_store.rabbitmq.basic_get(
            COSMOS_NETWORK_STORE_INPUT_QUEUE_NAME)
        self.assertEqual(self.test_data_str, body.decode())

    @freeze_time("2012-01-01")
    def test_send_heartbeat_sends_a_hb_correctly(self) -> None:
        self.test_store._initialise_rabbitmq()
        res = self.test_store.rabbitmq.queue_declare(
            self.test_queue_name, False, True, False, False)
        self.assertEqual(0, res.method.message_count)
        self.rabbitmq.queue_bind(
            queue=self.test_queue_name,
            exchange=HEALTH_CHECK_EXCHANGE,
            routing_key=HEARTBEAT_OUTPUT_WORKER_ROUTING_KEY)

        test_hb = {
            'component_name': self.test_store_name,
            'is_alive': True,
            'timestamp': datetime.now().timestamp()
        }
        self.test_store._send_heartbeat(test_hb)

        # Re-declare queue to get the number of messages
        res = self.test_store.rabbitmq.queue_declare(
            self.test_queue_name, False, True, False, False)

        self.assertEqual(1, res.method.message_count)

        # Check that the message received is actually the HB
        _, _, body = self.test_store.rabbitmq.basic_get(
            self.test_queue_name)
        self.assertEqual(test_hb, json.loads(body))

    @mock.patch.object(RabbitMQApi, "basic_consume")
    @mock.patch.object(RabbitMQApi, "start_consuming")
    def test_listen_for_data_calls_basic_consume_and_listen_for_data(
            self, mock_start_consuming, mock_basic_consume) -> None:
        mock_start_consuming.return_value = None
        mock_basic_consume.return_value = None

        self.test_store._listen_for_data()

        mock_start_consuming.assert_called_once()
        mock_basic_consume.assert_called_once()

    @freeze_time("2012-01-01")
    @mock.patch.object(CosmosNetworkStore, "_process_mongo_store")
    @mock.patch.object(CosmosNetworkStore, "_process_redis_store")
    @mock.patch.object(CosmosNetworkStore, "_send_heartbeat")
    @mock.patch.object(RabbitMQApi, "basic_ack")
    def test_process_data_calls_process_redis_store_and_process_mongo_store(
            self, mock_ack, mock_send_hb, mock_proc_redis,
            mock_proc_mongo) -> None:
        mock_ack.return_value = None
        mock_send_hb.return_value = None
        mock_proc_redis.return_value = None
        mock_proc_mongo.return_value = None

        self.test_store._initialise_rabbitmq()
        blocking_channel = self.test_store.rabbitmq.channel
        method = pika.spec.Basic.Deliver(
            routing_key=COSMOS_NETWORK_TRANSFORMED_DATA_ROUTING_KEY)
        body = json.dumps(self.network_data_optionals_enabled)
        properties = pika.spec.BasicProperties()

        self.test_store._process_data(blocking_channel, method, properties,
                                      body)

        mock_proc_mongo.assert_called_once_with(
            self.network_data_optionals_enabled)
        mock_proc_redis.assert_called_once_with(
            self.network_data_optionals_enabled)
        mock_ack.assert_called_once()

        # We will also check if a heartbeat was sent to avoid having more tests
        test_hb = {
            'component_name': self.test_store_name,
            'is_alive': True,
            'timestamp': datetime.now().timestamp()
        }
        mock_send_hb.assert_called_once_with(test_hb)

    @parameterized.expand([
        (Exception('test'), None,),
        (None, Exception('test'),),
    ])
    @mock.patch.object(CosmosNetworkStore, "_process_mongo_store")
    @mock.patch.object(CosmosNetworkStore, "_process_redis_store")
    @mock.patch.object(CosmosNetworkStore, "_send_heartbeat")
    @mock.patch.object(RabbitMQApi, "basic_ack")
    def test_process_data_does_not_send_hb_if_processing_error(
            self, proc_redis_exception, proc_mongo_exception, mock_ack,
            mock_send_hb, mock_proc_redis, mock_proc_mongo) -> None:
        mock_ack.return_value = None
        mock_send_hb.return_value = None
        mock_proc_redis.side_effect = proc_redis_exception
        mock_proc_mongo.side_effect = proc_mongo_exception

        self.test_store._initialise_rabbitmq()
        blocking_channel = self.test_store.rabbitmq.channel
        method = pika.spec.Basic.Deliver(
            routing_key=COSMOS_NETWORK_TRANSFORMED_DATA_ROUTING_KEY)
        body = json.dumps(self.network_data_optionals_enabled)
        properties = pika.spec.BasicProperties()

        self.test_store._process_data(blocking_channel, method, properties,
                                      body)

        mock_send_hb.assert_not_called()
        mock_ack.assert_called_once()

    @mock.patch.object(CosmosNetworkStore, "_process_mongo_store")
    @mock.patch.object(CosmosNetworkStore, "_process_redis_store")
    @mock.patch.object(CosmosNetworkStore, "_send_heartbeat")
    @mock.patch.object(RabbitMQApi, "basic_ack")
    def test_process_data_does_not_raise_msg_not_del_exce_if_raised(
            self, mock_ack, mock_send_hb, mock_proc_redis,
            mock_proc_mongo) -> None:
        mock_ack.return_value = None
        mock_send_hb.side_effect = MessageWasNotDeliveredException('test')
        mock_proc_redis.return_value = None
        mock_proc_mongo.return_value = None

        self.test_store._initialise_rabbitmq()
        blocking_channel = self.test_store.rabbitmq.channel
        method = pika.spec.Basic.Deliver(
            routing_key=COSMOS_NETWORK_TRANSFORMED_DATA_ROUTING_KEY)
        body = json.dumps(self.network_data_optionals_enabled)
        properties = pika.spec.BasicProperties()

        try:
            self.test_store._process_data(blocking_channel, method, properties,
                                          body)
        except MessageWasNotDeliveredException as e:
            self.fail("Was not expecting {}".format(e))

        mock_ack.assert_called_once()

    @parameterized.expand([
        (AMQPConnectionError('test'), AMQPConnectionError,),
        (AMQPChannelError('test'), AMQPChannelError,),
        (Exception('test'), Exception,),
    ])
    @mock.patch.object(CosmosNetworkStore, "_process_mongo_store")
    @mock.patch.object(CosmosNetworkStore, "_process_redis_store")
    @mock.patch.object(CosmosNetworkStore, "_send_heartbeat")
    @mock.patch.object(RabbitMQApi, "basic_ack")
    def test_process_data_raises_unexpected_errors_if_raised(
            self, exception_instance, exception_type, mock_ack, mock_send_hb,
            mock_proc_redis, mock_proc_mongo) -> None:
        mock_ack.return_value = None
        mock_send_hb.side_effect = exception_instance
        mock_proc_redis.return_value = None
        mock_proc_mongo.return_value = None

        self.test_store._initialise_rabbitmq()
        blocking_channel = self.test_store.rabbitmq.channel
        method = pika.spec.Basic.Deliver(
            routing_key=COSMOS_NETWORK_TRANSFORMED_DATA_ROUTING_KEY)
        body = json.dumps(self.network_data_optionals_enabled)
        properties = pika.spec.BasicProperties()

        self.assertRaises(exception_type,
                          self.test_store._process_data,
                          blocking_channel, method, properties, body)

        mock_ack.assert_called_once()

    @mock.patch("src.data_store.stores.network.cosmos."
                "transformed_data_processing_helper")
    def test_process_redis_store_calls_transformed_data_helper_fn_correctly(
            self, mock_helper_fn) -> None:
        mock_helper_fn.return_value = None
        test_conf = {
            'cosmos_rest': {
                'result':
                    self.test_store._process_redis_cosmos_rest_result_store,
                'error':
                    self.test_store._process_redis_cosmos_rest_error_store,
            }
        }
        self.test_store._process_redis_store(
            self.network_data_optionals_enabled)
        mock_helper_fn.assert_called_once_with(
            self.test_store_name, test_conf,
            self.network_data_optionals_enabled)

    def test_process_redis_cosmos_rest_result_store_stores_correctly(
            self) -> None:
        data = self.network_data_optionals_enabled['cosmos_rest']['result']
        redis_hash = Keys.get_hash_parent(self.parent_id)

        self.test_store._process_redis_cosmos_rest_result_store(data)

        self.assertEqual(
            data['data']['proposals'],
            json.loads(self.redis.hget(
                redis_hash,
                Keys.get_cosmos_network_proposals(self.parent_id)
            ).decode('utf-8')))
        self.assertEqual(
            data['meta_data']['last_monitored'],
            convert_to_float(self.redis.hget(
                redis_hash,
                Keys.get_cosmos_network_last_monitored_cosmos_rest(
                    self.parent_id)
            ).decode('utf-8'), 'bad_val'))

    @mock.patch.object(RedisApi, "set")
    @mock.patch.object(RedisApi, "hset")
    @mock.patch.object(RedisApi, "set_multiple")
    @mock.patch.object(RedisApi, "hset_multiple")
    @mock.patch.object(RedisApi, "set_for")
    def test_process_redis_cosmos_error_store_does_not_save(
            self, mock_set_for, mock_hset_multiple, mock_set_multiple,
            mock_hset, mock_set) -> None:
        data = self.network_data_error['cosmos_rest']['error']
        self.test_store._process_redis_cosmos_rest_error_store(data)

        mock_set.return_value = None
        mock_hset.return_value = None
        mock_set_multiple.return_value = None
        mock_hset_multiple.return_value = None
        mock_set_for.return_value = None

        mock_set.assert_not_called()
        mock_hset.assert_not_called()
        mock_set_multiple.assert_not_called()
        mock_hset_multiple.assert_not_called()
        mock_set_for.assert_not_called()

    @mock.patch("src.data_store.stores.network.cosmos."
                "transformed_data_processing_helper")
    def test_process_mongo_store_calls_transformed_data_helper_fn_correctly(
            self, mock_helper_fn) -> None:
        mock_helper_fn.return_value = None
        test_conf = {
            'cosmos_rest': {
                'result':
                    self.test_store._process_mongo_cosmos_rest_result_store,
                'error':
                    self.test_store._process_mongo_cosmos_rest_error_store,
            },
        }
        self.test_store._process_mongo_store(
            self.network_data_optionals_enabled)
        mock_helper_fn.assert_called_once_with(
            self.test_store_name, test_conf,
            self.network_data_optionals_enabled)

    def test_process_mongo_cosmos_rest_result_store_stores_correctly(
            self) -> None:
        data = self.network_data_optionals_enabled['cosmos_rest']['result']
        meta_data = data['meta_data']
        parent_id = meta_data['parent_id']

        self.test_store._process_mongo_cosmos_rest_result_store(data)

        documents = self.mongo.get_all(parent_id)
        document = documents[0]
        expected = [
            'network',
            1,
            meta_data['last_monitored'],
        ]
        actual = [
            document['doc_type'],
            document['n_entries'],
            convert_to_float(document[parent_id][0]['last_monitored'],
                             'bad_val'),
        ]

        self.assertListEqual(expected, actual)

    @mock.patch.object(MongoApi, "insert_one")
    @mock.patch.object(MongoApi, "insert_many")
    @mock.patch.object(MongoApi, "update_one")
    def test_process_mongo_cosmos_rest_error_does_not_save(
            self, mock_update_one, mock_insert_many, mock_insert_one) -> None:
        data = self.network_data_error['cosmos_rest']['error']
        self.test_store._process_mongo_cosmos_rest_error_store(data)

        mock_update_one.return_value = None
        mock_insert_many.return_value = None
        mock_insert_one.return_value = None

        mock_update_one.assert_not_called()
        mock_insert_many.assert_not_called()
        mock_insert_one.assert_not_called()
