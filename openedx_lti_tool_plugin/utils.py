"""Utilities for openedx_lti_tool_plugin."""
from datetime import datetime, timezone

from django.http.request import HttpRequest
from opaque_keys.edx.keys import CourseKey

from openedx_lti_tool_plugin.edxapp_wrapper.course_experience_module import get_course_outline_block_tree
from openedx_lti_tool_plugin.edxapp_wrapper.learning_sequences_module import get_user_course_outline


def get_course_outline(request: HttpRequest, course_id: str) -> dict:
    """Get course outline.

    Args:
        request: HTTP request object.
        course_id: Course ID string.

    Returns:
        Dictionary with course outline.
    """
    # Get course block tree for user.
    course_blocks = get_course_outline_block_tree(request, course_id, request.user)
    # Get course outline for user.
    course_outline = get_user_course_outline(
        CourseKey.from_string(course_id),
        request.user,
        datetime.now(tz=timezone.utc),
    )
    # Get available sequences in course for user.
    available_sequences = [str(usage_key) for usage_key in course_outline.sequences]
    # Remove unavailable sequences from block tree.
    for chapter in course_blocks.get('children', []):
        children = []

        for sequence in chapter.get('children', []):
            if sequence.get('id') in available_sequences:
                children.append(sequence)

        chapter['children'] = children

    return course_blocks
