"""Tests for control plane api calls"""
import os
import uuid
from itertools import cycle
from typing import NamedTuple, Optional

import numpy as np
import pinecone
import pytest
from pinecone import Vector
from pinecone.exceptions import ApiException, NotFoundException

from .test_data_plane import get_test_data_dict, write_test_data, get_vector_count
from .utils import retry_assert
from .remote_index import PodType, RemoteIndex

env = os.getenv('PINECONE_ENVIRONMENT')
key = os.getenv('PINECONE_API_KEY')

INDEX_NAME_PREFIX = 'test-control-plane'
d = 512

INDEX_NAME_KEY = 'index_name'
POD_TYPE_KEY = 'pod_type'


@pytest.fixture(scope="module",
                params=[{INDEX_NAME_KEY: f'{INDEX_NAME_PREFIX}-{PodType.P1}',
                         POD_TYPE_KEY: PodType.P1},
                        {INDEX_NAME_KEY: f'{INDEX_NAME_PREFIX}-{PodType.S1}',
                         POD_TYPE_KEY: PodType.S1},
                        {INDEX_NAME_KEY: f'{INDEX_NAME_PREFIX}-{PodType.P2}',
                         POD_TYPE_KEY: PodType.P2}],
                ids=['p1', 's1', 'p2'])
def index_fixture(request):
    index_name = request.param[INDEX_NAME_KEY]
    pod_type = request.param[POD_TYPE_KEY]
    # Note: relies on grouping strategy –-dist=loadfile to keep different xdist workers
    # from repeating this
    index_creation_args = {'name': index_name,
                           'dimension': d,
                           'pod_type': str(pod_type),
                           'pods': 2,
                           'timeout': 300}
    pinecone.create_index(**index_creation_args)

    def remove_index():
        if index_name in pinecone.list_indexes():
            pinecone.delete_index(index_name, timeout=300)

    # attempt to remove index even if creation raises exception
    request.addfinalizer(remove_index)

    yield index_name, f"{pod_type}.x1"


def setup_function():
    host = "https://controller.{}.pinecone.io".format(env)
    pinecone.init(host=host, api_key=key, environment=env)


# Dummy IndexDescription Class
class IndexDescription(object):
    def __init__(self, response: dict):
        for k, v in response.items():
            self.__dict__[k] = v

    def __str__(self):
        return str(self.__dict__)


def test_missing_dimension():
    # Missing Dimension
    name = 'test-missing-dim'
    with pytest.raises(TypeError):
        pinecone.create_index(name)


def test_invalid_name():
    # Missing Dimension
    name = 'Test-Bad-Name'
    with pytest.raises(ApiException) as e:
        pinecone.create_index(name, 32)
    assert e.value.status == 400


def test_quota_check():
    # Check with large number of shards
    with pytest.raises(ApiException):
        pinecone.create_index('big-index', d, pods=1000)
    # Check with large number of replicas:
    with pytest.raises(ApiException):
        pinecone.create_index('big-index', d, replicas=1000)


def test_get(index_fixture):
    index_name, pod_type = index_fixture
    # Successful Call
    result = pinecone.describe_index(index_name)

    meta_obj = IndexDescription(
        {'name': index_name, 'metric': 'cosine', 'replicas': 1, 'dimension': d, 'shards': 2, 'pods': 2,
         'pod_type': str(pod_type), 'status': {'ready': True, 'state': 'Ready'}}
    )

    assert result.__dict__ == meta_obj.__dict__

    # Calling non-existent index
    with pytest.raises(ApiException):
        pinecone.describe_index('non-existent-index')

    # Missing Field
    with pytest.raises(TypeError):
        pinecone.describe_index()


def test_update(index_fixture):
    index_name, _ = index_fixture
    # Scale Up
    num_replicas = 2
    pinecone.scale_index(name=index_name, replicas=num_replicas)
    meta_obj = pinecone.describe_index(index_name)
    assert meta_obj.replicas == 2
    assert meta_obj.pods == 4

    index = pinecone.Index(index_name=index_name)
    # Upsert to see if index still works
    n = 10
    ids = [str(uuid.uuid4()) for _ in range(n)]
    vectors = [np.random.rand(d).astype(np.float32).tolist() for _ in range(n)]
    weather_vocab = ['sunny', 'rain', 'cloudy', 'snowy']
    loop = cycle(weather_vocab)
    metadata = [{"value": i, 'weather': next(loop)} for i in range(n)]
    index.upsert(
        vectors=[
            Vector(id=ids[i], values=vectors[i], metadata=metadata[i])
            for i in range(5)
        ])
    retry_assert(lambda: index.describe_index_stats()['namespaces']['']['vector_count'] == n / 2)

    # Scale Down
    new_num_replicas = 1
    pinecone.scale_index(index_name, new_num_replicas)
    meta_obj = pinecone.describe_index(index_name)
    assert meta_obj.replicas == 1
    assert meta_obj.pods == 2
    # Upsert to see if index still works
    index.upsert(
        vectors=[
            Vector(id=ids[i], values=vectors[i], metadata=metadata[i])
            for i in range(5, n)
        ])
    retry_assert(lambda: index.describe_index_stats()['namespaces']['']['vector_count'] == n)

    # Missing replicas field
    with pytest.raises(TypeError):
        pinecone.scale_index(index_name)

    # Calling on non-existent index
    with pytest.raises(ApiException):
        pinecone.scale_index('non-existent-index', 2)


def test_scale_to_zero(index_fixture):
    index_name, _ = index_fixture
    num_replicas = 0
    pinecone.scale_index(name=index_name, replicas=num_replicas)
    retry_assert(lambda: pinecone.describe_index(index_name).replicas == 0)
    retry_assert(lambda: pinecone.describe_index(index_name).pods == 0)


def test_delete(index_fixture):
    index_name, _ = index_fixture
    # Delete existing index
    pinecone.delete_index(index_name)
    assert index_name not in pinecone.list_indexes()

    # Delete non existent index
    with pytest.raises(NotFoundException):
        pinecone.delete_index('non-existent-index')

    # Missing Field
    with pytest.raises(TypeError):
        pinecone.delete_index()


def test_quota_check():
    # Check with large number of shards
    with pytest.raises(ApiException) as e:
        pinecone.create_index('big-index', 512, shards=1000)
    # Check with large number of replicas:
    with pytest.raises(ApiException) as e:
        pinecone.create_index('big-index', 512, replicas=1000)


def test_collection():
    index_name = 'test-index'
    collection_name = 'integration-test-collection'
    dim = 512
    vector_count = 2000
    test_data = get_test_data_dict(vector_count, dimension=dim)
    with RemoteIndex(index_name=index_name, dimension=dim, pods=1) as index:
        write_test_data(index, '', vector_count, dimension=dim)
        assert get_vector_count(index, '') == vector_count

        pinecone.create_collection(collection_name, index_name)

        assert collection_name in pinecone.list_collections()

        retry_assert(lambda: pinecone.describe_collection(collection_name).status == 'Ready', 15)
        collection_metadata = pinecone.describe_collection(collection_name)
        assert collection_metadata.name == collection_name
        assert collection_metadata.size > 0

    index_name_from_collection = 'test-index-from-collection'
    with RemoteIndex(index_name=index_name_from_collection, dimension=dim, pods=2,
                     source_collection=collection_name) as index_from_collection:
        assert get_vector_count(index_from_collection, '') == vector_count

        id_ = next(iter(test_data))
        response = index_from_collection.fetch(ids=[id_], namespace='')
        assert response.vectors.get(id_).values == test_data[id_][0]
        assert response.vectors.get(id_).metadata == test_data[id_][1]

        pinecone.delete_collection(collection_name)
        retry_assert(lambda: collection_name not in pinecone.list_collections(), 15)


def test_create_collection_from_nonexistent_index():
    nonexistent_index_name = 'nonexistent_index_name'
    collection_name = 'collection'
    with pytest.raises(ApiException) as e:
        pinecone.create_collection(collection_name, nonexistent_index_name)
    assert e.value.body == f'source database {nonexistent_index_name} does not exist'


def test_create_index_from_nonexistent_collection():
    index_name = 'test-index'
    nonexistent_collection_name = 'nonexistent_collection_name'
    with pytest.raises(ApiException) as e:
        pinecone.create_index(index_name, d, pods=2, timeout=300, pod_type='s1',
                              source_collection=nonexistent_collection_name)
    assert e.value.body == f'failed to fetch source collection {nonexistent_collection_name}'
