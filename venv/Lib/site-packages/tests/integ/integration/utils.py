import os
import time

from loguru import logger
import pinecone
import pytest

from .remote_index import RemoteIndex


@pytest.fixture
def pinecone_init():
    env = os.getenv('PINECONE_ENVIRONMENT')
    api_key = os.getenv('PINECONE_API_KEY')
    pinecone.init(api_key=api_key, environment=env)


# def inject_fixture(name, fixture):
#     globals()[name] = fixture


def index_fixture_factory(remote_indices: [(RemoteIndex, str)], include_random_suffix=False):
    """
    Creates and returns a pytest fixture for creating/tearing down indexes to test against.
    - adds the xdist testrun_uid to the index name unless include_random_suffix is set False
    - fixture yields a pinecone.Index object
    """

    def pinecone_init():
        env = os.getenv('PINECONE_ENVIRONMENT')
        api_key = os.getenv('PINECONE_API_KEY')
        pinecone.init(api_key=api_key, environment=env)

    @pytest.fixture(scope="module", params=[remote_index[0] for remote_index in remote_indices],
                    ids=[remote_index[1] for remote_index in remote_indices])
    def index_fixture(testrun_uid, request):
        pinecone_init()
        if include_random_suffix:
            request.param.index_name = request.param.index_name + '-' + testrun_uid

        def remove_index():
            if request.param.index_name in pinecone.list_indexes():
                pinecone.delete_index(request.param.index_name, timeout=300)

        # attempt to remove index even if creation raises exception
        request.addfinalizer(remove_index)

        logger.info('Proceeding with index_name {}', request.param.index_name)
        with request.param as index:
            yield index, request.param.index_name

    return index_fixture


def retry_assert(fun, max_tries=5):
    wait_time = 0.5
    last_exc = None
    for i in range(max_tries):
        try:
            assert fun()
            return
        except Exception as e:
            last_exc = e
            time.sleep(wait_time)
            wait_time = wait_time * 2
            continue
    if last_exc:
        raise last_exc
