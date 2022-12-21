import time
from enum import Enum

from loguru import logger
import pinecone
import os

from pinecone import Index, GRPCIndex
from pinecone import PineconeException
from urllib3.exceptions import MaxRetryError

QUOTA = 2


class PodType(Enum):
    """
    Enum for pod types
    """
    P1 = 'p1'
    S1 = 's1'
    P2 = 'p2'

    def __str__(self):
        return self.value


class RemoteIndex:
    index = None

    def __init__(self, pods=1, index_name=None, dimension=512, pod_type=PodType.P1, metadata_config=None,
                 _openapi_client_config=None, grpc=0, source_collection=''):
        self.env = os.getenv('PINECONE_ENVIRONMENT')
        self.key = os.getenv('PINECONE_API_KEY')
        self._openapi_client_config = _openapi_client_config
        self.pod_type = pod_type
        pinecone.init(environment=self.env, api_key=self.key, openapi_config=self._openapi_client_config)
        self.pods = pods
        self.index_name = index_name if index_name else 'tests-service-{0}'.format(pod_type)
        self.dimension = dimension
        self.grpc = grpc
        self.metadata_config = metadata_config
        self.source_collection = source_collection

    def __enter__(self):
        if self.index_name not in pinecone.list_indexes():
            index_creation_args = {'name': self.index_name,
                                   'dimension': self.dimension,
                                   'pod_type': str(self.pod_type),
                                   'pods': self.pods,
                                   'timeout': 300,
                                   'metadata_config': self.metadata_config,
                                   'source_collection': self.source_collection}
            pinecone.create_index(**index_creation_args)

        if self.grpc:
            self.index = GRPCIndex(self.index_name)
        else:
            self.index = Index(self.index_name)
        self.wait_for_ready(self.index)
        return self.index

    @staticmethod
    def wait_for_ready(index):
        logger.info('waiting until index gets ready...')
        max_attempts = 30
        for i in range(max_attempts):
            try:
                time.sleep(1)
                index.describe_index_stats()
                break
            except (PineconeException, MaxRetryError):
                if i + 1 == max_attempts:
                    logger.info("Index didn't get ready in time. Raising error...")
                    raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        pinecone.delete_index(self.index_name, timeout=300)
        self.index.__exit__(exc_type, exc_val, exc_tb)
