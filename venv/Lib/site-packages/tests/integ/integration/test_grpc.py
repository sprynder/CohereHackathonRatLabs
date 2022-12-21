import itertools
import os
import sys
from typing import Optional

import pinecone
import pytest
from loguru import logger
from pinecone import GRPCIndex, PineconeException

from .remote_index import RemoteIndex, PodType
from .utils import index_fixture_factory, retry_assert, pinecone_init

logger.remove()
logger.add(sys.stdout, level=(os.getenv("PINECONE_LOGGING") or "INFO"))

vector_dim = 512
env = os.getenv('PINECONE_ENVIRONMENT')
api_key = os.getenv('PINECONE_API_KEY')

INDEX_NAME_PREFIX = 'test-grpc'

test_data_plane_index = index_fixture_factory(
    [(RemoteIndex(pods=2, index_name=f'{INDEX_NAME_PREFIX}-{PodType.P1}',
                  dimension=vector_dim,
                  pod_type=PodType.P1, grpc=1), 'p1'),
     (RemoteIndex(pods=2, index_name=f'{INDEX_NAME_PREFIX}-{PodType.S1}',
                  dimension=vector_dim,
                  pod_type=PodType.S1, grpc=1), 's1'),
     (RemoteIndex(pods=2, index_name=f'{INDEX_NAME_PREFIX}-{PodType.P2}',
                  dimension=vector_dim,
                  pod_type=PodType.P2, grpc=1), 'p2')]
    )


def get_test_data(vector_count=10, no_meta_vector_count=5, dimension=vector_dim):
    """repeatably produces same results for a given vector_count"""
    meta_vector_count = vector_count - no_meta_vector_count
    metadata_choices = [
        {'genre': 'action', 'year': 2020},
        {'genre': 'documentary', 'year': 2021},
        {'genre': 'documentary', 'year': 2005},
        {'genre': 'drama', 'year': 2011},
    ]
    no_meta_vectors: list[tuple[str, list[float], Optional[dict]]] = [
        (f'vec{i}', [i / 1000] * dimension, None)
        for i in range(no_meta_vector_count)
    ]
    meta_vectors: list[tuple[str, list[float], Optional[dict]]] = [
        (f'mvec{i}', [i / 1000] * dimension, metadata_choices[i % len(metadata_choices)])
        for i in range(meta_vector_count)
    ]
    return list(meta_vectors) + list(no_meta_vectors)


def get_test_data_dict(vector_count=10, no_meta_vector_count=5):
    return {id_: (values, metadata) for id_, values, metadata in get_test_data(vector_count, no_meta_vector_count)}


def get_vector_count(index, namespace):
    stats = index.describe_index_stats().namespaces
    if namespace not in stats:
        return 0
    return stats[namespace].vector_count


def write_test_data(index, namespace, vector_count=10, no_meta_vector_count=5, dimension=vector_dim, batch_size=300):
    """writes vector_count vectors into index, half with metadata half without."""
    data = get_test_data(vector_count, no_meta_vector_count, dimension)
    count_before = get_vector_count(index, namespace)

    async_upsert(index, namespace, data, batch_size)

    retry_assert(lambda: vector_count == get_vector_count(index, namespace) - count_before)


def async_upsert(index, namespace, data, batch_size):
    def chunks():
        """A helper function to break an iterable into chunks of size batch_size."""
        it = iter(data)
        chunk = tuple(itertools.islice(it, batch_size))
        while chunk:
            yield chunk
            chunk = tuple(itertools.islice(it, batch_size))

    async_results = [index.upsert(vectors=data_chunk,
                                  namespace=namespace,
                                  async_req=True)
                     for data_chunk in chunks()]
    [async_result.result() for async_result in async_results]


def test_summarize_no_api_key():
    pinecone.init(api_key='', environment=env)
    with pytest.raises(PineconeException) as exc_info:
        nonexistent_index = GRPCIndex('nonexistent-index')
        api_response = nonexistent_index.describe_index_stats()
        logger.debug('got api response {}', api_response)
    logger.debug('got expected exception: {}', exc_info.value)
    pinecone.init(api_key=api_key, environment=env)


def test_summarize_nonexistent_index(pinecone_init):
    logger.info("api key header: " + os.getenv('PINECONE_API_KEY'))
    index = GRPCIndex('non-existent-index')
    with pytest.raises(PineconeException) as exc_info:
        api_response = index.describe_index_stats()
        logger.debug('got api response {}', api_response)
    logger.debug('got expected exception: {}', exc_info.value)


def test_invalid_upsert_no_params(test_data_plane_index):
    index, _ = test_data_plane_index
    with pytest.raises(TypeError) as exc_info:
        api_response = index.upsert()
        logger.debug('got api response {}', api_response)
    logger.debug('got expected exception: {}', exc_info.value)


def test_invalid_upsert_vector_no_values(test_data_plane_index):
    index, _ = test_data_plane_index
    with pytest.raises(TypeError) as exc_info:
        api_response = index.upsert(id='bad_vec1')
        logger.debug('got api response {}', api_response)
    logger.debug('got expected exception: {}', exc_info.value)


def test_upsert_vectors_no_metadata(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_upsert_vectors_no_metadata'
    ids = ['vec1', 'vec2']
    vectors = [[0.1] * vector_dim, [0.2] * vector_dim]
    api_response = index.upsert(vectors=zip(ids, vectors), namespace=namespace)
    assert api_response.upserted_count == 2
    logger.debug('got openapi upsert without metadata response: {}', api_response)


def test_upsert_vectors(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_upsert_vectors'
    metadata = [{'genre': 'action', 'year': 2020}, {'genre': 'documentary', 'year': 2021}]
    ids = ['mvec1', 'mvec2']
    values = [[0.1] * vector_dim, [0.2] * vector_dim]
    api_response = index.upsert(vectors=zip(ids, values, metadata), namespace=namespace)
    assert api_response.upserted_count == 2
    logger.debug('got openapi upsert with metadata response: {}', api_response)


def test_invalid_upsert_vectors_wrong_dimension(test_data_plane_index):
    index, _ = test_data_plane_index
    with pytest.raises(PineconeException) as e:
        ids = ['vec1', 'vec2']
        values = [[0.1] * 50, [0.2] * 50]
        api_response = index.upsert(vectors=zip(ids, values), namespace='ns1')
        logger.debug('got api response {}', api_response)
    logger.debug('got expected exception: {}', e.value)
    assert "dimension" in str(e.value)


def test_fetch_vectors_no_metadata(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_fetch_vectors_no_metadata'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    test_data = get_test_data_dict(vector_count)

    api_response = index.fetch(ids=['vec1', 'vec2'], namespace=namespace)
    logger.debug('got openapi fetch without metadata response: {}', api_response)

    assert api_response.vectors.get('vec1')
    assert api_response.vectors.get('vec1').values == test_data.get('vec1')[0]
    assert api_response.vectors.get('vec1').get('metadata') is None


def test_fetch_vectors(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_fetch_vectors'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    test_data = get_test_data_dict(vector_count)

    api_response = index.fetch(ids=['mvec1', 'mvec2'], namespace=namespace)
    logger.debug('got openapi fetch response: {}', api_response)

    assert api_response.vectors.get('mvec1')
    assert api_response.vectors.get('mvec1').values == test_data.get('mvec1')[0]
    assert api_response.vectors.get('mvec1').metadata == test_data.get('mvec1')[1]


def test_fetch_vectors_mixed_metadata(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_fetch_vectors_mixed_metadata'
    vector_count = 10
    write_test_data(index, namespace, vector_count, no_meta_vector_count=5)
    test_data = get_test_data_dict(vector_count)

    api_response = index.fetch(ids=['vec1', 'mvec2'], namespace=namespace)
    logger.debug('got openapi fetch response: {}', api_response)

    for vector_id in ['mvec2', 'vec1']:
        assert api_response.vectors.get(vector_id)
        assert api_response.vectors.get(vector_id).values == test_data.get(vector_id)[0]
        assert api_response.vectors.get(vector_id).metadata == test_data.get(vector_id)[1]


def test_invalid_fetch_nonexistent_vectors(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_invalid_fetch_nonexistent_vectors'
    write_test_data(index, namespace)
    api_response = index.fetch(ids=['no-such-vec1', 'no-such-vec2'], namespace=namespace)
    logger.debug('got openapi fetch response: {}', api_response)


def test_invalid_fetch_nonexistent_namespace(test_data_plane_index):
    index, _ = test_data_plane_index
    api_response = index.fetch(ids=['no-such-vec1', 'no-such-vec2'], namespace='no-such-namespace')
    logger.debug('got openapi fetch response: {}', api_response)


def test_summarize(test_data_plane_index):
    index, _ = test_data_plane_index
    vector_count = 400
    namespace = 'test_describe_index_stats'
    stats_before = index.describe_index_stats()
    assert stats_before.index_fullness == 0
    write_test_data(index, namespace, vector_count=vector_count, dimension=vector_dim)
    response = index.describe_index_stats()
    assert response.namespaces[namespace].vector_count == vector_count
    assert response.total_vector_count == stats_before.total_vector_count + vector_count


def test_summarize_with_filter(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_describe_index_stats_with_filter'
    count_before = get_vector_count(index, namespace)
    before_total_count = index.describe_index_stats().total_vector_count
    vectors = [('1', [0.1] * vector_dim, {'color': 'yellow'}),
               ('2', [-0.1] * vector_dim, {'color': 'red'}),
               ('3', [0.1] * vector_dim),
               ('4', [-0.1] * vector_dim, {'color': 'red'})]
    upsert_response = index.upsert(vectors=vectors, namespace=namespace)
    retry_assert(lambda: len(vectors) == get_vector_count(index, namespace) - count_before)
    logger.debug('got upsert response: {}', upsert_response)

    response = index.describe_index_stats(filter={'color': 'red'})
    assert response.namespaces[namespace].vector_count == 2
    assert response.total_vector_count == before_total_count + len(vectors)


def test_query_simple(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_simple'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    # simple query - no filter, no data, no metadata
    api_response = index.query(
        vector=[0.1] * vector_dim,
        namespace=namespace,
        top_k=10,
        include_values=False,
        include_metadata=False
    )
    logger.debug('got openapi query (no filter, no data, no metadata) response: {}', api_response)

    first_match_vector = api_response.matches[0]
    assert not first_match_vector.values
    assert not first_match_vector.metadata


def test_query_simple_with_values(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_simple_with_values'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    test_data = get_test_data_dict(vector_count)
    # simple query - no filter, with data, no metadata
    api_response = index.query(
        vector=[0.1] * vector_dim,
        namespace=namespace,
        top_k=10,
        include_values=True,
        include_metadata=False
    )
    logger.debug('got openapi query (no filter, with data, no metadata) response: {}', api_response)

    first_match_vector = api_response.matches[0]
    assert first_match_vector.values == test_data.get(first_match_vector.id)[0]
    assert not first_match_vector.metadata


def test_query_simple_with_values_metadata(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_simple_with_values_metadata'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    test_data = get_test_data_dict(vector_count)
    # simple query - no filter, with data, with metadata
    api_response = index.query(
        vector=[0.1] * vector_dim,
        namespace=namespace,
        top_k=10,
        include_values=True,
        include_metadata=True
    )
    logger.debug('got openapi query (no filter, with data, with metadata) response: {}', api_response)

    first_match_vector = api_response.matches[0]
    assert first_match_vector.values == test_data.get(first_match_vector.id)[0]
    if first_match_vector.id.startswith('mvec'):
        assert first_match_vector.metadata == test_data.get(first_match_vector.id)[1]
    else:
        assert not first_match_vector.metadata


def test_query_simple_with_values_mixed_metadata(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_simple_with_values_mixed_metadata'
    top_k = 10
    vector_count = 10
    write_test_data(index, namespace, vector_count, no_meta_vector_count=5)
    test_data = get_test_data_dict(vector_count, no_meta_vector_count=5)
    # simple query - no filter, with data, with metadata
    api_response = index.query(
        queries=[
            [0.1] * vector_dim,
            [0.2] * vector_dim
        ],
        namespace=namespace,
        top_k=top_k,
        include_values=True,
        include_metadata=True
    )
    logger.debug('got openapi query (no filter, with data, with metadata) response: {}', api_response)

    for query_vector_results in api_response.results:
        assert len(query_vector_results.matches) == top_k
        for match_vector in query_vector_results.matches:
            assert match_vector.values == test_data.get(match_vector.id)[0]
            if test_data.get(match_vector.id)[1]:
                assert match_vector.metadata == test_data.get(match_vector.id)[1]
            else:
                assert not match_vector.metadata


def test_query_simple_with_filter_values_metadata(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_simple_with_filter_values_metadata'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    test_data = get_test_data_dict(vector_count)
    # simple query - with filter, with data, with metadata
    api_response = index.query(
        vector=[0.1] * vector_dim,
        namespace=namespace,
        top_k=10,
        include_values=True,
        include_metadata=True,
        filter={'genre': {'$in': ['action']}}
    )
    logger.debug('got openapi query (with filter, with data, with metadata) response: {}', api_response)

    first_match_vector = api_response.matches[0]
    retry_assert(lambda: first_match_vector.values == test_data.get(first_match_vector.id)[0])
    retry_assert(lambda: first_match_vector.metadata == test_data.get(first_match_vector.id)[1])
    retry_assert(lambda: first_match_vector.metadata.get('genre') == 'action')


def test_query_mixed_metadata_sanity(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_mixed_metadata'
    count_before = get_vector_count(index, namespace)
    vectors = [('1', [0.1] * vector_dim, {'colors': 'yellow'}),
               ('2', [-0.1] * vector_dim, {'colors': 'red'})]
    upsert_response = index.upsert(vectors=vectors, namespace=namespace)
    retry_assert(lambda: len(vectors) == get_vector_count(index, namespace) - count_before)
    logger.debug('got upsert response: {}', upsert_response)

    query1_response = index.query(queries=[([0.1] * vector_dim, {'colors': 'yellow'})],
                                  top_k=10,
                                  include_metadata=True,
                                  namespace=namespace)
    logger.debug('got first query response: {}', query1_response)

    query2_response = index.query(queries=[([0.1] * vector_dim, {}), ([0.1] * vector_dim, {'colors': 'yellow'})],
                                  top_k=10,
                                  include_metadata=True,
                                  namespace=namespace)
    logger.debug('got second query response: {}', query2_response)

    vectors_dict = {k: m for k, _, m in vectors}
    for query_vector_results in query1_response.results:
        assert len(query_vector_results.matches) == 1
        for match_vector in query_vector_results.matches:
            if vectors_dict.get(match_vector.id):
                assert match_vector.metadata == vectors_dict.get(match_vector.id)
            else:
                assert not match_vector.metadata

    for query_vector_results in query2_response.results:
        for match_vector in query_vector_results.matches:
            if vectors_dict.get(match_vector.id):
                assert match_vector.metadata == vectors_dict.get(match_vector.id)
            else:
                assert not match_vector.metadata


def test_invalid_query_nonexistent_namespace(test_data_plane_index):
    index, _ = test_data_plane_index
    api_response = index.query(
        vector=[0.1] * vector_dim,
        namespace='no-such-ns',
        top_k=10,
        include_values=True,
        include_metadata=True,
        filter={'action': {'$in': ['action']}}
    )
    logger.debug('got openapi query (with filter, with data, with metadata) response: {}', api_response)
    assert len(api_response.matches) == 0


def test_query_with_per_vector_top_k(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_with_per_vector_top_k'
    write_test_data(index, namespace)
    # query with query-vector-specific top_k override
    api_response = index.query(
        queries=[([0.1] * vector_dim, {}), ([0.2] * vector_dim, {})],
        namespace=namespace,
        top_k=10,
        include_values=True,
        include_metadata=True
    )
    logger.debug('got openapi query response: {}', api_response)


def test_query_by_id(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_by_id'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    test_data = get_test_data_dict(vector_count)
    api_response = index.query(
        id='vec1',
        namespace=namespace,
        top_k=10,
        include_values=True,
        include_metadata=True
    )
    logger.debug('got openapi query response: {}', api_response)

    assert len(api_response.matches) == 10
    for match_vector in api_response.matches:
        assert match_vector.values == test_data.get(match_vector.id)[0]
        if test_data.get(match_vector.id)[1]:
            assert match_vector.metadata == test_data.get(match_vector.id)[1]
        else:
            assert not match_vector.metadata


def test_query_by_id_not_found(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_by_id_not_found'
    id_ = 'nonexistent'
    with pytest.raises(PineconeException) as exc_info:
        api_response = index.query(
            id=id_,
            namespace=namespace,
            top_k=10,
            include_values=True,
            include_metadata=False
        )
        logger.debug('got openapi query response: {}', api_response)
    logger.debug('got expected exception: {}', exc_info.value)
    assert f"Could not find vector with id '{id_}' in namespace '{namespace}'" in str(exc_info.value)


def test_query_uses_distributed_knn(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_query_with_multi_shard'
    write_test_data(index, namespace, vector_count=1000, no_meta_vector_count=1000)
    query_response = index.query(
        vector=[0.1] * vector_dim,
        namespace=namespace,
        top_k=500,
        include_values=False,
        include_metadata=False
    )
    # assert that we got the same number of results as the top_k
    # regardless of the number of shards
    assert len(query_response.matches) == 500
    logger.debug('got openapi query response: {}', query_response)


def test_delete(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_delete'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    test_data = get_test_data_dict(vector_count)

    api_response = index.fetch(ids=['mvec1', 'mvec2'], namespace=namespace)
    logger.debug('got openapi fetch response: {}', api_response)
    assert api_response.vectors and api_response.vectors.get('mvec1').values == test_data.get('mvec1')[0]

    vector_count = get_vector_count(index, namespace)
    api_response = index.delete(ids=['vec1', 'vec2'], namespace=namespace)
    logger.debug('got openapi delete response: {}', api_response)
    retry_assert(lambda: get_vector_count(index, namespace) == (vector_count - 2))
    api_response = index.fetch(ids=['no-such-vec1', 'no-such-vec2'], namespace=namespace)
    logger.debug('got openapi fetch response: {}', api_response)


def test_delete_all(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_delete_all'
    write_test_data(index, namespace)
    api_response = index.delete(delete_all=True, namespace=namespace)
    logger.debug('got openapi delete response: {}', api_response)
    retry_assert(lambda: namespace not in index.describe_index_stats()['namespaces'])


def test_invalid_delete_nonexistent_ids(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_nonexistent_ids'
    write_test_data(index, namespace)
    api_response = index.delete(ids=['no-such-vec-1', 'no-such-vec-2'], namespace=namespace)
    logger.debug('got openapi delete response: {}', api_response)


def test_invalid_delete_from_nonexistent_namespace(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_delete_namespace_non_existent'
    api_response = index.delete(ids=['vec1', 'vec2'], namespace=namespace)
    logger.debug('got openapi delete response: {}', api_response)


def test_delete_all_nonexistent_namespace(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_delete_all_non_existent'
    api_response = index.delete(delete_all=True, namespace=namespace)
    logger.debug('got openapi delete response: {}', api_response)


def test_update(test_data_plane_index):
    index, _ = test_data_plane_index
    namespace = 'test_update'
    vector_count = 10
    write_test_data(index, namespace, vector_count)
    test_data = get_test_data_dict(vector_count)
    assert get_vector_count(index, namespace) == vector_count

    api_response = index.update(id='mvec1', namespace=namespace, values=test_data.get('mvec2')[0])
    logger.debug('got openapi update response: {}', api_response)
    retry_assert(
        lambda: index.fetch(ids=['mvec1'], namespace=namespace).vectors.get('mvec1').values == test_data.get('mvec2')[
            0])
    assert index.fetch(ids=['mvec1'], namespace=namespace).vectors.get('mvec1').metadata == test_data.get('mvec1')[1]

    api_response = index.update(id='mvec2', namespace=namespace, set_metadata=test_data.get('mvec1')[1])
    logger.debug('got openapi update response: {}', api_response)
    retry_assert(
        lambda: index.fetch(ids=['mvec2'], namespace=namespace).vectors.get('mvec2').metadata == test_data.get('mvec1')[
            1])
    assert index.fetch(ids=['mvec2'], namespace=namespace).vectors.get('mvec2').values == test_data.get('mvec2')[0]

    api_response = index.update(id='mvec3', namespace=namespace, values=test_data.get('mvec1')[0],
                                set_metadata=test_data.get('mvec2')[1])
    logger.debug('got openapi update response: {}', api_response)
    retry_assert(
        lambda: index.fetch(ids=['mvec3'], namespace=namespace).vectors.get('mvec3').values == test_data.get('mvec1')[
            0])
    assert index.fetch(ids=['mvec3'], namespace=namespace).vectors.get('mvec3').metadata == test_data.get('mvec2')[1]
