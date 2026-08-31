"""Celery Tasks.

Attributes:
    MODULE_PATH (str): This module absolute path.

"""
import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey

from openedx_lti_tool_plugin.edxapp_wrapper.grades_module import course_grade_factory
from openedx_lti_tool_plugin.edxapp_wrapper.modulestore_module import modulestore
from openedx_lti_tool_plugin.models import LtiProfile
from openedx_lti_tool_plugin.resource_link_launch.ags import MODULE_PATH
from openedx_lti_tool_plugin.resource_link_launch.ags.models import LtiActivityLineitem, LtiGradedResource

log = logging.getLogger(__name__)
MODULE_PATH = f'{MODULE_PATH}.tasks'
AGS_CLAIM_ENDPOINT = 'https://purl.imsglobal.org/spec/lti-ags/claim/endpoint'
AGS_SCORE_SCOPE = 'https://purl.imsglobal.org/spec/lti-ags/scope/score'
AGS_LINEITEM_SCOPE = 'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem'


def is_gradable_block(block) -> bool:
    """Return True if a block produces a score and is graded or weighted.

    Covers native ``problem`` blocks, consumed LTI tools (``lti_consumer``) and any
    other scored XBlock, so each becomes its own lineitem on the target platform.
    """
    return bool(
        getattr(block, 'has_score', False)
        and (getattr(block, 'graded', False) or getattr(block, 'weight', None))
    )


def get_gradable_blocks(course_key: CourseKey) -> list:
    """Return all gradable, scored blocks in the course.

    Args:
        course_key: CourseKey of the launched course.

    Returns:
        List of gradable block instances.

    """
    return [block for block in modulestore().get_items(course_key) if is_gradable_block(block)]


def get_gradable_blocks_for_resource(resource_id: str) -> list:
    """Return the gradable blocks for a launched resource (course OR container block).

    - Course launch → every gradable block in the course.
    - Container block launch (section/subsection/unit) → the gradable blocks within it,
      so embedding a unit creates one lineitem per problem inside that unit.
    - Leaf block launch (a single problem) → empty list: its own coupled lineitem
      (created in ``handle_ags``) already covers it, so we don't split it.

    Args:
        resource_id: Launched course or block ID.

    Returns:
        List of gradable block instances.

    """
    try:
        return get_gradable_blocks(CourseKey.from_string(resource_id))
    except InvalidKeyError:
        pass

    root = modulestore().get_item(UsageKey.from_string(resource_id))
    if not root.get_children():
        return []

    gradable = []

    def collect(block):
        for child in block.get_children():
            if is_gradable_block(child):
                gradable.append(child)
            collect(child)

    collect(root)

    return gradable


@shared_task(name=f'{MODULE_PATH}.setup_problem_lineitems')
def setup_problem_lineitems(
    lti_profile_id: int,
    resource_id: str,
    context_id: str,
    resource_link_id: str,
    lineitems_url: str,
):
    """Create per-problem target lineitems and per-user LtiGradedResource records.

    Only used in **per-problem** passback mode (Moodle). For each gradable block in the
    launched content (native problems as well as consumed LTI tools and other scored
    blocks), creates (once, shared across users of the same activity) a lineitem on the
    platform via pylti1p3's ``find_or_create_lineitem`` and a per-user
    ``LtiGradedResource`` so its score posts to its own column.

    The lineitem is keyed and tagged by ``resource_link_id`` so that two platform
    activities embedding the same Open edX problem get separate columns instead of one.
    The AGS message is rebuilt from a JWT carrying the ``lineitems`` collection URL,
    mirroring ``LtiGradedResource.publish_score``.

    Args:
        lti_profile_id: ID of the launching user's LtiProfile.
        resource_id: The launched Open edX course/content ID.
        context_id: LTI context claim id (the platform's course/context).
        resource_link_id: LTI resource link id (the platform activity/placement).
        lineitems_url: AGS lineitems collection URL from the launch JWT.

    """
    from pylti1p3.contrib.django import DjangoDbToolConf, DjangoMessageLaunch  # pylint: disable=import-outside-toplevel
    from pylti1p3.lineitem import LineItem  # pylint: disable=import-outside-toplevel

    lti_profile = LtiProfile.objects.filter(id=lti_profile_id).first()
    if not lti_profile:
        return

    blocks = get_gradable_blocks_for_resource(resource_id)

    # JWT carrying the lineitems collection URL — mirrors publish_score_jwt.
    jwt = {
        'body': {
            'iss': lti_profile.platform_id,
            'aud': lti_profile.client_id,
            AGS_CLAIM_ENDPOINT: {
                'lineitems': lineitems_url,
                'scope': {AGS_LINEITEM_SCOPE, AGS_SCORE_SCOPE},
            },
        },
    }
    ags = DjangoMessageLaunch(request=None, tool_config=DjangoDbToolConf())\
        .set_auto_validation(enable=False)\
        .set_jwt(jwt)\
        .set_restored()\
        .validate_registration()\
        .get_ags()

    for block in blocks:
        block_id = str(block.location)
        label = block.display_name or block_id

        activity_lineitem, created = LtiActivityLineitem.objects.get_or_create(
            platform_id=lti_profile.platform_id,
            resource_link_id=resource_link_id,
            problem_id=block_id,
            defaults={'context_id': context_id, 'resource_id': resource_id, 'label': label},
        )

        if created or not activity_lineitem.lineitem:
            lineitem = LineItem()
            # Tag per (activity, problem) so distinct placements don't share a lineitem.
            lineitem.set_tag(f'{resource_link_id}:{block_id}' if resource_link_id else block_id)
            lineitem.set_label(label)
            lineitem.set_score_maximum(float(getattr(block, 'weight', None) or 1.0))
            activity_lineitem.lineitem = ags.find_or_create_lineitem(lineitem, find_by='tag').get_id()
            activity_lineitem.save()

        try:
            LtiGradedResource.objects.get_or_create(
                lti_profile=lti_profile,
                context_key=block_id,
                lineitem=activity_lineitem.lineitem,
            )
        except ValidationError as exc:
            log.warning(
                'LTI AGS: skipping LtiGradedResource for block %s: %s',
                block_id,
                exc.messages,
            )


@shared_task(name=f'{MODULE_PATH}.send_score_updates')
def send_score_updates(
    user_id: str,
    course_id: str,
    problem_id: str,
):
    """Publish AGS scores for every launched resource affected by a grade change.

    A grade change in Open edX is only ``(user, block)`` — it carries no notion of which
    platform activity the learner launched. So on each change we walk the changed block
    and its ancestors (unit, subsection, section) up to — but not including — the course,
    and for every level that has an ``LtiGradedResource`` for this user we post that
    level's aggregate score to its lineitem. This serves both:

    - **coupled** records (context = a launched unit/subsection/component) -> the launched
      resource's aggregate lands in its single per-placement column, and
    - **per-problem** records (context = a leaf block) -> the block's own score.

    The course level is handled separately by ``publish_course_score``.

    Args:
        user_id: Grading user ID.
        course_id: Context course id string.
        problem_id: Usage id of the block whose score changed.

    """
    lti_profile = LtiProfile.objects.filter(user__id=user_id).first()
    if not lti_profile:
        return

    try:
        usage_key = UsageKey.from_string(problem_id)
    except InvalidKeyError:
        return

    user = get_user_model().objects.filter(id=user_id).first()
    if not user:
        return

    course_grade = course_grade_factory().read(
        user,
        modulestore().get_course(CourseKey.from_string(course_id)),
    )

    # Collect the changed block and its ancestors, up to (not including) the course.
    locations = []
    block = modulestore().get_item(usage_key)
    while block is not None and block.location.block_type != 'course':
        locations.append(block.location)
        parent = getattr(block, 'parent', None)
        block = modulestore().get_item(parent) if parent else None

    for location in locations:
        graded_resources = LtiGradedResource.objects.all_from_user_id(
            user_id=user_id,
            context_key=str(location),
        )
        if not graded_resources:
            continue

        earned, possible = course_grade.score_for_block(location)
        for graded_resource in graded_resources:
            log.info(
                'LTI AGS: Sending AGS update for %s with user %s',
                str(location),
                user_id,
            )
            graded_resource.publish_score(earned, possible)
