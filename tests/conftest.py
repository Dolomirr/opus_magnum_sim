import pytest

import opus_magnum_sym.elements.env.index_manager as im
from opus_magnum_sym.elements.env import level_counter


@pytest.fixture(autouse=True)
def clean_state():
    im.reset()
    level_counter.CORRECT_FINISHED = 0
    yield  # noqa: PT022
