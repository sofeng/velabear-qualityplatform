import json
import logging
import re
import threading
from difflib import SequenceMatcher

from asgiref.sync import async_to_sync
from django.db import close_old_connections, transaction
from django.utils import timezone

from apps.requirement_analysis.models import AIModelConfig, AIModelService
from apps.ui_automation.models import (
    Element,
    TestCase as UiAutomationTestCase,
    TestCaseStep as UiAutomationTestCaseStep,
    TestExecution,
    TestSuite,
    TestSuiteTestCase,
    UiProject,
)
from apps.ui_automation.operation_logger import log_operation
from apps.ui_automation.test_executor import TestExecutor

from .models import TestCaseUiAutomationRecord, TestRunUiAutomationBatch, TestRunUiAutomationCandidate

logger = logging.getLogger(__name__)


DEFAULT_UI_AUTOMATION_PROMPT = """You convert Chinese manual test cases into structured UI automation test cases.

Return JSON only. Do not use markdown code fences.

Required schema:
{
  "name": "string",
  "description": "string",
  "preconditions": "string",
  "priority": "high|medium|low",
  "steps": [
    {
      "step_number": 1,
      "description": "string",
      "action_type": "click|fill|getText|waitFor|hover|scroll|screenshot|assert|wait|enterIframe|exitIframe|switchTab",
      "element_name": "string",
      "input_value": "string",
      "wait_time": 1000,
      "assert_type": "textContains|textEquals|isVisible|exists|hasAttribute",
      "assert_value": "string"
    }
  ]
}

Rules:
- Prefer the provided element names exactly when relevant.
- Leave element_name empty when no element should be bound.
- wait_time must be an integer in milliseconds.
- Keep steps concise and executable.
- For assertion steps, provide assert_type and assert_value when possible.
"""


ACTION_TYPE_CHOICES = {
    "click",
    "fill",
    "getText",
    "waitFor",
    "hover",
    "scroll",
    "screenshot",
    "assert",
    "wait",
    "enterIframe",
    "exitIframe",
    "switchTab",
}

ASSERT_TYPE_CHOICES = {
    "textContains",
    "textEquals",
    "isVisible",
    "exists",
    "hasAttribute",
}


def normalize_text(value):
    if value is None:
        return ""
    value = str(value).strip().lower()
    return re.sub(r"[\s\-_:/\\|,.，。！？!?'\"“”‘’（）()【】\[\]<>《》]+", "", value)


def map_priority(source_priority):
    priority = (source_priority or "").lower()
    if priority in {"critical", "high", "p0", "p1"}:
        return "high"
    if priority in {"low", "p3"}:
        return "low"
    return "medium"


def normalize_wait_time(value):
    try:
        if value in ("", None):
            return 1000
        number = int(value)
        return max(number, 0)
    except (TypeError, ValueError):
        return 1000


def extract_json_object(raw_text):
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("AI 返回内容为空")

    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("无法从 AI 返回中解析 JSON")


def split_manual_steps(raw_steps):
    text = (raw_steps or "").strip()
    if not text:
        return []

    lines = [line.strip() for line in re.split(r"\r?\n+", text) if line.strip()]
    if len(lines) > 1:
        return [re.sub(r"^(?:步骤)?\d+[.、:：)\s]+", "", line).strip() for line in lines]

    parts = [
        part.strip()
        for part in re.split(r"(?:^|(?<=\s))(?:步骤)?\d+[.、:：)\s]+", text)
        if part and part.strip()
    ]
    if len(parts) > 1:
        return parts
    return [text]


def extract_input_value(text):
    source = (text or "").strip()
    if not source:
        return ""

    quote_match = re.search(r"[\"“'‘](.+?)[\"”'’]", source)
    if quote_match:
        return quote_match.group(1).strip()

    keyword_match = re.search(r"(?:输入|填写|录入|设置|搜索|键入)(.+)$", source)
    if keyword_match:
        value = keyword_match.group(1).strip()
        value = re.sub(r"^(为|成|内容为|内容是|值为|值是)", "", value).strip(" ：:，,。.")
        return value

    return ""


def infer_assert_type(text):
    source = (text or "").strip()
    if not source:
        return "textContains"
    if any(keyword in source for keyword in ["可见", "显示", "出现", "存在"]):
        return "isVisible"
    if any(keyword in source for keyword in ["等于", "一致", "为"]):
        return "textEquals"
    if any(keyword in source for keyword in ["属性", "attribute"]):
        return "hasAttribute"
    return "textContains"


def infer_action_type(step_text, expected_text=""):
    text = f"{step_text or ''} {expected_text or ''}"
    if "进入iframe" in text or "切入iframe" in text:
        return "enterIframe"
    if "退出iframe" in text or "返回上层iframe" in text:
        return "exitIframe"
    if "切换标签" in text or "切换页签" in text or "switch tab" in text.lower():
        return "switchTab"
    if "截图" in text:
        return "screenshot"
    if "悬停" in text or "hover" in text.lower():
        return "hover"
    if "滚动" in text:
        return "scroll"
    if "等待" in text and any(keyword in text for keyword in ["秒", "毫秒", "ms", "s"]):
        return "wait"
    if "等待" in text:
        return "waitFor"
    if any(keyword in text for keyword in ["校验", "验证", "断言", "检查", "确认"]):
        return "assert"
    if any(keyword in text for keyword in ["输入", "填写", "录入", "键入", "设置", "搜索"]):
        return "fill"
    if any(keyword in text for keyword in ["获取文本", "获取内容", "读取文本"]):
        return "getText"
    if any(keyword in text for keyword in ["点击", "单击", "双击", "提交", "保存", "选择", "勾选"]):
        return "click"
    return "click"


def build_source_snapshot(source_case):
    step_details = [
        {
            "step_number": step.step_number,
            "action": step.action,
            "expected": step.expected,
        }
        for step in source_case.step_details.all().order_by("step_number")
    ]
    return {
        "source_testcase_id": source_case.id,
        "title": source_case.title,
        "description": source_case.description,
        "preconditions": source_case.preconditions,
        "steps_text": source_case.steps,
        "expected_result": source_case.expected_result,
        "priority": source_case.priority,
        "test_type": source_case.test_type,
        "step_details": step_details,
    }


def build_element_catalog(ui_project):
    elements = (
        Element.objects.filter(project=ui_project)
        .select_related("locator_strategy")
        .order_by("page", "order", "name")
    )
    return [
        {
            "id": element.id,
            "name": element.name,
            "page": element.page or "",
            "description": element.description or "",
            "element_type": element.element_type,
            "locator_strategy": element.locator_strategy.name if element.locator_strategy else "",
            "locator_value": element.locator_value,
        }
        for element in elements
    ]


def match_element(step_text, elements, preferred_name=""):
    normalized_preferred = normalize_text(preferred_name)
    normalized_step = normalize_text(step_text)
    best_match = None

    for element in elements:
        normalized_name = normalize_text(element["name"])
        if not normalized_name:
            continue

        score = 0
        match_type = ""
        reason = ""

        if normalized_preferred and normalized_name == normalized_preferred:
            score = 1.0
            match_type = "exact"
            reason = "与 AI 返回的元素名称完全一致"
        elif normalized_preferred and (
            normalized_preferred in normalized_name or normalized_name in normalized_preferred
        ):
            score = 0.95
            match_type = "contains"
            reason = "与 AI 返回的元素名称高度匹配"
        elif normalized_step and normalized_name in normalized_step:
            score = 0.9
            match_type = "contains"
            reason = "步骤描述中直接包含元素名称"
        else:
            similarity = SequenceMatcher(None, normalized_step, normalized_name).ratio()
            if similarity >= 0.58:
                score = round(similarity, 4)
                match_type = "fuzzy"
                reason = "根据步骤描述进行模糊匹配"

        page = element.get("page") or ""
        normalized_page = normalize_text(page)
        if score > 0 and normalized_page and normalized_page in normalized_step:
            score = min(score + 0.05, 1.0)
            reason = f"{reason}，页面名称也匹配" if reason else "页面名称匹配"

        if score <= 0:
            continue

        current = {
            "element_id": element["id"],
            "element_name": element["name"],
            "match_type": match_type,
            "match_score": round(score, 4),
            "match_reason": reason,
        }
        if best_match is None or current["match_score"] > best_match["match_score"]:
            best_match = current

    return best_match


def build_step_record(index, action_type, description, element_match=None, **extra):
    return {
        "step_number": index,
        "description": (description or "").strip(),
        "action_type": action_type if action_type in ACTION_TYPE_CHOICES else infer_action_type(description),
        "element_id": element_match.get("element_id") if element_match else None,
        "element_name": element_match.get("element_name") if element_match else "",
        "input_value": extra.get("input_value", "") or "",
        "wait_time": normalize_wait_time(extra.get("wait_time", 1000)),
        "assert_type": extra.get("assert_type", "") or "",
        "assert_value": extra.get("assert_value", "") or "",
        "match_type": element_match.get("match_type") if element_match else "",
        "match_score": element_match.get("match_score") if element_match else 0,
        "match_reason": element_match.get("match_reason") if element_match else "",
    }


def normalize_candidate_steps(steps_data, elements=None):
    elements = elements or []
    element_map = {element["id"]: element for element in elements}
    normalized_steps = []

    for index, raw_step in enumerate(steps_data or [], start=1):
        raw_step = raw_step or {}
        description = (raw_step.get("description") or "").strip()
        action_type = raw_step.get("action_type") or infer_action_type(description)
        if action_type not in ACTION_TYPE_CHOICES:
            action_type = infer_action_type(description)

        element_id = raw_step.get("element_id")
        element_name = (raw_step.get("element_name") or "").strip()
        element_match = None

        if element_id and element_id in element_map:
            element = element_map[element_id]
            element_match = {
                "element_id": element["id"],
                "element_name": element["name"],
                "match_type": raw_step.get("match_type") or "manual",
                "match_score": raw_step.get("match_score") or 1,
                "match_reason": raw_step.get("match_reason") or "人工选择",
            }
        elif elements:
            element_match = match_element(description, elements, element_name)

        normalized_steps.append(
            build_step_record(
                index,
                action_type=action_type,
                description=description,
                element_match=element_match,
                input_value=raw_step.get("input_value", ""),
                wait_time=raw_step.get("wait_time", 1000),
                assert_type=raw_step.get("assert_type", "") if raw_step.get("assert_type", "") in ASSERT_TYPE_CHOICES else "",
                assert_value=raw_step.get("assert_value", ""),
            )
        )

    return normalized_steps


def build_heuristic_steps(source_snapshot, elements):
    steps = []

    if source_snapshot["step_details"]:
        for step in source_snapshot["step_details"]:
            action_text = step.get("action") or ""
            expected_text = step.get("expected") or ""
            action_type = infer_action_type(action_text, expected_text)
            element_match = match_element(action_text, elements)
            steps.append(
                build_step_record(
                    len(steps) + 1,
                    action_type=action_type,
                    description=action_text,
                    element_match=element_match,
                    input_value=extract_input_value(action_text) if action_type == "fill" else "",
                )
            )
            if expected_text:
                assert_match = match_element(expected_text, elements)
                steps.append(
                    build_step_record(
                        len(steps) + 1,
                        action_type="assert",
                        description=f"校验：{expected_text}",
                        element_match=assert_match,
                        assert_type=infer_assert_type(expected_text),
                        assert_value=expected_text,
                    )
                )
        return steps

    for item in split_manual_steps(source_snapshot.get("steps_text")):
        action_type = infer_action_type(item)
        element_match = match_element(item, elements)
        steps.append(
            build_step_record(
                len(steps) + 1,
                action_type=action_type,
                description=item,
                element_match=element_match,
                input_value=extract_input_value(item) if action_type == "fill" else "",
            )
        )

    expected_result = (source_snapshot.get("expected_result") or "").strip()
    if expected_result:
        steps.append(
            build_step_record(
                len(steps) + 1,
                action_type="assert",
                description=f"校验：{expected_result}",
                element_match=match_element(expected_result, elements),
                assert_type=infer_assert_type(expected_result),
                assert_value=expected_result,
            )
        )

    if not steps:
        title = source_snapshot.get("title") or "待补充步骤"
        steps.append(
            build_step_record(
                1,
                action_type=infer_action_type(title),
                description=title,
                element_match=match_element(title, elements),
            )
        )

    return steps


def refresh_batch_status(batch):
    if batch.status in {"running"}:
        return batch

    total = batch.candidates.count()
    approved = batch.candidates.filter(review_status="approved").count()
    pending = batch.candidates.filter(review_status="pending").count()

    if total == 0:
        batch.status = "draft"
    elif approved > 0 and pending == 0:
        batch.status = "approved"
    elif approved > 0:
        batch.status = "partially_approved"
    else:
        batch.status = "pending_review"

    batch.save(update_fields=["status", "updated_at"])
    return batch


class TestCaseUiAutomationService:
    @classmethod
    def auto_match_ui_project(cls, source_testcase):
        project_name = (getattr(source_testcase.project, "name", "") or "").strip()
        if not project_name:
            return None
        return UiProject.objects.filter(name=project_name).first()

    @classmethod
    def validate_target_ui_project(cls, source_testcase, target_ui_project):
        if target_ui_project is None:
            raise ValueError("请选择目标 UI 项目")

        source_project_name = (getattr(source_testcase.project, "name", "") or "").strip().casefold()
        target_project_name = (getattr(target_ui_project, "name", "") or "").strip().casefold()
        if source_project_name and target_project_name and source_project_name != target_project_name:
            raise ValueError("目标 UI 项目需与源测试用例所属项目同名")

        return target_ui_project

    @classmethod
    def get_or_create_record(cls, source_testcase, target_ui_project, engine, user):
        defaults = {
            "target_ui_project": target_ui_project,
            "engine": engine,
            "created_by": user,
            "updated_by": user,
        }
        record, created = TestCaseUiAutomationRecord.objects.get_or_create(
            source_testcase=source_testcase,
            defaults=defaults,
        )
        target_changed = record.target_ui_project_id != target_ui_project.id

        if created:
            return record, True, False

        updated_fields = ["updated_by", "updated_at"]
        if record.target_ui_project_id != target_ui_project.id:
            record.target_ui_project = target_ui_project
            if record.generated_test_case_id and record.generated_test_case.project_id != target_ui_project.id:
                record.generated_test_case = None
                updated_fields.append("generated_test_case")
            updated_fields.append("target_ui_project")
        if record.engine != engine:
            record.engine = engine
            updated_fields.append("engine")
        record.updated_by = user
        record.save(update_fields=updated_fields)
        return record, False, target_changed

    @classmethod
    def generate_record(cls, source_testcase, target_ui_project, engine, user):
        cls.validate_target_ui_project(source_testcase, target_ui_project)
        record, _, target_changed = cls.get_or_create_record(source_testcase, target_ui_project, engine, user)
        element_catalog = build_element_catalog(target_ui_project)

        record.status = "generating"
        record.updated_by = user
        record.save(update_fields=["status", "updated_by", "updated_at"])

        try:
            payload = TestRunUiAutomationService.build_candidate_payload(
                source_testcase,
                element_catalog,
                allow_fallback=False,
            )
        except Exception as exc:
            record.status = "failed"
            record.name = source_testcase.title
            record.description = source_testcase.description or ""
            record.preconditions = source_testcase.preconditions or ""
            record.priority = map_priority(source_testcase.priority)
            record.source_snapshot = build_source_snapshot(source_testcase)
            record.steps_data = []
            record.step_count = 0
            record.review_comment = ""
            record.generation_source = "ai"
            record.generation_error = str(exc)
            record.reviewed_by = None
            record.reviewed_at = None
            record.updated_by = user
            record.save(
                update_fields=[
                    "status",
                    "name",
                    "description",
                    "preconditions",
                    "priority",
                    "source_snapshot",
                    "steps_data",
                    "step_count",
                    "review_comment",
                    "generation_source",
                    "generation_error",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_by",
                    "updated_at",
                ]
            )
            raise ValueError(str(exc)) from exc

        update_fields = [
            "target_ui_project",
            "engine",
            "status",
            "name",
            "description",
            "preconditions",
            "priority",
            "source_snapshot",
            "steps_data",
            "step_count",
            "review_comment",
            "generation_source",
            "generation_error",
            "reviewed_by",
            "reviewed_at",
            "updated_by",
            "updated_at",
        ]

        record.target_ui_project = target_ui_project
        record.engine = engine
        record.status = "pending_review"
        record.name = payload["name"]
        record.description = payload["description"]
        record.preconditions = payload["preconditions"]
        record.priority = payload["priority"]
        record.source_snapshot = payload["source_snapshot"]
        record.steps_data = payload["steps_data"]
        record.step_count = payload["step_count"]
        record.review_comment = ""
        record.generation_source = payload["generation_source"]
        record.generation_error = payload["generation_error"]
        record.reviewed_by = None
        record.reviewed_at = None
        record.updated_by = user

        if target_changed and record.generated_test_case_id and record.generated_test_case.project_id != target_ui_project.id:
            record.generated_test_case = None
            update_fields.append("generated_test_case")

        record.save(update_fields=update_fields)
        return record

    @classmethod
    def approve_record(cls, record, reviewer):
        if record.target_ui_project_id is None:
            raise ValueError("候选用例未绑定目标 UI 项目")
        cls.validate_target_ui_project(record.source_testcase, record.target_ui_project)

        steps_data = normalize_candidate_steps(record.steps_data, build_element_catalog(record.target_ui_project))
        if not steps_data:
            raise ValueError("候选用例没有可执行步骤，请先补充步骤")

        with transaction.atomic():
            ui_case = record.generated_test_case
            if ui_case and ui_case.project_id != record.target_ui_project_id:
                ui_case = None

            if ui_case is None:
                ui_case = UiAutomationTestCase.objects.create(
                    project=record.target_ui_project,
                    name=record.name,
                    description=record.description,
                    status="ready",
                    priority=record.priority if record.priority in {"high", "medium", "low"} else "medium",
                    created_by=reviewer,
                )
                log_operation("create", "test_case", ui_case.id, ui_case.name, reviewer)
            else:
                ui_case.name = record.name
                ui_case.description = record.description
                ui_case.status = "ready"
                ui_case.priority = record.priority if record.priority in {"high", "medium", "low"} else "medium"
                ui_case.save(update_fields=["name", "description", "status", "priority", "updated_at"])
                log_operation("edit", "test_case", ui_case.id, ui_case.name, reviewer)

            ui_case.steps.all().delete()
            step_instances = []
            for index, step in enumerate(steps_data, start=1):
                step_instances.append(
                    UiAutomationTestCaseStep(
                        test_case=ui_case,
                        step_number=index,
                        action_type=step["action_type"],
                        element_id=step["element_id"],
                        input_value=step.get("input_value", ""),
                        wait_time=normalize_wait_time(step.get("wait_time", 1000)),
                        assert_type=step.get("assert_type", ""),
                        assert_value=step.get("assert_value", ""),
                        description=step.get("description", ""),
                    )
                )
            UiAutomationTestCaseStep.objects.bulk_create(step_instances)

            record.steps_data = steps_data
            record.step_count = len(steps_data)
            record.status = "approved"
            record.generated_test_case = ui_case
            record.reviewed_by = reviewer
            record.reviewed_at = timezone.now()
            record.updated_by = reviewer
            record.save(
                update_fields=[
                    "steps_data",
                    "step_count",
                    "status",
                    "generated_test_case",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_by",
                    "updated_at",
                ]
            )

        return record

    @classmethod
    def reject_record(cls, record, reviewer, review_comment=""):
        record.status = "rejected"
        record.review_comment = review_comment or record.review_comment
        record.reviewed_by = reviewer
        record.reviewed_at = timezone.now()
        record.updated_by = reviewer
        record.save(
            update_fields=["status", "review_comment", "reviewed_by", "reviewed_at", "updated_by", "updated_at"]
        )
        return record

    @classmethod
    def mark_record_pending_if_needed(cls, record):
        if record.status != "approved":
            return record
        record.status = "pending_review"
        record.reviewed_by = None
        record.reviewed_at = None
        record.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return record


class TestRunUiAutomationService:
    @classmethod
    def auto_match_ui_project(cls, test_run):
        exact = UiProject.objects.filter(name=test_run.project.name).first()
        if exact:
            return exact

        normalized_source = normalize_text(test_run.project.name)
        best_match = None
        best_score = 0
        for ui_project in UiProject.objects.all().only("id", "name"):
            score = SequenceMatcher(None, normalized_source, normalize_text(ui_project.name)).ratio()
            if score > best_score:
                best_score = score
                best_match = ui_project
        return best_match if best_score >= 0.8 else None

    @classmethod
    def get_or_create_batch(cls, test_run, target_ui_project, engine, user):
        defaults = {
            "target_ui_project": target_ui_project,
            "engine": engine,
            "created_by": user,
            "updated_by": user,
        }
        batch, created = TestRunUiAutomationBatch.objects.get_or_create(test_run=test_run, defaults=defaults)
        target_changed = batch.target_ui_project_id != target_ui_project.id

        if created:
            return batch, True, False

        updated_fields = ["updated_by", "updated_at"]
        if batch.target_ui_project_id != target_ui_project.id:
            batch.target_ui_project = target_ui_project
            batch.generated_suite = None
            batch.last_execution = None
            updated_fields.extend(["target_ui_project", "generated_suite", "last_execution"])
        if batch.engine != engine:
            batch.engine = engine
            updated_fields.append("engine")
        batch.updated_by = user
        batch.save(update_fields=updated_fields)

        return batch, False, target_changed

    @classmethod
    def _call_writer_model(cls, source_snapshot, element_catalog):
        config = AIModelConfig.objects.filter(role="writer", is_active=True).order_by("-updated_at", "-id").first()
        if not config:
            raise RuntimeError("未配置启用中的编写模型，已切换为规则生成")

        payload = {
            "manual_testcase": source_snapshot,
            "available_elements": [
                {
                    "name": element["name"],
                    "page": element["page"],
                    "description": element["description"],
                    "element_type": element["element_type"],
                }
                for element in element_catalog[:300]
            ],
            "notes": {
                "engine": "playwright_or_selenium",
                "allowed_actions": sorted(ACTION_TYPE_CHOICES),
                "allowed_assert_types": sorted(ASSERT_TYPE_CHOICES),
            },
        }
        messages = [
            {"role": "system", "content": DEFAULT_UI_AUTOMATION_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        response = async_to_sync(AIModelService.call_openai_compatible_api)(config, messages)
        return extract_json_object(response["choices"][0]["message"]["content"])

    @classmethod
    def build_candidate_payload(cls, source_case, element_catalog, allow_fallback=True):
        source_snapshot = build_source_snapshot(source_case)

        try:
            ai_payload = cls._call_writer_model(source_snapshot, element_catalog)
            steps = normalize_candidate_steps(ai_payload.get("steps", []), element_catalog)
            if not steps:
                raise ValueError("AI 生成结果中没有可用步骤")
            return {
                "name": (ai_payload.get("name") or source_case.title).strip(),
                "description": (ai_payload.get("description") or source_case.description or "").strip(),
                "preconditions": (ai_payload.get("preconditions") or source_case.preconditions or "").strip(),
                "priority": ai_payload.get("priority") if ai_payload.get("priority") in {"high", "medium", "low"} else map_priority(source_case.priority),
                "source_snapshot": source_snapshot,
                "steps_data": steps,
                "step_count": len(steps),
                "generation_source": "ai",
                "generation_error": "",
            }
        except Exception as exc:
            if not allow_fallback:
                raise RuntimeError(f"AI 生成 UI 自动化用例失败：{exc}") from exc
            logger.warning("Falling back to heuristic UI automation generation for testcase %s: %s", source_case.id, exc)
            heuristic_steps = build_heuristic_steps(source_snapshot, element_catalog)
            return {
                "name": source_case.title,
                "description": source_case.description or "",
                "preconditions": source_case.preconditions or "",
                "priority": map_priority(source_case.priority),
                "source_snapshot": source_snapshot,
                "steps_data": heuristic_steps,
                "step_count": len(heuristic_steps),
                "generation_source": "heuristic",
                "generation_error": str(exc),
            }

    @classmethod
    def generate_candidates(cls, test_run, target_ui_project, engine, user):
        batch, _, target_changed = cls.get_or_create_batch(test_run, target_ui_project, engine, user)
        element_catalog = build_element_catalog(target_ui_project)

        batch.status = "generating"
        batch.updated_by = user
        batch.save(update_fields=["status", "updated_by", "updated_at"])

        run_cases = test_run.run_cases.select_related("testcase").prefetch_related("testcase__step_details").order_by("id")
        existing_candidates = {
            candidate.run_case_id: candidate
            for candidate in batch.candidates.select_related("generated_test_case", "run_case").all()
        }

        summary = {
            "total_source_cases": run_cases.count(),
            "generated_or_updated": 0,
            "skipped_approved": 0,
            "ai_count": 0,
            "heuristic_count": 0,
            "warning_count": 0,
            "generated_at": timezone.now().isoformat(),
        }

        with transaction.atomic():
            for run_case in run_cases:
                existing_candidate = existing_candidates.get(run_case.id)

                if (
                    existing_candidate
                    and existing_candidate.review_status == "approved"
                    and existing_candidate.generated_test_case_id
                    and not target_changed
                ):
                    summary["skipped_approved"] += 1
                    continue

                payload = cls.build_candidate_payload(run_case.testcase, element_catalog)
                if payload["generation_source"] == "ai":
                    summary["ai_count"] += 1
                else:
                    summary["heuristic_count"] += 1
                if payload["generation_error"]:
                    summary["warning_count"] += 1

                defaults = {
                    **payload,
                    "batch": batch,
                    "run_case": run_case,
                    "review_status": "pending",
                    "review_comment": "",
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "generated_test_case": None,
                }
                if existing_candidate:
                    for field, value in defaults.items():
                        setattr(existing_candidate, field, value)
                    existing_candidate.save()
                else:
                    TestRunUiAutomationCandidate.objects.create(**defaults)

                summary["generated_or_updated"] += 1

            batch.generation_summary = summary
            batch.save(update_fields=["generation_summary", "updated_at"])

        refresh_batch_status(batch)
        return batch

    @classmethod
    def ensure_suite(cls, batch):
        suite = batch.generated_suite
        if suite and suite.project_id == batch.target_ui_project_id:
            expected_name = f"[计划执行#{batch.test_run_id}] {batch.test_run.name}"
            if suite.name != expected_name:
                suite.name = expected_name
                suite.description = f"由测试计划执行批次自动维护。来源执行：{batch.test_run.name}"
                suite.save(update_fields=["name", "description", "updated_at"])
            return suite

        suite = TestSuite.objects.create(
            project=batch.target_ui_project,
            name=f"[计划执行#{batch.test_run_id}] {batch.test_run.name}",
            description=f"由测试计划执行批次自动维护。来源执行：{batch.test_run.name}",
        )
        batch.generated_suite = suite
        batch.save(update_fields=["generated_suite", "updated_at"])
        return suite

    @classmethod
    def approve_candidate(cls, candidate, reviewer):
        batch = candidate.batch
        if batch.target_ui_project_id is None:
            raise ValueError("候选用例未绑定目标 UI 项目")

        steps_data = normalize_candidate_steps(candidate.steps_data, build_element_catalog(batch.target_ui_project))
        if not steps_data:
            raise ValueError("候选用例没有可执行步骤，请先补充步骤")

        with transaction.atomic():
            ui_case = candidate.generated_test_case
            if ui_case and ui_case.project_id != batch.target_ui_project_id:
                ui_case = None

            if ui_case is None:
                ui_case = UiAutomationTestCase.objects.create(
                    project=batch.target_ui_project,
                    name=candidate.name,
                    description=candidate.description,
                    status="ready",
                    priority=candidate.priority if candidate.priority in {"high", "medium", "low"} else "medium",
                    created_by=reviewer,
                )
                log_operation("create", "test_case", ui_case.id, ui_case.name, reviewer)
            else:
                ui_case.name = candidate.name
                ui_case.description = candidate.description
                ui_case.status = "ready"
                ui_case.priority = candidate.priority if candidate.priority in {"high", "medium", "low"} else "medium"
                ui_case.save(update_fields=["name", "description", "status", "priority", "updated_at"])
                log_operation("edit", "test_case", ui_case.id, ui_case.name, reviewer)

            ui_case.steps.all().delete()
            step_instances = []
            for index, step in enumerate(steps_data, start=1):
                step_instances.append(
                    UiAutomationTestCaseStep(
                        test_case=ui_case,
                        step_number=index,
                        action_type=step["action_type"],
                        element_id=step["element_id"],
                        input_value=step.get("input_value", ""),
                        wait_time=normalize_wait_time(step.get("wait_time", 1000)),
                        assert_type=step.get("assert_type", ""),
                        assert_value=step.get("assert_value", ""),
                        description=step.get("description", ""),
                    )
                )
            UiAutomationTestCaseStep.objects.bulk_create(step_instances)

            candidate.steps_data = steps_data
            candidate.step_count = len(steps_data)
            candidate.review_status = "approved"
            candidate.generated_test_case = ui_case
            candidate.reviewed_by = reviewer
            candidate.reviewed_at = timezone.now()
            candidate.save(
                update_fields=[
                    "steps_data",
                    "step_count",
                    "review_status",
                    "generated_test_case",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

        refresh_batch_status(batch)
        return candidate

    @classmethod
    def reject_candidate(cls, candidate, reviewer, review_comment=""):
        candidate.review_status = "rejected"
        candidate.review_comment = review_comment or candidate.review_comment
        candidate.reviewed_by = reviewer
        candidate.reviewed_at = timezone.now()
        candidate.save(update_fields=["review_status", "review_comment", "reviewed_by", "reviewed_at", "updated_at"])
        refresh_batch_status(candidate.batch)
        return candidate

    @classmethod
    def mark_candidate_pending_if_needed(cls, candidate):
        if candidate.review_status != "approved":
            return candidate
        candidate.review_status = "pending"
        candidate.reviewed_by = None
        candidate.reviewed_at = None
        candidate.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "updated_at"])
        refresh_batch_status(candidate.batch)
        return candidate

    @classmethod
    def sync_approved_cases_to_suite(cls, batch):
        approved_candidates = (
            batch.candidates.filter(review_status="approved", generated_test_case__isnull=False)
            .select_related("generated_test_case", "run_case")
            .order_by("run_case__id")
        )
        if not approved_candidates.exists():
            raise ValueError("当前执行下没有已审核通过的 UI 自动化候选用例")

        suite = cls.ensure_suite(batch)
        suite.suite_test_cases.all().delete()
        suite_cases = [
            TestSuiteTestCase(
                test_suite=suite,
                test_case=candidate.generated_test_case,
                order=index,
            )
            for index, candidate in enumerate(approved_candidates, start=1)
        ]
        TestSuiteTestCase.objects.bulk_create(suite_cases)
        return suite

    @classmethod
    def execute_batch(cls, batch, user, browser="chrome", headless=True):
        suite = cls.sync_approved_cases_to_suite(batch)
        suite.execution_status = "running"
        suite.save(update_fields=["execution_status", "updated_at"])

        batch.status = "running"
        batch.updated_by = user
        batch.save(update_fields=["status", "updated_by", "updated_at"])

        def run_suite_task(batch_id, suite_id, engine, browser_name, is_headless, user_obj):
            close_old_connections()
            try:
                local_batch = TestRunUiAutomationBatch.objects.select_related("generated_suite").get(id=batch_id)
                local_suite = TestSuite.objects.get(id=suite_id)
                executor = TestExecutor(
                    test_suite=local_suite,
                    engine=engine,
                    browser=browser_name,
                    headless=is_headless,
                    executed_by=user_obj,
                )
                executor.run()

                update_fields = ["updated_at"]
                if executor.execution:
                    local_batch.last_execution = executor.execution
                    update_fields.append("last_execution")

                if executor.execution and executor.execution.status == "SUCCESS":
                    local_batch.status = "completed"
                else:
                    local_batch.status = "failed"
                update_fields.append("status")
                local_batch.save(update_fields=update_fields)
            except Exception as exc:
                logger.exception("Failed to execute UI automation batch %s: %s", batch_id, exc)
                TestRunUiAutomationBatch.objects.filter(id=batch_id).update(status="failed", updated_at=timezone.now())
            finally:
                close_old_connections()

        thread = threading.Thread(
            target=run_suite_task,
            args=(batch.id, suite.id, batch.engine, browser, headless, user),
            daemon=True,
        )
        thread.start()

        log_operation("run", "suite", suite.id, suite.name, user)

        return {
            "message": "已开始执行已审核的 UI 自动化用例",
            "suite_id": suite.id,
            "suite_name": suite.name,
            "engine": batch.engine,
            "browser": browser,
            "headless": headless,
        }
