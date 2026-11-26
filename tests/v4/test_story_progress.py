"""Deterministic story state does not infer progression from lantern brightness."""

from nur_game.cinematics.progress import StoryProgress
import pytest


def test_checkpoint_restarts_current_scene_without_forgetting_completed_ones():
    story = StoryProgress()
    story.begin_opening()
    story.skip()
    story.collect('F01')
    story.skip()
    story.collect('F02')
    story.tick(.1)
    assert hasattr(story, 'snapshot'), 'Story checkpoints must preserve fragment and scene ids'
    restored = StoryProgress.restore(story.snapshot())
    assert restored.collected == {'F01', 'F02'}
    assert restored.seen == {'CS00', 'CS01'}
    assert restored.active == 'CS02'
    assert restored.scene_elapsed == 0
    assert restored.snapshot() == story.snapshot()


@pytest.mark.parametrize('changes', [
    {'seen': ['CS00', 'CS01']},
    {'collected': ['F02'], 'seen': ['CS00', 'CS02']},
    {'active': 'CS02'},
    {'completed': True},
    {'finale_requested': True},
    {'active': 'CS08'},
])
def test_checkpoint_cannot_invent_missing_fragments_or_premature_ending(changes):
    data = StoryProgress().snapshot()
    data.update(changes)
    with pytest.raises(ValueError):
        StoryProgress.restore(data)


def test_finale_requires_all_six_memories_and_reveals_real_world_only_after_void():
    story = StoryProgress()
    story.begin_opening()
    story.skip()
    assert hasattr(story, 'request_finale'), 'The final road needs a narrative ending'
    assert not story.request_finale()
    for number in range(1, 7):
        story.collect(f'F{number:02d}')
        assert story.active == f'CS{number:02d}'
        assert not story.request_finale()
        story.skip()
    assert story.ready and story.request_finale()
    assert story.active == 'CS07' and not story.completed
    story.skip()
    assert story.active == 'CS08' and not story.completed
    story.skip()
    assert story.active is None and story.completed
    assert StoryProgress.restore(story.snapshot()).completed
