import uuid

import numpy as np

from .remote_index import RemoteIndex, PodType
from .utils import index_fixture_factory, retry_assert

d = 256

n1 = 5
n2 = 10
namespace_1 = 'test_1'
namespace_2 = 'test_2'
vectors = [np.random.rand(d).astype(np.float32).tolist() for i in range(n1 + n2)]
ids = [str(uuid.uuid4()) for _ in range(n1 + n2)]

INDEX_NAME_PREFIX = 'test-namespace'

test_namespaces_index = index_fixture_factory(
    [(RemoteIndex(pods=1, index_name=f'{INDEX_NAME_PREFIX}-{PodType.P1}',
                  dimension=d,
                  pod_type=PodType.P1), 'p1'),
     (RemoteIndex(pods=1, index_name=f'{INDEX_NAME_PREFIX}-{PodType.S1}',
                  dimension=d,
                  pod_type=PodType.S1), 's1'),
     (RemoteIndex(pods=1, index_name=f'{INDEX_NAME_PREFIX}-{PodType.P2}', dimension=d,
                  pod_type=PodType.P2), 'p2')]
)


def test_upsert(test_namespaces_index):
    """
    simple upsert to 2 namespaces
    """
    index, _ = test_namespaces_index
    index.upsert(vectors=zip(ids[:n1], list(vectors[:n1])), namespace=namespace_1)
    index.upsert(vectors=zip(ids[:n2], list(vectors[:n2])), namespace=namespace_2)

    retry_assert(lambda: index.describe_index_stats()['namespaces'][namespace_1]['vector_count'] == n1)
    retry_assert(lambda: index.describe_index_stats()['namespaces'][namespace_2]['vector_count'] == n2)


def test_query(test_namespaces_index):
    """
    simple query from 2 namespaces
    """
    index, _ = test_namespaces_index
    query_response = index.query(queries=[vectors[1]], top_k=n1, namespace=namespace_1)
    assert len(query_response.results[0].matches) == n1
    query_response = index.query(queries=[vectors[1]], top_k=n2, namespace=namespace_2)
    assert len(query_response.results[0].matches) == n2


def test_query_nonexistent(test_namespaces_index):
    """
    query from default and a random namespace.
    """
    index, _ = test_namespaces_index
    index.query(queries=[vectors[1]], top_k=n1)
    rand_name = "random_namespace"
    index.query(queries=[vectors[1]], top_k=n1, namespace=rand_name)


def test_delete_nonexistent(test_namespaces_index):
    """
        delete from the default namespace and from random namespace.
    """
    index, _ = test_namespaces_index
    rand_name = "random_namespace"
    index.delete(ids=[ids[1]])
    index.delete(ids=[ids[1]], namespace=rand_name)
    retry_assert(lambda: index.describe_index_stats()['namespaces'][namespace_1]['vector_count'] == n1)
    retry_assert(lambda: index.describe_index_stats()['namespaces'][namespace_2]['vector_count'] == n2)


def test_delete_from_namespace(test_namespaces_index):
    """
    delete from a specific namespace
    """
    index, _ = test_namespaces_index
    index.delete(ids=[ids[1]], namespace=namespace_1)
    retry_assert(
        lambda: index.describe_index_stats()['namespaces'][namespace_1]['vector_count'] == n1 - 1)
    retry_assert(lambda: index.describe_index_stats()['namespaces'][namespace_2]['vector_count'] == n2)

    index.delete(ids=[ids[0]], namespace=namespace_2)
    retry_assert(
        lambda: index.describe_index_stats()['namespaces'][namespace_1]['vector_count'] == n1 - 1)
    retry_assert(
        lambda: index.describe_index_stats()['namespaces'][namespace_2]['vector_count'] == n2 - 1)


def test_delete_namespace(test_namespaces_index):
    """
    delete a specific namespace
    """
    index, _ = test_namespaces_index
    index.delete(delete_all=True, namespace=namespace_1)
    retry_assert(lambda: namespace_1 not in index.describe_index_stats()['namespaces'])
