from __future__ import annotations

import asyncio
import logging
import sys
import threading
import uuid

from django.db import transaction
from django.utils import timezone

from .models import (
    AIModelConfig,
    AIModelService,
    BusinessRequirement,
    PromptConfig,
    RequirementAnalysis,
    RequirementDocument,
    TestCaseGenerationTask,
)
from .prompt_defaults import ensure_default_prompt_config, get_preferred_prompt_config
from .services import DocumentProcessor

logger = logging.getLogger(__name__)


def trim_text(value, limit):
    text = str(value or '').strip()
    if len(text) <= limit:
        return text
    return f'{text[:limit]}...(已截断)'


def generate_ai_requirement_id():
    timestamp = timezone.localtime().strftime('%Y%m%d%H%M%S')
    base_id = f'AIREQ{timestamp}'
    if not BusinessRequirement.objects.filter(requirement_id=base_id).exists():
        return base_id

    suffix = 1
    while True:
        requirement_id = f'{base_id}{suffix:03d}'
        if not BusinessRequirement.objects.filter(requirement_id=requirement_id).exists():
            return requirement_id
        suffix += 1


def ensure_document_text(document):
    if not document.extracted_text:
        document.extracted_text = DocumentProcessor.extract_text(document)
        document.save(update_fields=['extracted_text', 'updated_at'])
    return str(document.extracted_text or '').strip()


def create_requirement_from_text_document(
    *,
    user,
    project,
    title,
    content,
    source='ai_assistant_document',
    module='AI需求',
    requirement_type='functional',
    requirement_level='medium',
):
    document = RequirementDocument.objects.create(
        title=trim_text(title, 200) or 'AI需求文档',
        file=f'{source}/{uuid.uuid4().hex}.txt',
        document_type='txt',
        status='uploaded',
        uploaded_by=user,
        project=project,
        file_size=len(str(content or '').encode('utf-8')),
        extracted_text=str(content or '').strip(),
    )
    return create_requirement_from_document(
        document=document,
        user=user,
        project=project,
        title=title,
        module=module,
        requirement_type=requirement_type,
        requirement_level=requirement_level,
        source=source,
    )


def create_requirement_from_document(
    *,
    document,
    user,
    project=None,
    project_id=None,
    title='',
    module='AI需求',
    requirement_type='functional',
    requirement_level='medium',
    source='document_upload',
):
    if project is None and project_id:
        from apps.projects.models import Project

        project = Project.objects.filter(id=project_id).first()

    document_text = ensure_document_text(document)
    if not document_text:
        raise ValueError('无法从需求文档中提取有效文本。')

    with transaction.atomic():
        if project and document.project_id != project.id:
            document.project = project

        document.status = 'analyzed'
        document.save(update_fields=['project', 'status', 'extracted_text', 'updated_at'])

        analysis = RequirementAnalysis.objects.filter(document=document).first()
        if analysis:
            existing_requirement = analysis.requirements.order_by('id').first()
            if existing_requirement:
                return existing_requirement, analysis, False
        else:
            analysis = RequirementAnalysis.objects.create(
                document=document,
                analysis_report=(
                    f'由{source}创建的需求分析记录。\n\n'
                    f'来源文档：{document.title}\n\n'
                    f'文档内容摘要：\n{trim_text(document_text, 2000)}'
                ),
                requirements_count=0,
                analysis_time=0.5,
            )

        requirement_name = trim_text(title or document.title, 200) or 'AI需求文档创建需求'
        requirement_id = generate_ai_requirement_id()
        requirement = BusinessRequirement.objects.create(
            analysis=analysis,
            requirement_id=requirement_id,
            requirement_name=requirement_name,
            requirement_type=requirement_type,
            module=module or 'AI需求',
            requirement_level=requirement_level,
            reviewer=getattr(user, 'username', '') or 'AI助手',
            estimated_hours=8,
            description='\n'.join([
                f'来源文档：{document.title}',
                '',
                trim_text(document_text, 20000),
            ]).strip(),
            acceptance_criteria='需求文档内容已提取，需通过需求分析、需求评审和测试用例生成补充验收标准。',
        )

        analysis.requirements_count = analysis.requirements.count()
        analysis.save(update_fields=['requirements_count', 'updated_at'])

    return requirement, analysis, True


def build_requirement_text_for_generation(requirement):
    project_name = ''
    if requirement.analysis_id and getattr(requirement.analysis, 'document', None):
        project_name = getattr(requirement.analysis.document.project, 'name', '') or ''

    return '\n'.join([
        f'需求编号：{requirement.requirement_id}',
        f'需求名称：{requirement.requirement_name}',
        f'所属项目：{project_name or "-"}',
        f'需求类型：{requirement.get_requirement_type_display()}',
        f'需求级别：{requirement.get_requirement_level_display()}',
        f'所属模块：{requirement.module}',
        '',
        '需求描述：',
        requirement.description or '',
        '',
        '验收标准：',
        requirement.acceptance_criteria or '',
    ]).strip()


def create_testcase_generation_task_for_requirement(requirement, user):
    writer_config = AIModelConfig.objects.filter(role='writer', is_active=True).first()
    if not writer_config:
        raise ValueError('未找到可用的测试用例编写模型配置。')

    reviewer_config = AIModelConfig.objects.filter(role='reviewer', is_active=True).first()
    writer_prompt = get_preferred_prompt_config('writer') or ensure_default_prompt_config('writer', created_by=user)
    reviewer_prompt = get_preferred_prompt_config('reviewer')
    if reviewer_config and not reviewer_prompt:
        reviewer_prompt = ensure_default_prompt_config('reviewer', created_by=user)

    project = None
    if requirement.analysis_id and getattr(requirement.analysis, 'document', None):
        project = requirement.analysis.document.project

    task = TestCaseGenerationTask.objects.create(
        task_id=f'TASK_{uuid.uuid4().hex[:8].upper()}',
        title=f'{requirement.requirement_name} - 需求文档生成用例'[:200],
        requirement_text=build_requirement_text_for_generation(requirement),
        writer_model_config=writer_config,
        reviewer_model_config=reviewer_config,
        writer_prompt_config=writer_prompt,
        reviewer_prompt_config=reviewer_prompt if reviewer_config else None,
        project=project,
        generation_log='由需求文档上传入口创建测试用例生成任务。',
        created_by=user,
    )

    requirement.case_generation_status = 'generating'
    requirement.save(update_fields=['case_generation_status', 'updated_at'])
    if 'test' not in sys.argv:
        start_testcase_generation_task(task, requirement=requirement)
    return task


def start_testcase_generation_task(task, *, requirement=None):
    def execute_task():
        try:
            task.status = 'generating'
            task.progress = 10
            task.save(update_fields=['status', 'progress', 'updated_at'])

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                task.progress = 30
                task.save(update_fields=['progress', 'updated_at'])

                generated_cases = loop.run_until_complete(AIModelService.generate_test_cases(task))
                task.generated_test_cases = generated_cases
                task.progress = 60
                task.save(update_fields=['generated_test_cases', 'progress', 'updated_at'])

                if task.reviewer_model_config and task.reviewer_prompt_config:
                    task.status = 'reviewing'
                    task.progress = 70
                    task.save(update_fields=['status', 'progress', 'updated_at'])
                    try:
                        review_feedback = loop.run_until_complete(
                            asyncio.wait_for(
                                AIModelService.review_test_cases(task, generated_cases),
                                timeout=120.0,
                            )
                        )
                    except asyncio.TimeoutError:
                        review_feedback = '评审超时，已保留生成的测试用例作为最终结果。'
                    except Exception as exc:
                        review_feedback = f'评审失败：{exc}\n\n已保留生成的测试用例作为最终结果。'
                    task.review_feedback = review_feedback

                task.final_test_cases = generated_cases
                task.status = 'completed'
                task.progress = 100
                task.completed_at = timezone.now()
                task.save(update_fields=[
                    'generated_test_cases',
                    'review_feedback',
                    'final_test_cases',
                    'status',
                    'progress',
                    'completed_at',
                    'updated_at',
                ])

                if requirement:
                    requirement.case_generation_status = 'generated'
                    requirement.save(update_fields=['case_generation_status', 'updated_at'])
            finally:
                loop.close()
        except Exception as exc:
            logger.error('需求文档测试用例生成任务执行失败: %s', exc)
            task.status = 'failed'
            task.error_message = str(exc)
            task.save(update_fields=['status', 'error_message', 'updated_at'])
            if requirement:
                requirement.case_generation_status = 'failed'
                requirement.save(update_fields=['case_generation_status', 'updated_at'])

    thread = threading.Thread(target=execute_task, daemon=True)
    thread.start()
