import pytest

import opus_magnum_sym.elements.env.index_manager as im
from opus_magnum_sym.elements.env import level_counter
from opus_magnum_sym.elements.env.area_tracker import default_area_tracker


@pytest.fixture(autouse=True)
def clean_state():
    im.reset()
    level_counter.reset()
    default_area_tracker.reset()
    yield  # noqa: PT022
