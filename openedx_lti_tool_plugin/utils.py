"""Utilities for openedx_lti_tool_plugin."""
from datetime import datetime, timezone

from django.http.request import HttpRequest
from opaque_keys.edx.keys import CourseKey

from openedx_lti_tool_plugin.edxapp_wrapper.course_experience_module import get_course_outline_block_tree
from openedx_lti_tool_plugin.edxapp_wrapper.learning_sequences_module import get_user_course_outline
from openedx_lti_tool_plugin.edxapp_wrapper.modulestore_module import modulestore


def get_course_outline(request: HttpRequest, course_id: str) -> dict:
    """Get course outline.

    Args:
        request: HTTP request object.
        course_id: Course ID string.

    Returns:
        Dictionary with course outline.
    """
    course_key = CourseKey.from_string(course_id)
    # Get course block tree for user.
    course_blocks = get_course_outline_block_tree(request, course_id, request.user)
    # Get course outline for user.
    course_outline = get_user_course_outline(
        course_key,
        request.user,
        datetime.now(tz=timezone.utc),
    )
    # Get available sequences in course for user.
    available_sequences = map(str, course_outline.sequences)
    available_units = [
        str(unit.location)
        for unit in modulestore().get_items(
            course_key,
            qualifiers={'block_type': 'vertical'},
        )
    ]

    # Remove unavailable sequences/units from block tree.
    for chapter in course_blocks.get('children', []):
        # Replace chapter children with available sequences.
        chapter['children'] = [
            sequence for sequence in chapter.get('children', [])
            if sequence.get('id') in available_sequences
        ]
        for sequence in chapter.get('children', []):
            # Replace sequence children with published units.
            sequence['children'] = [
                unit for unit in sequence.get('children', [])
                if unit.get('id') in available_units
            ]

    return course_blocks
