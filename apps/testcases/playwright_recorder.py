import json
import os
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import urlopen

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Max
from django.utils import timezone

from .models import PlaywrightRecordingSession, PlaywrightRecordingStep
from .snapshot_sanitizer import (
    normalize_snapshot_inline_text,
    remove_private_use_characters,
    sanitize_recording_payload,
    sanitize_snapshot_content,
)


ALLOWED_BROWSER_TYPES = {'chromium', 'firefox', 'webkit'}
POLL_INTERVAL_SECONDS = 0.6
EMPTY_PAGE_LIMIT = 8
RECORDER_READY_TIMEOUT_SECONDS = 45
LOCALHOST_NAMES = {'localhost', '127.0.0.1', '::1', '0.0.0.0'}
ACTIVE_RECORDING_STATUSES = [
    PlaywrightRecordingSession.STATUS_STARTING,
    PlaywrightRecordingSession.STATUS_RECORDING,
    PlaywrightRecordingSession.STATUS_STOPPING,
]
TERMINAL_RECORDING_STATUSES = {
    PlaywrightRecordingSession.STATUS_COMPLETED,
    PlaywrightRecordingSession.STATUS_FAILED,
}

ACTIVE_RECORDERS = {}
ACTIVE_RECORDERS_LOCK = threading.RLock()
RECORDER_SETTINGS_LOCK = threading.RLock()
RECORDER_SETTINGS_FILENAME = 'playwright-recorder-settings.json'


@dataclass(frozen=True)
class RecorderRuntimeConfig:
    slot: int
    display: str
    cdp_public_port: int
    cdp_internal_port: int
    cdp_host_port: int
    vnc_port: int
    novnc_port: int
    novnc_host_port: int

    def as_metadata(self):
        return {
            'runtime_slot': self.slot,
            'display': self.display,
            'cdp_port': self.cdp_public_port,
            'cdp_internal_port': self.cdp_internal_port,
            'cdp_host_port': self.cdp_host_port,
            'vnc_port': self.vnc_port,
            'novnc_port': self.novnc_port,
            'novnc_host_port': self.novnc_host_port,
        }


class RecordingStartError(RuntimeError):
    pass


RECORDING_SCRIPT = r"""
(() => {
  if (window.__testhubRecordingInstalled) return;
  window.__testhubRecordingInstalled = true;

  const events = [];
  const pendingFillTimers = new Map();
  let lastSignature = '';
  let lastAt = 0;
  const specialKeys = new Set(['Enter', 'Tab', 'Escape', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']);
  const iconFontPrivateUsePattern = /[\uE000-\uF8FF]/g;

  const nowIso = () => new Date().toISOString();
  const trimText = (value, max = 180) => String(value || '').replace(iconFontPrivateUsePattern, '').replace(/\s+/g, ' ').trim().slice(0, max);
  const normalizeContextText = (value, max = 500) => trimText(value, max);
  window.__testhub_recording_setContext = context => {
    window.__testhubRecordingContext = context && typeof context === 'object' ? { ...context } : {};
  };
  const readRecordingContext = () => {
    const context = window.__testhubRecordingContext && typeof window.__testhubRecordingContext === 'object'
      ? window.__testhubRecordingContext
      : {};
    const modulePath = normalizeContextText(context.module_path || context.path || context.system_page_path || context.page_path || '');
    const moduleName = normalizeContextText(context.module_name || context.name || context.system_page_name || context.page_name || '');
    if (!modulePath && !moduleName) return {};
    const payload = {
      context: {
        ...context,
        module_path: modulePath,
        module_name: moduleName,
      },
      recording_scope: {
        ...(context.recording_scope && typeof context.recording_scope === 'object' ? context.recording_scope : {}),
        module_path: modulePath,
        path: modulePath,
        module_name: moduleName,
      },
      system_page_path: modulePath,
      page_menu_path: modulePath,
      menu_path: modulePath,
      module_path: modulePath,
      recording_scope_path: modulePath,
      system_page_name: moduleName,
      page_menu_name: moduleName,
      menu_name: moduleName,
      module_name: moduleName,
    };
    return payload;
  };
  const cssEscape = value => {
    if (window.CSS && typeof window.CSS.escape === 'function') return window.CSS.escape(value);
    return String(value || '').replace(/[^a-zA-Z0-9_-]/g, '\\$&');
  };

  const isVisible = element => {
    if (!element || !(element instanceof Element)) return false;
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style && style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
  };

  const inferRole = element => {
    const explicitRole = element.getAttribute('role');
    if (explicitRole) return explicitRole;
    const tag = element.tagName.toLowerCase();
    const type = (element.getAttribute('type') || '').toLowerCase();
    if (tag === 'a') return 'link';
    if (tag === 'button') return 'button';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'select') return 'combobox';
    if (tag === 'input') {
      if (['button', 'submit', 'reset'].includes(type)) return 'button';
      if (type === 'checkbox') return 'checkbox';
      if (type === 'radio') return 'radio';
      return 'textbox';
    }
    if (element.isContentEditable) return 'textbox';
    return '';
  };

  const elementText = element => {
    const tag = element.tagName.toLowerCase();
    const ariaLabel = element.getAttribute('aria-label');
    const labelledBy = element.getAttribute('aria-labelledby');
    if (ariaLabel) return trimText(ariaLabel);
    if (labelledBy) {
      const label = labelledBy
        .split(/\s+/)
        .map(id => document.getElementById(id)?.innerText || '')
        .join(' ');
      if (trimText(label)) return trimText(label);
    }
    if (element.labels && element.labels.length) {
      const labels = Array.from(element.labels).map(label => label.innerText || '').join(' ');
      if (trimText(labels)) return trimText(labels);
    }
    if (element.getAttribute('placeholder')) return trimText(element.getAttribute('placeholder'));
    if (element.getAttribute('title')) return trimText(element.getAttribute('title'));
    if (element.getAttribute('value') && ['button', 'submit', 'reset'].includes((element.getAttribute('type') || '').toLowerCase())) {
      return trimText(element.getAttribute('value'));
    }
    if (tag === 'select') {
      const selectedText = Array.from(element.selectedOptions || [])
        .map(option => option.label || option.textContent || option.value || '')
        .join(' ');
      return trimText(selectedText || element.getAttribute('name') || element.getAttribute('id') || '');
    }
    return trimText(element.innerText || element.textContent || element.getAttribute('name') || '');
  };

  const cssPath = element => {
    const parts = [];
    let current = element;
    while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body) {
      const tag = current.tagName.toLowerCase();
      if (current.id) {
        parts.unshift(`${tag}#${cssEscape(current.id)}`);
        break;
      }
      let index = 1;
      let sibling = current;
      while ((sibling = sibling.previousElementSibling)) {
        if (sibling.tagName === current.tagName) index += 1;
      }
      parts.unshift(`${tag}:nth-of-type(${index})`);
      current = current.parentElement;
    }
    return parts.length ? parts.join(' > ') : '';
  };

  const xpathOf = element => {
    const parts = [];
    let current = element;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      const tag = current.tagName.toLowerCase();
      let index = 1;
      let sibling = current.previousElementSibling;
      while (sibling) {
        if (sibling.tagName === current.tagName) index += 1;
        sibling = sibling.previousElementSibling;
      }
      parts.unshift(`${tag}[${index}]`);
      current = current.parentElement;
    }
    return parts.length ? `/${parts.join('/')}` : '';
  };

  const locatorValues = element => {
    if (!element || !(element instanceof Element)) return {};
    const tag = element.tagName.toLowerCase();
    const text = elementText(element);
    const classnames = Array.from(element.classList || [])
      .map(item => trimText(item, 120))
      .filter(Boolean);
    const linkText = tag === 'a' ? text : '';
    return {
      id: element.id || '',
      name: element.getAttribute('name') || '',
      classname: classnames[0] || '',
      classnames,
      tagname: tag,
      linktext: linkText,
      partiallinktext: linkText ? linkText.slice(0, 80) : '',
      xpath: xpathOf(element),
      cssselector: cssPath(element),
    };
  };

  const selectorCandidates = element => {
    const tag = element.tagName.toLowerCase();
    const role = inferRole(element);
    const text = elementText(element);
    const locators = locatorValues(element);
    const candidates = [];
    const push = (type, value, priority) => {
      if (!value) return;
      if (candidates.some(item => item.type === type && item.value === value)) return;
      candidates.push({ type, value, priority });
    };

    ['data-testid', 'data-test', 'data-cy', 'data-qa'].forEach(attr => {
      const value = element.getAttribute(attr);
      if (value) push(attr, `[${attr}="${value.replace(/"/g, '\\"')}"]`, 1);
    });
    if (element.id) push('id', `#${cssEscape(element.id)}`, 2);
    if (element.getAttribute('name')) push('name', `${tag}[name="${element.getAttribute('name').replace(/"/g, '\\"')}"]`, 3);
    if (element.getAttribute('placeholder')) {
      push('placeholder', `${tag}[placeholder="${element.getAttribute('placeholder').replace(/"/g, '\\"')}"]`, 4);
    }
    if (role && text) push('role', `role=${role}[name="${text.replace(/"/g, '\\"')}"]`, 5);
    if (text && ['button', 'a'].includes(tag)) push('text', `${tag}:has-text("${text.replace(/"/g, '\\"')}")`, 6);
    push('css', cssPath(element), 9);
    push('by_id', locators.id, 10);
    push('by_name', locators.name, 11);
    push('by_classname', locators.classname, 12);
    push('by_tagname', locators.tagname, 13);
    push('by_linktext', locators.linktext, 14);
    push('by_partiallinktext', locators.partiallinktext, 15);
    push('by_xpath', locators.xpath, 16);
    push('by_cssselector', locators.cssselector, 17);

    return candidates.sort((left, right) => left.priority - right.priority);
  };

  const selectedOptionSummaries = element => Array.from(element.selectedOptions || []).map(option => ({
    value: option.value ?? '',
    label: trimText(option.label || option.textContent || option.value || ''),
    text: trimText(option.textContent || option.label || option.value || ''),
  }));

  const selectDisplayValue = element => selectedOptionSummaries(element)
    .map(option => option.label || option.text || option.value)
    .filter(Boolean);

  const summarizeElement = element => {
    if (!element || !(element instanceof Element)) return {};
    const tag = element.tagName.toLowerCase();
    const type = (element.getAttribute('type') || '').toLowerCase();
    const role = inferRole(element);
    const rect = element.getBoundingClientRect();
    const isPassword = tag === 'input' && type === 'password';
    const selectedOptions = tag === 'select' ? selectedOptionSummaries(element) : [];
    const value = isPassword ? '' : (
      tag === 'select'
        ? selectDisplayValue(element)
        : (element.value ?? '')
    );
    const locators = locatorValues(element);

    return {
      tag,
      tagName: locators.tagname,
      tagname: locators.tagname,
      type,
      role,
      text: elementText(element),
      id: element.id || '',
      name: element.getAttribute('name') || '',
      className: locators.classnames.join(' ').slice(0, 240),
      classname: locators.classname,
      placeholder: element.getAttribute('placeholder') || '',
      ariaLabel: element.getAttribute('aria-label') || '',
      ariaChecked: element.getAttribute('aria-checked') || '',
      ariaPressed: element.getAttribute('aria-pressed') || '',
      ariaSelected: element.getAttribute('aria-selected') || '',
      title: element.getAttribute('title') || '',
      linkText: locators.linktext,
      linktext: locators.linktext,
      partialLinkText: locators.partiallinktext,
      partiallinktext: locators.partiallinktext,
      xpath: locators.xpath,
      cssSelector: locators.cssselector,
      cssselector: locators.cssselector,
      locatorValues: locators,
      value,
      selectedValue: tag === 'select' ? (element.value ?? '') : '',
      selectedOptions,
      checked: Boolean(element.checked),
      disabled: Boolean(element.disabled) || element.getAttribute('aria-disabled') === 'true',
      isPassword,
      rect: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
    };
  };

  const isCheckableType = type => ['checkbox', 'radio'].includes(String(type || '').toLowerCase());

  const controlTypeOf = element => {
    if (!element || !(element instanceof Element)) return '';
    const tag = element.tagName.toLowerCase();
    const type = (element.getAttribute('type') || '').toLowerCase();
    const role = inferRole(element).toLowerCase();
    if (tag === 'input' && isCheckableType(type)) return type;
    if (['checkbox', 'radio', 'switch'].includes(role)) return role === 'switch' ? 'checkbox' : role;
    return '';
  };

  const findLabelControl = element => {
    const label = element instanceof Element ? element.closest('label') : null;
    if (!label) return null;
    if (label.control instanceof Element && isCheckableType(label.control.getAttribute('type'))) return label.control;
    return label.querySelector('input[type="checkbox"],input[type="radio"]');
  };

  const findCheckableControl = element => {
    if (!(element instanceof Element)) return null;
    const direct = element.closest('input[type="checkbox"],input[type="radio"]');
    if (direct) return direct;
    return findLabelControl(element);
  };

  const fallbackClickElement = element => {
    if (!(element instanceof Element)) return null;
    const interactive = element.closest('button,a,input,textarea,select,[role],[contenteditable="true"],[tabindex],label');
    if (interactive) return interactive;
    let current = element;
    while (current && current instanceof Element && current !== document.documentElement) {
      if (isVisible(current) && (elementText(current) || current.id || current.getAttribute('class'))) {
        return current;
      }
      current = current.parentElement;
    }
    return element.closest('body') || element;
  };

  const visibleControlProxy = (control, triggerElement = null) => {
    const candidates = [];
    if (triggerElement instanceof Element) {
      const triggerLabel = triggerElement.closest('label');
      if (triggerLabel) candidates.push(triggerLabel);
      const triggerRole = triggerElement.closest('[role="checkbox"],[role="radio"],[role="switch"],[aria-checked]');
      if (triggerRole) candidates.push(triggerRole);
      const triggerInteractive = triggerElement.closest('button,a,[role],[contenteditable="true"],[tabindex]');
      if (triggerInteractive) candidates.push(triggerInteractive);
    }
    if (control instanceof Element) {
      if (control.labels && control.labels.length) candidates.push(...Array.from(control.labels));
      const controlRole = control.closest('[role="checkbox"],[role="radio"],[role="switch"],[aria-checked]');
      if (controlRole) candidates.push(controlRole);
      const controlLabel = control.closest('label');
      if (controlLabel) candidates.push(controlLabel);
      candidates.push(control);
    }
    return candidates.find(item => item instanceof Element && isVisible(item)) || control || triggerElement;
  };

  const readControlChecked = (control, fallbackElement = null) => {
    if (control instanceof HTMLInputElement && isCheckableType(control.type)) return Boolean(control.checked);
    const element = control instanceof Element ? control : fallbackElement;
    if (!(element instanceof Element)) return false;
    const ariaChecked = String(element.getAttribute('aria-checked') || '').toLowerCase();
    if (ariaChecked === 'true') return true;
    if (['false', 'mixed'].includes(ariaChecked)) return false;
    return Boolean(element.checked);
  };

  const emitCheckable = (control, triggerElement = null, source = 'change') => {
    if (!(control instanceof Element)) return;
    const controlType = controlTypeOf(control);
    if (!controlType) return;
    const recordElement = visibleControlProxy(control, triggerElement);
    if (!(recordElement instanceof Element)) return;
    const checked = readControlChecked(control, recordElement);
    const actionType = controlType === 'radio' ? 'select' : (checked ? 'check' : 'uncheck');
    const controlSummary = summarizeElement(control);
    enqueue(actionType, recordElement, {
      checked,
      controlType,
      control: controlSummary,
      controlSelectors: selectorCandidates(control),
      recordedFrom: source,
      elementOverrides: {
        role: controlType,
        type: controlType,
        checked,
        value: controlSummary.value,
        id: controlSummary.id || summarizeElement(recordElement).id,
        name: controlSummary.name || summarizeElement(recordElement).name,
        locatorValues: controlSummary.locatorValues || summarizeElement(recordElement).locatorValues,
        ariaChecked: String(checked),
      },
    });
  };

  const emitRoleCheckable = (element, source = 'click') => {
    if (!(element instanceof Element)) return;
    const controlType = controlTypeOf(element);
    if (!controlType) return;
    const checked = readControlChecked(element);
    const actionType = controlType === 'radio' ? 'select' : (checked ? 'check' : 'uncheck');
    enqueue(actionType, element, {
      checked,
      controlType,
      controlSelectors: selectorCandidates(element),
      recordedFrom: source,
      elementOverrides: {
        role: controlType,
        type: controlType,
        checked,
        ariaChecked: String(checked),
      },
    });
  };

  const isFillable = element => {
    if (!element || !(element instanceof Element)) return false;
    const tag = element.tagName.toLowerCase();
    const type = (element.getAttribute('type') || '').toLowerCase();
    if (tag === 'textarea' || element.isContentEditable) return true;
    return tag === 'input' && !['button', 'submit', 'reset', 'checkbox', 'radio', 'file'].includes(type);
  };

  const readFillValue = element => {
    if (!element || !(element instanceof Element)) return '';
    if (element.isContentEditable) return element.textContent || '';
    return element.value ?? '';
  };

  const frameSummary = () => {
    const summary = {
      url: window.location.href,
      name: window.name || '',
      isMain: window.self === window.top,
      element: null,
      selectors: [],
    };
    try {
      const frameElement = window.frameElement;
      if (frameElement && frameElement instanceof Element) {
        summary.element = summarizeElement(frameElement);
        summary.selectors = selectorCandidates(frameElement);
      }
    } catch (error) {
      summary.accessError = String(error && error.message ? error.message : error);
    }
    return summary;
  };

  const enqueue = (actionType, element, extra = {}) => {
    if (!element || !isVisible(element)) return;
    const elementOverrides = extra.elementOverrides && typeof extra.elementOverrides === 'object'
      ? extra.elementOverrides
      : {};
    const payloadExtra = { ...extra };
    delete payloadExtra.elementOverrides;
    const baseSelectors = selectorCandidates(element);
    const extraSelectors = Array.isArray(payloadExtra.controlSelectors)
      ? payloadExtra.controlSelectors
      : [];
    const mergedSelectors = [...extraSelectors, ...baseSelectors].filter((item, index, items) => (
      item && item.value && items.findIndex(candidate => (
        candidate && candidate.type === item.type && candidate.value === item.value
      )) === index
    ));
    const payload = {
      action_type: actionType,
      timestamp: nowIso(),
      url: window.location.href,
      title: document.title,
      frame: frameSummary(),
      element: {
        ...summarizeElement(element),
        ...elementOverrides,
      },
      selectors: mergedSelectors,
      ...readRecordingContext(),
      ...payloadExtra,
    };
    const signature = JSON.stringify([
      payload.action_type,
      payload.url,
      payload.element.tag,
      payload.element.type,
      payload.element.role,
      payload.element.id,
      payload.element.name,
      payload.element.text,
      payload.element.cssSelector,
      payload.value,
      payload.checked,
      payload.selectedValue,
      payload.controlType,
      payload.key,
    ]);
    const currentAt = Date.now();
    if (signature === lastSignature && currentAt - lastAt < 200) return;
    lastSignature = signature;
    lastAt = currentAt;
    events.push(payload);
  };

  const emitFill = element => {
    if (!isFillable(element)) return;
    const tag = element.tagName.toLowerCase();
    const type = (element.getAttribute('type') || '').toLowerCase();
    const isPassword = tag === 'input' && type === 'password';
    enqueue('fill', element, { value: isPassword ? '********' : readFillValue(element) });
  };

  const scheduleFill = element => {
    if (!isFillable(element)) return;
    const existingTimer = pendingFillTimers.get(element);
    if (existingTimer) window.clearTimeout(existingTimer);
    const timer = window.setTimeout(() => {
      pendingFillTimers.delete(element);
      emitFill(element);
    }, 450);
    pendingFillTimers.set(element, timer);
  };

  const flushFill = element => {
    const existingTimer = pendingFillTimers.get(element);
    if (existingTimer) window.clearTimeout(existingTimer);
    pendingFillTimers.delete(element);
    emitFill(element);
  };

  const flushPendingFills = () => {
    Array.from(pendingFillTimers.keys()).forEach(flushFill);
  };

  document.addEventListener('click', event => {
    flushPendingFills();
    const target = event.target instanceof Element ? event.target : null;
    const nativeControl = target ? findCheckableControl(target) : null;
    if (nativeControl) {
      window.setTimeout(() => emitCheckable(nativeControl, target, 'click'), 0);
      return;
    }

    const roleControl = target
      ? target.closest('[role="checkbox"],[role="radio"],[role="switch"],[aria-checked]')
      : null;
    if (roleControl && controlTypeOf(roleControl)) {
      window.setTimeout(() => emitRoleCheckable(roleControl, 'click'), 0);
      return;
    }

    const element = target ? fallbackClickElement(target) : null;
    if (element) enqueue('click', element);
  }, true);

  document.addEventListener('change', event => {
    const element = event.target;
    if (!(element instanceof Element)) return;
    const tag = element.tagName.toLowerCase();
    const type = (element.getAttribute('type') || '').toLowerCase();
    if (tag === 'select') {
      enqueue('select', element, {
        value: selectDisplayValue(element),
        selectedValue: element.value ?? '',
        selectedOptions: selectedOptionSummaries(element),
      });
    } else if (tag === 'input' && ['checkbox', 'radio'].includes(type)) {
      emitCheckable(element, event.target, 'change');
    } else if (isFillable(element)) {
      flushFill(element);
    }
  }, true);

  document.addEventListener('input', event => {
    const element = event.target;
    if (element instanceof Element) scheduleFill(element);
  }, true);

  document.addEventListener('keydown', event => {
    if (!specialKeys.has(event.key)) return;
    const element = event.target instanceof Element
      ? event.target.closest('button,a,input,textarea,select,[role],[contenteditable="true"],[tabindex]') || event.target
      : null;
    if (element) {
      if (isFillable(element)) flushFill(element);
      enqueue('press', element, { key: event.key });
    }
  }, true);

  window.__testhub_recording_drainEvents = (flushPending = false) => {
    if (flushPending) flushPendingFills();
    return events.splice(0, events.length);
  };
})();
"""


DOM_SNAPSHOT_SCRIPT = r"""
(() => {
  const selector = 'a,button,input,textarea,select,[role],[contenteditable="true"],[tabindex]:not([tabindex="-1"])';
  const iconFontPrivateUsePattern = /[\uE000-\uF8FF]/g;
  const trimText = (value, max = 160) => String(value || '').replace(iconFontPrivateUsePattern, '').replace(/\s+/g, ' ').trim().slice(0, max);
  const isVisible = element => {
    if (!element || !(element instanceof Element)) return false;
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style && style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
  };
  const inferRole = element => {
    const explicitRole = element.getAttribute('role');
    if (explicitRole) return explicitRole;
    const tag = element.tagName.toLowerCase();
    const type = (element.getAttribute('type') || '').toLowerCase();
    if (tag === 'a') return 'link';
    if (tag === 'button') return 'button';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'select') return 'combobox';
    if (tag === 'input') {
      if (['button', 'submit', 'reset'].includes(type)) return 'button';
      if (type === 'checkbox') return 'checkbox';
      if (type === 'radio') return 'radio';
      return 'textbox';
    }
    if (element.isContentEditable) return 'textbox';
    return tag;
  };
  const textOf = element => {
    if (element.getAttribute('aria-label')) return trimText(element.getAttribute('aria-label'));
    if (element.labels && element.labels.length) {
      const labels = Array.from(element.labels).map(label => label.innerText || '').join(' ');
      if (trimText(labels)) return trimText(labels);
    }
    return trimText(
      element.getAttribute('placeholder') ||
      element.getAttribute('title') ||
      element.innerText ||
      element.textContent ||
      element.getAttribute('name') ||
      element.getAttribute('id') ||
      ''
    );
  };
  return Array.from(document.querySelectorAll(selector))
    .filter(isVisible)
    .slice(0, 500)
    .map((element, index) => ({
      ref: `recorded-${index + 1}`,
      role: inferRole(element),
      text: textOf(element),
      tag: element.tagName.toLowerCase(),
      type: (element.getAttribute('type') || '').toLowerCase(),
      id: element.getAttribute('id') || '',
      name: element.getAttribute('name') || '',
      placeholder: element.getAttribute('placeholder') || '',
      checked: Boolean(element.checked),
      disabled: Boolean(element.disabled),
    }));
})();
"""


def normalize_browser_type(browser_type):
    normalized = str(browser_type or 'chromium').strip().lower()
    return normalized if normalized in ALLOWED_BROWSER_TYPES else 'chromium'


def normalize_target_url(raw_url):
    target_url = str(raw_url or '').strip()
    if not target_url:
        raise ValueError('Target URL is required')

    parsed = urlparse(target_url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValueError('Target URL must start with http:// or https://')
    return target_url


def parse_recorder_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'y', 'on')


def get_recorder_cdp_port():
    try:
        return int(os.environ.get('PLAYWRIGHT_RECORDER_CDP_PORT', '9222'))
    except (TypeError, ValueError):
        return 9222


def get_recorder_cdp_internal_port():
    try:
        return int(os.environ.get('PLAYWRIGHT_RECORDER_CDP_INTERNAL_PORT', '9333'))
    except (TypeError, ValueError):
        return 9333


def get_recorder_int_env(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_recorder_optional_int_env(name):
    value = os.environ.get(name)
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_recorder_cdp_host_port():
    return get_recorder_int_env('PLAYWRIGHT_RECORDER_CDP_HOST_PORT', get_recorder_cdp_port())


def get_recorder_novnc_host_port():
    return get_recorder_int_env('PLAYWRIGHT_RECORDER_NOVNC_HOST_PORT', 46080)


def get_recorder_vnc_port():
    return get_recorder_int_env('PLAYWRIGHT_RECORDER_VNC_PORT', 5900)


def get_recorder_novnc_port():
    return get_recorder_int_env('PLAYWRIGHT_RECORDER_NOVNC_PORT', 6080)


def get_recorder_max_sessions_default():
    return max(1, get_recorder_int_env('PLAYWRIGHT_RECORDER_MAX_SESSIONS', 5))


def get_recorder_settings_path():
    configured = str(os.environ.get('PLAYWRIGHT_RECORDER_SETTINGS_FILE') or '').strip()
    if configured:
        return configured
    return os.path.join(str(settings.BASE_DIR), 'data', RECORDER_SETTINGS_FILENAME)


def load_recorder_runtime_settings():
    path = get_recorder_settings_path()
    with RECORDER_SETTINGS_LOCK:
        try:
            with open(path, 'r', encoding='utf-8') as settings_file:
                data = json.load(settings_file)
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except Exception:
            return {}


def save_recorder_runtime_settings(data):
    path = get_recorder_settings_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    payload = data if isinstance(data, dict) else {}
    tmp_path = f'{path}.tmp'
    with RECORDER_SETTINGS_LOCK:
        with open(tmp_path, 'w', encoding='utf-8') as settings_file:
            json.dump(payload, settings_file, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    return payload


def get_recorder_max_sessions_override():
    value = load_recorder_runtime_settings().get('max_sessions')
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return None


def get_recorder_range_capacity(start_name, end_name, start_default):
    end = get_recorder_optional_int_env(end_name)
    if end is None:
        return None
    start = get_recorder_int_env(start_name, start_default)
    return max(0, end - start + 1)


def get_recorder_max_session_capacity():
    capacities = [
        get_recorder_range_capacity('PLAYWRIGHT_RECORDER_CDP_PORT', 'PLAYWRIGHT_RECORDER_CDP_PORT_END', get_recorder_cdp_port()),
        get_recorder_range_capacity('PLAYWRIGHT_RECORDER_CDP_HOST_PORT', 'PLAYWRIGHT_RECORDER_CDP_HOST_PORT_END', get_recorder_cdp_host_port()),
        get_recorder_range_capacity('PLAYWRIGHT_RECORDER_NOVNC_PORT', 'PLAYWRIGHT_RECORDER_NOVNC_PORT_END', get_recorder_novnc_port()),
        get_recorder_range_capacity('PLAYWRIGHT_RECORDER_NOVNC_HOST_PORT', 'PLAYWRIGHT_RECORDER_NOVNC_HOST_PORT_END', get_recorder_novnc_host_port()),
    ]
    capacities = [item for item in capacities if item is not None and item > 0]
    return min(capacities) if capacities else None


def get_recorder_max_sessions():
    configured = get_recorder_max_sessions_override()
    max_sessions = configured if configured is not None else get_recorder_max_sessions_default()
    capacity = get_recorder_max_session_capacity()
    if capacity:
        max_sessions = min(max_sessions, capacity)
    return max(1, max_sessions)


def set_recorder_max_sessions(value):
    max_sessions = max(1, int(value))
    capacity = get_recorder_max_session_capacity()
    if capacity and max_sessions > capacity:
        raise ValueError(f'并发录制数量不能超过端口容量 {capacity}')

    settings_data = load_recorder_runtime_settings()
    settings_data['max_sessions'] = max_sessions
    save_recorder_runtime_settings(settings_data)
    os.environ['PLAYWRIGHT_RECORDER_MAX_SESSIONS'] = str(max_sessions)
    return get_recorder_max_sessions()


def get_recorder_max_sessions_config():
    override = get_recorder_max_sessions_override()
    capacity = get_recorder_max_session_capacity()
    return {
        'max_sessions': get_recorder_max_sessions(),
        'configured_max_sessions': override,
        'default_max_sessions': get_recorder_max_sessions_default(),
        'capacity': capacity,
        'source': 'runtime' if override is not None else 'environment',
        'settings_file': get_recorder_settings_path(),
    }


def replace_origin_port(origin, port):
    if port is None:
        return str(origin or '').rstrip('/')

    parsed = urlparse(str(origin or '').strip())
    scheme = parsed.scheme or 'http'
    host = parsed.hostname or 'localhost'
    if ':' in host and not host.startswith('['):
        host = f'[{host}]'
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f'{auth}:{parsed.password}'
        host = f'{auth}@{host}'
    return urlunparse((scheme, f'{host}:{int(port)}', '', '', '', '')).rstrip('/')


def get_recorder_devtools_external_origin(host_port=None):
    configured = str(os.environ.get('PLAYWRIGHT_RECORDER_DEVTOOLS_EXTERNAL_ORIGIN') or '').strip()
    if configured:
        return replace_origin_port(configured, host_port) if host_port is not None else configured.rstrip('/')

    host = str(os.environ.get('PLAYWRIGHT_RECORDER_DEVTOOLS_HOST') or 'localhost').strip() or 'localhost'
    port = str(host_port or get_recorder_cdp_host_port()).strip()
    return f'http://{host}:{port}'.rstrip('/')


def get_recorder_localhost_rewrite_host():
    return str(os.environ.get('PLAYWRIGHT_RECORDER_LOCALHOST_REWRITE_HOST') or '').strip()


def get_recorder_novnc_external_origin(host_port=None):
    configured = str(os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_EXTERNAL_ORIGIN') or '').strip()
    if configured:
        return replace_origin_port(configured, host_port) if host_port is not None else configured.rstrip('/')

    host = str(os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_HOST') or 'localhost').strip() or 'localhost'
    port = str(host_port or get_recorder_novnc_host_port()).strip()
    return f'http://{host}:{port}'.rstrip('/')


def get_recorder_novnc_websocket_path():
    path = str(os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_PATH') or 'websockify').strip()
    return path.strip('/') or 'websockify'


def get_recorder_xvfb_screen_spec():
    return str(os.environ.get('PLAYWRIGHT_RECORDER_XVFB_SCREEN') or '1920x1080x24').strip() or '1920x1080x24'


def get_recorder_xvfb_display():
    return str(os.environ.get('PLAYWRIGHT_RECORDER_XVFB_DISPLAY') or ':99').strip() or ':99'


def get_recorder_initial_navigation_timeout():
    return get_recorder_int_env('PLAYWRIGHT_RECORDER_INITIAL_NAVIGATION_TIMEOUT', 30000)


def get_recorder_start_timeout():
    return get_recorder_int_env('PLAYWRIGHT_RECORDER_READY_TIMEOUT', RECORDER_READY_TIMEOUT_SECONDS)


def get_recorder_chromium_launch_timeout():
    return get_recorder_int_env('PLAYWRIGHT_RECORDER_CHROMIUM_LAUNCH_TIMEOUT', 30000)


def get_recorder_desktop_ready_timeout():
    return get_recorder_int_env('PLAYWRIGHT_RECORDER_DESKTOP_READY_TIMEOUT', 8)


def should_ignore_https_errors():
    return parse_recorder_bool(os.environ.get('PLAYWRIGHT_RECORDER_IGNORE_HTTPS_ERRORS'), default=True)


def get_recorder_screen_size():
    screen_spec = get_recorder_xvfb_screen_spec()
    match = re.match(r'^\s*(\d+)x(\d+)(?:x\d+)?\s*$', screen_spec)
    if not match:
        return 1920, 1080
    return int(match.group(1)), int(match.group(2))


def build_recorder_desktop_env(display):
    env = dict(os.environ)
    if display:
        env['DISPLAY'] = display
    locale = env.get('LANG') or os.environ.get('LANG') or 'C.UTF-8'
    env.setdefault('LANG', locale)
    env.setdefault('GTK_IM_MODULE', 'fcitx')
    env.setdefault('QT_IM_MODULE', 'fcitx')
    env.setdefault('XMODIFIERS', '@im=fcitx')
    env.setdefault('INPUT_METHOD', 'fcitx')
    env.setdefault('LC_CTYPE', locale)
    return env


def build_recorder_novnc_url(runtime_config=None):
    host_port = runtime_config.novnc_host_port if runtime_config else None
    origin = get_recorder_novnc_external_origin(host_port=host_port)
    parsed_origin = urlparse(origin)
    scheme = (parsed_origin.scheme or 'http').lower()
    host = parsed_origin.hostname or 'localhost'
    port = parsed_origin.port or (443 if scheme == 'https' else 80)
    resize_mode = str(os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_RESIZE') or 'scale').strip() or 'scale'
    query = urlencode({
        'autoconnect': '1',
        'host': host,
        'port': str(port),
        'path': get_recorder_novnc_websocket_path(),
        'encrypt': '1' if scheme == 'https' else '0',
        'resize': resize_mode,
        'quality': str(os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_QUALITY') or '8'),
        'compression': str(os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_COMPRESSION') or '2'),
    })
    return f'{origin}/vnc.html?{query}'


def rewrite_localhost_target_url_for_recorder(target_url):
    rewrite_host = get_recorder_localhost_rewrite_host()
    if not rewrite_host:
        return target_url

    parsed = urlparse(target_url)
    if (parsed.hostname or '').lower() not in LOCALHOST_NAMES:
        return target_url

    netloc = rewrite_host
    if parsed.port:
        netloc = f'{netloc}:{parsed.port}'
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f'{auth}:{parsed.password}'
        netloc = f'{auth}@{netloc}'

    return urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))


def is_localhost_url(target_url):
    parsed = urlparse(target_url)
    return (parsed.hostname or '').lower() in LOCALHOST_NAMES


def get_url_port(parsed_url):
    if parsed_url.port:
        return parsed_url.port
    if parsed_url.scheme == 'https':
        return 443
    return 80


def build_url_with_host_port(target_url, host, port):
    parsed = urlparse(target_url)
    netloc = host
    if port:
        netloc = f'{host}:{port}'
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f'{auth}:{parsed.password}'
        netloc = f'{auth}@{netloc}'
    return urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))


def restore_recorded_localhost_url(recorded_url, original_target_url, browser_target_url):
    if not recorded_url or not original_target_url or not browser_target_url:
        return recorded_url
    original = urlparse(original_target_url)
    browser = urlparse(browser_target_url)
    recorded = urlparse(recorded_url)
    if not browser.netloc or recorded.netloc != browser.netloc:
        return recorded_url
    return urlunparse((
        recorded.scheme,
        original.netloc,
        recorded.path,
        recorded.params,
        recorded.query,
        recorded.fragment,
    ))


def wait_for_tcp_port(host, port, timeout=8):
    deadline = time.time() + max(0.1, timeout)
    last_error = ''
    while time.time() < deadline:
        try:
            with socket.create_connection((host, int(port)), timeout=1):
                return True, ''
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.15)
    return False, last_error


def validate_recorder_websocket_endpoint(host, port, path=None, timeout=8):
    path = '/' + (path or get_recorder_novnc_websocket_path()).strip('/')
    deadline = time.time() + max(0.1, timeout)
    request = (
        f'GET {path} HTTP/1.1\r\n'
        f'Host: {host}:{port}\r\n'
        'Upgrade: websocket\r\n'
        'Connection: Upgrade\r\n'
        'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n'
        'Sec-WebSocket-Version: 13\r\n'
        '\r\n'
    ).encode('ascii')
    last_error = ''

    while time.time() < deadline:
        try:
            with socket.create_connection((host, int(port)), timeout=1.5) as ws_socket:
                ws_socket.settimeout(1.5)
                ws_socket.sendall(request)
                response = ws_socket.recv(256).decode('iso-8859-1', errors='replace')
                if response.startswith('HTTP/1.1 101') or response.startswith('HTTP/1.0 101'):
                    return True, ''
                first_line = response.splitlines()[0] if response.splitlines() else response.strip()
                last_error = first_line or 'empty websocket handshake response'
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.15)

    return False, last_error


def probe_target_url_connectivity(target_url, timeout=3):
    parsed = urlparse(target_url)
    host = parsed.hostname
    if not host:
        return {
            'ok': False,
            'host': '',
            'port': None,
            'error': 'target url has no host',
        }

    port = get_url_port(parsed)
    started_at = time.time()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return {
                'ok': True,
                'host': host,
                'port': port,
                'elapsed_ms': int((time.time() - started_at) * 1000),
            }
    except Exception as exc:
        return {
            'ok': False,
            'host': host,
            'port': port,
            'elapsed_ms': int((time.time() - started_at) * 1000),
            'error': str(exc),
        }


class TcpPortForwarder:
    def __init__(self, listen_host, listen_port, target_host, target_port):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.error = ''
        self.server_socket = None
        self.client_sockets = set()
        self.client_lock = threading.Lock()
        self.thread = threading.Thread(
            target=self._serve,
            name=f'playwright-recorder-cdp-proxy-{listen_port}',
            daemon=True,
        )

    def start(self):
        self.thread.start()
        self.ready_event.wait(timeout=2)
        if self.error:
            raise RecordingStartError(self.error)

    def stop(self):
        self.stop_event.set()
        try:
            if self.server_socket:
                self.server_socket.close()
        except Exception:
            pass
        with self.client_lock:
            clients = list(self.client_sockets)
        for client in clients:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass
        self.thread.join(timeout=2)

    def _serve(self):
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.listen_host, self.listen_port))
            self.listen_port = server.getsockname()[1]
            server.listen(64)
            server.settimeout(0.5)
            self.server_socket = server
            self.ready_event.set()

            while not self.stop_event.is_set():
                try:
                    client_socket, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    name=f'playwright-recorder-cdp-client-{self.listen_port}',
                    daemon=True,
                ).start()
        except Exception as exc:
            self.error = str(exc)
            self.ready_event.set()
        finally:
            try:
                if self.server_socket:
                    self.server_socket.close()
            except Exception:
                pass

    def _handle_client(self, client_socket):
        target_socket = None
        with self.client_lock:
            self.client_sockets.add(client_socket)
        try:
            target_socket = socket.create_connection(
                (self.target_host, self.target_port),
                timeout=5,
            )
            with self.client_lock:
                self.client_sockets.add(target_socket)
            client_socket.settimeout(1)
            target_socket.settimeout(1)
            done_event = threading.Event()

            left = threading.Thread(
                target=self._pipe,
                args=(client_socket, target_socket, done_event),
                daemon=True,
            )
            right = threading.Thread(
                target=self._pipe,
                args=(target_socket, client_socket, done_event),
                daemon=True,
            )
            left.start()
            right.start()
            while not done_event.is_set() and (left.is_alive() or right.is_alive()):
                time.sleep(0.1)
            for current_socket in (client_socket, target_socket):
                try:
                    current_socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
            left.join(timeout=1)
            right.join(timeout=1)
        except Exception:
            pass
        finally:
            for current_socket in (client_socket, target_socket):
                if current_socket is None:
                    continue
                try:
                    current_socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    current_socket.close()
                except Exception:
                    pass
                with self.client_lock:
                    self.client_sockets.discard(current_socket)

    def _pipe(self, source, target, done_event):
        try:
            while not self.stop_event.is_set() and not done_event.is_set():
                try:
                    chunk = source.recv(65536)
                except socket.timeout:
                    continue
                except Exception:
                    break
                if not chunk:
                    break
                try:
                    target.sendall(chunk)
                except Exception:
                    break
        finally:
            done_event.set()


def has_active_recording_session(exclude_session_id=None):
    queryset = PlaywrightRecordingSession.objects.filter(status__in=ACTIVE_RECORDING_STATUSES)
    if exclude_session_id:
        queryset = queryset.exclude(session_id=exclude_session_id)
    return queryset.exists()


def has_active_in_memory_recorder(exclude_session_id=None):
    with ACTIVE_RECORDERS_LOCK:
        return any(
            session_id != exclude_session_id and runner.is_alive()
            for session_id, runner in ACTIVE_RECORDERS.items()
        )


def can_cleanup_orphan_recorder_processes(exclude_session_id=None):
    return (
        not has_active_in_memory_recorder(exclude_session_id=exclude_session_id)
        and not has_active_recording_session(exclude_session_id=exclude_session_id)
    )


def start_recording_session(session):
    with ACTIVE_RECORDERS_LOCK:
        dead_ids = [session_id for session_id, runner in ACTIVE_RECORDERS.items() if not runner.is_alive()]
        for session_id in dead_ids:
            ACTIVE_RECORDERS.pop(session_id, None)

        cleanup_stale_recording_sessions(exclude_session_ids={session.session_id})
        if can_cleanup_orphan_recorder_processes(exclude_session_id=session.session_id):
            cleanup_orphan_recorder_processes()

        runtime_config = allocate_recorder_runtime_config()
        runner = PlaywrightRecorder(session.session_id, runtime_config)
        ACTIVE_RECORDERS[session.session_id] = runner
        runner.start()

    if not runner.wait_until_ready(timeout=get_recorder_start_timeout()):
        runner.stop()
        runner.join(timeout=12)
        with ACTIVE_RECORDERS_LOCK:
            current = ACTIVE_RECORDERS.get(session.session_id)
            if current is runner:
                ACTIVE_RECORDERS.pop(session.session_id, None)
        if runner.is_alive() and can_cleanup_orphan_recorder_processes(exclude_session_id=session.session_id):
            cleanup_orphan_recorder_processes()
        runner._fail_session('Controlled browser did not become ready in time')
        raise RecordingStartError('Controlled browser did not become ready in time')

    if runner.start_error:
        with ACTIVE_RECORDERS_LOCK:
            current = ACTIVE_RECORDERS.get(session.session_id)
            if current is runner:
                ACTIVE_RECORDERS.pop(session.session_id, None)
        raise RecordingStartError(runner.start_error)

    return runner


def stop_recording_session(session_id, wait_timeout=8):
    with ACTIVE_RECORDERS_LOCK:
        runner = ACTIVE_RECORDERS.get(session_id)

    PlaywrightRecordingSession.objects.filter(
        session_id=session_id,
        status__in=ACTIVE_RECORDING_STATUSES,
    ).update(
        status=PlaywrightRecordingSession.STATUS_STOPPING,
        updated_at=timezone.now(),
        metadata=mark_recording_metadata(session_id, active_recorder=False, stop_requested=True),
    )

    if runner:
        runner.stop()
        runner.join(timeout=wait_timeout)
        if runner.is_alive():
            PlaywrightRecordingSession.objects.filter(session_id=session_id).update(
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
                stopped_at=timezone.now(),
                updated_at=timezone.now(),
                metadata=mark_recording_metadata(session_id, active_recorder=False, stop_requested=True),
            )
        return runner

    PlaywrightRecordingSession.objects.filter(
        session_id=session_id,
        status__in=ACTIVE_RECORDING_STATUSES,
    ).update(
        status=PlaywrightRecordingSession.STATUS_COMPLETED,
        stopped_at=timezone.now(),
        updated_at=timezone.now(),
        metadata=mark_recording_metadata(session_id, active_recorder=False, stop_requested=True),
    )
    return None


def get_active_recording_ids():
    with ACTIVE_RECORDERS_LOCK:
        return [session_id for session_id, runner in ACTIVE_RECORDERS.items() if runner.is_alive()]


def mark_recording_metadata(session_id, **updates):
    session = PlaywrightRecordingSession.objects.filter(session_id=session_id).only('metadata').first()
    metadata = dict(session.metadata or {}) if session else {}
    metadata.update(updates)
    return metadata


def normalize_recorder_display_number(display):
    display = str(display or '').strip()
    match = re.match(r'^:?(?P<number>\d+)(?:\.\d+)?$', display)
    return match.group('number') if match else ''


def offset_recorder_display(display, slot):
    display = str(display or '').strip() or ':99'
    match = re.match(r'^:?(?P<number>\d+)(?P<screen>\.\d+)?$', display)
    if not match:
        return display
    screen = match.group('screen') or ''
    return f':{int(match.group("number")) + int(slot)}{screen}'


def build_recorder_runtime_config(slot=0):
    slot = max(0, int(slot or 0))
    return RecorderRuntimeConfig(
        slot=slot,
        display=offset_recorder_display(get_recorder_xvfb_display(), slot),
        cdp_public_port=get_recorder_cdp_port() + slot,
        cdp_internal_port=get_recorder_cdp_internal_port() + slot,
        cdp_host_port=get_recorder_cdp_host_port() + slot,
        vnc_port=get_recorder_vnc_port() + slot,
        novnc_port=get_recorder_novnc_port() + slot,
        novnc_host_port=get_recorder_novnc_host_port() + slot,
    )


def get_recorder_runtime_port_values(runtime_config):
    return {
        runtime_config.cdp_public_port,
        runtime_config.cdp_internal_port,
        runtime_config.vnc_port,
        runtime_config.novnc_port,
    }


def is_tcp_port_bindable(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((host, int(port)))
        return True
    except OSError:
        return False


def is_recorder_runtime_available(runtime_config):
    for port in get_recorder_runtime_port_values(runtime_config):
        if not is_tcp_port_bindable('0.0.0.0', port):
            return False

    display_number = normalize_recorder_display_number(runtime_config.display)
    if display_number and os.path.exists(f'/tmp/.X{display_number}-lock'):
        return False
    return True


def get_active_recorder_runtime_slots():
    with ACTIVE_RECORDERS_LOCK:
        return {
            runner.runtime_config.slot
            for runner in ACTIVE_RECORDERS.values()
            if runner.is_alive() and getattr(runner, 'runtime_config', None)
        }


def allocate_recorder_runtime_config():
    used_slots = get_active_recorder_runtime_slots()
    for slot in range(get_recorder_max_sessions()):
        if slot in used_slots:
            continue
        runtime_config = build_recorder_runtime_config(slot)
        if is_recorder_runtime_available(runtime_config):
            return runtime_config
    raise RecordingStartError(
        f'No available controlled browser runtime slot. '
        f'Max concurrent sessions: {get_recorder_max_sessions()}'
    )


def iter_recorder_runtime_configs_for_cleanup():
    for slot in range(get_recorder_max_sessions()):
        yield build_recorder_runtime_config(slot)


def list_processes_for_recorder_cleanup():
    if os.name == 'nt':
        return []
    try:
        output = subprocess.check_output(
            ['ps', '-eo', 'pid=,ppid=,stat=,args='],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except Exception:
        return []

    processes = []
    for line in output.splitlines():
        match = re.match(r'\s*(?P<pid>\d+)\s+(?P<ppid>\d+)\s+(?P<stat>\S+)\s+(?P<command>.+?)\s*$', line)
        if not match:
            continue
        try:
            pid = int(match.group('pid'))
            ppid = int(match.group('ppid'))
        except ValueError:
            continue
        processes.append({
            'pid': pid,
            'ppid': ppid,
            'stat': match.group('stat'),
            'command': match.group('command'),
        })
    return processes


def is_recorder_orphan_process(command):
    command = str(command or '')
    normalized_command = command.replace('[', ' ').replace(']', ' ')
    runtime_configs = list(iter_recorder_runtime_configs_for_cleanup())
    displays = {config.display for config in runtime_configs if config.display}
    display_numbers = {normalize_recorder_display_number(display) for display in displays}
    display_numbers.discard('')
    cdp_ports = {str(config.cdp_public_port) for config in runtime_configs}
    cdp_ports.update(str(config.cdp_internal_port) for config in runtime_configs)
    vnc_ports = {str(config.vnc_port) for config in runtime_configs}
    novnc_ports = {str(config.novnc_port) for config in runtime_configs}

    if re.search(r'(^|/|\s)Xvfb(\s|$)', normalized_command) and any(
        re.search(rf'(^|\s){re.escape(display)}(\s|$)', command)
        for display in displays
    ):
        return True
    if re.search(r'(^|/|\s)x11vnc(\s|$)', normalized_command):
        if any(re.search(rf'(^|\s)-display\s+{re.escape(display)}(\s|$)', command) for display in displays):
            return True
        if any(re.search(rf'(^|\s)-rfbport\s+{re.escape(port)}(\s|$)', command) for port in vnc_ports):
            return True
    if re.search(r'(^|/|\s)websockify(\s|$)', normalized_command):
        if any(
            re.search(rf'(^|\s)(0\.0\.0\.0:|127\.0\.0\.1:|localhost:)?{re.escape(port)}(\s|$)', command)
            for port in novnc_ports
        ):
            return True
    if re.search(r'(^|/|\s)(chromium|chrome)(\s|$)', normalized_command, re.IGNORECASE):
        for port in cdp_ports:
            if f'--remote-debugging-port={port}' in command or re.search(rf'--remote-debugging-port\s+{re.escape(port)}(\s|$)', command):
                return True
    if display_numbers and re.search(r'(^|/|\s)(fluxbox|openbox)(\s|$)', normalized_command):
        return True
    if display_numbers and re.search(r'(^|/|\s)(fcitx5|fcitx)(\s|$)', normalized_command):
        return True
    if re.search(r'(^|/|\s)dbus-daemon(\s|$)', normalized_command) and '--session' in command:
        return True
    return False


def terminate_recorder_processes(processes):
    current_pid = os.getpid()
    process_by_pid = {process['pid']: process for process in processes}
    child_pids = {}
    for process in processes:
        child_pids.setdefault(process.get('ppid'), set()).add(process.get('pid'))

    target_pids = {
        process['pid']
        for process in processes
        if process.get('pid') != current_pid and is_recorder_orphan_process(process.get('command'))
    }

    for pid in list(target_pids):
        stack = list(child_pids.get(pid, set()))
        while stack:
            child_pid = stack.pop()
            if child_pid == current_pid or child_pid in target_pids:
                continue
            target_pids.add(child_pid)
            stack.extend(child_pids.get(child_pid, set()))

        parent = process_by_pid.get(process_by_pid.get(pid, {}).get('ppid'))
        parent_command = str(parent.get('command') if parent else '').lower()
        if parent and parent.get('pid') != current_pid and 'playwright' in parent_command and 'run-driver' in parent_command:
            target_pids.add(parent['pid'])

    target_pids = sorted(target_pids)
    if not target_pids:
        return []

    for pid in target_pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception:
            pass

    deadline = time.time() + 3
    remaining = set(target_pids)
    while remaining and time.time() < deadline:
        for pid in list(remaining):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                remaining.discard(pid)
            except Exception:
                remaining.discard(pid)
        if remaining:
            time.sleep(0.1)

    for pid in list(remaining):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception:
            pass

    return target_pids


def cleanup_recorder_display_lock():
    removed = False
    processes = list_processes_for_recorder_cleanup()
    for runtime_config in iter_recorder_runtime_configs_for_cleanup():
        display_number = normalize_recorder_display_number(runtime_config.display)
        if not display_number:
            continue
        lock_path = f'/tmp/.X{display_number}-lock'
        if not os.path.exists(lock_path):
            continue
        display_pattern = re.compile(rf'(^|/|\s)Xvfb(\s|$).*({re.escape(runtime_config.display)})(\s|$)')
        if any(display_pattern.search(str(item.get('command') or '')) for item in processes):
            continue
        try:
            os.remove(lock_path)
            removed = True
        except OSError:
            pass
    return removed


def reap_recorder_child_processes():
    if os.name == 'nt':
        return 0

    reaped = 0
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        except OSError:
            break
        if not pid:
            break
        reaped += 1
    return reaped


def cleanup_orphan_recorder_processes():
    if os.name == 'nt':
        return []
    processes = list_processes_for_recorder_cleanup()
    killed_pids = terminate_recorder_processes(processes)
    cleanup_recorder_display_lock()
    reap_recorder_child_processes()
    return killed_pids


def cleanup_stale_recording_sessions(exclude_session_ids=None):
    exclude_session_ids = set(exclude_session_ids or [])
    active_ids = set(get_active_recording_ids())
    queryset = PlaywrightRecordingSession.objects.filter(status__in=ACTIVE_RECORDING_STATUSES)
    queryset = queryset.exclude(
        recording_method=PlaywrightRecordingSession.RECORDING_METHOD_LOCAL_AGENT_PLAYWRIGHT
    )
    if active_ids:
        queryset = queryset.exclude(session_id__in=active_ids)
    if exclude_session_ids:
        queryset = queryset.exclude(session_id__in=exclude_session_ids)
    now = timezone.now()
    for session in queryset:
        metadata = dict(session.metadata or {})
        metadata['active_recorder'] = False
        metadata['stale_recorder_cleanup'] = True
        session.status = PlaywrightRecordingSession.STATUS_COMPLETED
        session.stopped_at = session.stopped_at or now
        session.metadata = metadata
        session.save(update_fields=['status', 'stopped_at', 'metadata', 'updated_at'])


class PlaywrightRecorder:
    def __init__(self, session_id, runtime_config=None):
        self.session_id = session_id
        self.runtime_config = runtime_config or build_recorder_runtime_config(0)
        self.stop_requested = threading.Event()
        self.ready_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name=f'playwright-recorder-{session_id}', daemon=True)
        self.step_number = 0
        self.start_error = ''
        self.original_target_url = ''
        self.browser_target_url = ''

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_requested.set()
        self._set_session_status(PlaywrightRecordingSession.STATUS_STOPPING)

    def join(self, timeout=None):
        self.thread.join(timeout)

    def is_alive(self):
        return self.thread.is_alive()

    def wait_until_ready(self, timeout=None):
        return self.ready_event.wait(timeout=timeout)

    def _run(self):
        close_old_connections()
        browser = None
        playwright = None
        xvfb_process = None
        desktop_processes = []
        desktop_url = ''
        desktop_warning = ''
        cdp_proxy = None
        target_proxy = None
        normal_shutdown = False

        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright

            session = PlaywrightRecordingSession.objects.get(session_id=self.session_id)
            session.target_url = normalize_target_url(session.target_url)
            session.browser_type = normalize_browser_type(session.browser_type)
            self.original_target_url = session.target_url
            self.browser_target_url = session.target_url
            self.step_number = session.steps.aggregate(max_step=Max('step_number')).get('max_step') or 0
            self._set_session_status(PlaywrightRecordingSession.STATUS_STARTING, error_message='')

            xvfb_process, display = self._ensure_display()
            desktop_env = build_recorder_desktop_env(display) if display else {}
            desktop_processes, desktop_url, desktop_warning = self._start_desktop_access(display, desktop_env)
            target_proxy = self._start_localhost_target_proxy()
            cdp_public_port = self.runtime_config.cdp_public_port
            cdp_internal_port = self.runtime_config.cdp_internal_port
            if session.browser_type == 'chromium' and cdp_internal_port != cdp_public_port:
                cdp_proxy = TcpPortForwarder(
                    '0.0.0.0',
                    cdp_public_port,
                    '127.0.0.1',
                    cdp_internal_port,
                )
                cdp_proxy.start()

            playwright = sync_playwright().start()
            launcher = getattr(playwright, session.browser_type)
            launch_options = {'headless': False}
            screen_width, screen_height = get_recorder_screen_size()
            if display:
                launch_options['env'] = desktop_env

            if session.browser_type == 'chromium':
                launch_options['args'] = [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--ignore-certificate-errors',
                    '--allow-insecure-localhost',
                    '--start-maximized',
                    '--start-fullscreen',
                    f'--ozone-platform-hint=x11',
                    '--window-position=0,0',
                    f'--window-size={screen_width},{screen_height}',
                    f'--app-shell-host-window-size={screen_width}x{screen_height}',
                    '--force-device-scale-factor=1',
                    f'--remote-debugging-address={"127.0.0.1" if cdp_proxy else "0.0.0.0"}',
                    f'--remote-debugging-port={cdp_internal_port if cdp_proxy else cdp_public_port}',
                    '--remote-allow-origins=*',
                ]

            browser = launcher.launch(**launch_options, timeout=get_recorder_chromium_launch_timeout())
            context = browser.new_context(
                viewport=None,
                no_viewport=True,
                accept_downloads=True,
                ignore_https_errors=should_ignore_https_errors(),
            )
            context.add_init_script(RECORDING_SCRIPT)
            page = context.new_page()
            page.set_default_timeout(5000)
            if session.browser_type == 'chromium':
                browser_geometry = self._fit_browser_window_to_screen(context, page, screen_width, screen_height)
            else:
                browser_geometry = {}
            devtools_url = self._resolve_browser_url(session.browser_type)
            ready_metadata = {
                **self.runtime_config.as_metadata(),
                'started_browser_pid': getattr(getattr(browser, 'process', None), 'pid', None),
                'active_recorder': True,
                'display': display or os.environ.get('DISPLAY') or '',
                'desktop_screen_width': screen_width,
                'desktop_screen_height': screen_height,
                'browser_geometry': browser_geometry,
                'input_method_enabled': bool(desktop_env.get('DBUS_SESSION_BUS_ADDRESS')),
                'original_target_url': self.original_target_url,
                'browser_target_url': self.browser_target_url,
                'target_connectivity': probe_target_url_connectivity(self.browser_target_url),
            }
            if target_proxy:
                ready_metadata['localhost_target_proxy'] = True
                ready_metadata['localhost_proxy_port'] = target_proxy.listen_port
                ready_metadata['localhost_proxy_target_host'] = target_proxy.target_host
                ready_metadata['localhost_proxy_target_port'] = target_proxy.target_port
            if self.browser_target_url != self.original_target_url:
                ready_metadata['target_url_rewritten'] = True
                ready_metadata['localhost_rewrite_host'] = get_recorder_localhost_rewrite_host()
            if desktop_url:
                ready_metadata['browser_url'] = desktop_url
                ready_metadata['desktop_url'] = desktop_url
                ready_metadata['browser_access_mode'] = 'novnc'
            elif devtools_url:
                ready_metadata['browser_url'] = devtools_url
                ready_metadata['browser_access_mode'] = 'devtools'
            if desktop_warning:
                ready_metadata['desktop_warning'] = desktop_warning
            if devtools_url:
                ready_metadata['devtools_url'] = devtools_url
                ready_metadata['cdp_port'] = cdp_public_port
                ready_metadata['cdp_internal_port'] = cdp_internal_port if cdp_proxy else cdp_public_port
                ready_metadata['cdp_proxy'] = bool(cdp_proxy)

            self._set_session_status(
                PlaywrightRecordingSession.STATUS_RECORDING,
                metadata=ready_metadata,
            )
            self.ready_event.set()

            if not self.stop_requested.is_set():
                try:
                    page.goto(
                        self.browser_target_url,
                        wait_until='domcontentloaded',
                        timeout=get_recorder_initial_navigation_timeout(),
                    )
                except PlaywrightTimeoutError as exc:
                    # Keep the browser open: slow pages can still be operated manually.
                    self._append_session_warning(f'Initial navigation timed out: {exc}')
                except PlaywrightError as exc:
                    self._append_session_warning(f'Initial navigation failed: {exc}')

            empty_page_count = 0
            while not self.stop_requested.is_set():
                if not browser.is_connected():
                    break

                pages = [item for item in context.pages if not item.is_closed()]
                if not pages:
                    empty_page_count += 1
                    if empty_page_count >= EMPTY_PAGE_LIMIT:
                        break
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue

                empty_page_count = 0
                for current_page in pages:
                    self._drain_page_events(current_page)
                time.sleep(POLL_INTERVAL_SECONDS)

            if browser.is_connected():
                for current_page in [item for item in context.pages if not item.is_closed()]:
                    self._drain_page_events(current_page, flush_pending=True)

            normal_shutdown = True
        except Exception as exc:
            if self.stop_requested.is_set():
                normal_shutdown = True
            else:
                self.start_error = str(exc)
                self._fail_session(str(exc))
                self.ready_event.set()
        finally:
            try:
                if browser is not None and browser.is_connected():
                    browser.close()
            except Exception:
                pass
            try:
                if playwright is not None:
                    playwright.stop()
            except Exception:
                pass
            try:
                if cdp_proxy is not None:
                    cdp_proxy.stop()
            except Exception:
                pass
            try:
                if target_proxy is not None:
                    target_proxy.stop()
            except Exception:
                pass
            self._stop_processes(desktop_processes)
            self._stop_virtual_display(xvfb_process)
            if (
                self.stop_requested.is_set()
                and can_cleanup_orphan_recorder_processes(exclude_session_id=self.session_id)
            ):
                cleanup_orphan_recorder_processes()

            if normal_shutdown:
                self._complete_session()

            with ACTIVE_RECORDERS_LOCK:
                current = ACTIVE_RECORDERS.get(self.session_id)
                if current is self:
                    ACTIVE_RECORDERS.pop(self.session_id, None)
            close_old_connections()

    def _run_db_operation(self, operation):
        result = {}

        def run():
            close_old_connections()
            try:
                result['value'] = operation()
            except Exception as exc:
                result['error'] = exc
            finally:
                close_old_connections()

        worker = threading.Thread(target=run, name=f'playwright-recorder-db-{self.session_id}', daemon=True)
        worker.start()
        worker.join()
        if 'error' in result:
            raise result['error']
        return result.get('value')

    def _fit_browser_window_to_screen(self, context, page, width, height):
        geometry = {
            'requested_width': int(width),
            'requested_height': int(height),
        }
        try:
            cdp_session = context.new_cdp_session(page)
            window_info = cdp_session.send('Browser.getWindowForTarget')
            window_id = window_info.get('windowId')
            if not window_id:
                return geometry
            try:
                cdp_session.send('Browser.setWindowBounds', {
                    'windowId': window_id,
                    'bounds': {'windowState': 'normal'},
                })
            except Exception:
                pass
            cdp_session.send('Browser.setWindowBounds', {
                'windowId': window_id,
                'bounds': {
                    'left': 0,
                    'top': 0,
                    'width': int(width),
                    'height': int(height),
                },
            })
            try:
                page.set_viewport_size({'width': int(width), 'height': int(height)})
            except Exception as exc:
                geometry['viewport_resize_warning'] = str(exc)
            try:
                cdp_session.send('Browser.setWindowBounds', {
                    'windowId': window_id,
                    'bounds': {'windowState': 'maximized'},
                })
            except Exception:
                pass
            try:
                current_bounds = cdp_session.send('Browser.getWindowBounds', {'windowId': window_id})
                if isinstance(current_bounds, dict):
                    geometry['window_bounds'] = current_bounds.get('bounds') or current_bounds
            except Exception:
                pass
            try:
                viewport = page.evaluate("""() => ({
                  innerWidth: window.innerWidth,
                  innerHeight: window.innerHeight,
                  outerWidth: window.outerWidth,
                  outerHeight: window.outerHeight,
                  screenWidth: window.screen.width,
                  screenHeight: window.screen.height,
                  devicePixelRatio: window.devicePixelRatio
                })""")
                if isinstance(viewport, dict):
                    geometry['page_viewport'] = viewport
            except Exception:
                pass
        except Exception as exc:
            self._append_session_warning(f'Could not resize controlled browser window: {exc}')
            geometry['error'] = str(exc)
        return geometry

    def _ensure_display(self):
        current_display = os.environ.get('DISPLAY')
        force_xvfb = parse_recorder_bool(os.environ.get('PLAYWRIGHT_RECORDER_FORCE_XVFB'), default=False)
        use_xvfb = parse_recorder_bool(os.environ.get('PLAYWRIGHT_RECORDER_USE_XVFB'), default=not bool(current_display))
        if current_display and not force_xvfb:
            return None, current_display
        if not use_xvfb:
            return None, current_display or ''

        display = self.runtime_config.display
        command = [
            'Xvfb',
            display,
            '-screen',
            '0',
            get_recorder_xvfb_screen_spec(),
            '-nolisten',
            'tcp',
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(0.4)
        if process.poll() is not None:
            _, stderr = process.communicate(timeout=1)
            raise RecordingStartError(f'Failed to start Xvfb display {display}: {stderr.strip()}')
        return process, display

    def _configure_keyboard_layout(self, env):
        setxkbmap = shutil.which('setxkbmap')
        if not setxkbmap:
            return ''
        try:
            result = subprocess.run(
                [setxkbmap, '-layout', 'us'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3,
                check=False,
            )
        except Exception as exc:
            return f'keyboard layout could not be configured: {exc}'
        if result.returncode:
            return f'keyboard layout could not be configured: {result.stderr.strip()}'
        return ''

    def _start_desktop_access(self, display, env):
        if not display:
            return [], '', ''
        enabled = parse_recorder_bool(os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_ENABLED'), default=True)
        if not enabled:
            return [], '', ''

        x11vnc = shutil.which('x11vnc')
        websockify = shutil.which('websockify')
        if not x11vnc or not websockify:
            return [], '', 'noVNC desktop access unavailable: x11vnc or websockify is not installed'

        web_root = str(os.environ.get('PLAYWRIGHT_RECORDER_NOVNC_WEB_ROOT') or '/usr/share/novnc').strip()
        if not os.path.isdir(web_root):
            return [], '', f'noVNC desktop access unavailable: web root not found: {web_root}'

        processes = []
        vnc_port = self.runtime_config.vnc_port
        novnc_port = self.runtime_config.novnc_port

        try:
            input_method_warning = self._start_input_method(env, processes)
            keyboard_warning = self._configure_keyboard_layout(env)
            desktop_warnings = [item for item in (input_method_warning, keyboard_warning) if item]

            window_manager = next((item for item in ('fluxbox', 'openbox') if shutil.which(item)), '')
            if window_manager:
                wm_process = subprocess.Popen(
                    [window_manager],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                processes.append(wm_process)
                time.sleep(0.2)
                if wm_process.poll() is not None:
                    processes.pop()

            vnc_process = subprocess.Popen(
                [
                    x11vnc,
                    '-display',
                    display,
                    '-rfbport',
                    str(vnc_port),
                    '-no6',
                    '-forever',
                    '-shared',
                    '-nopw',
                    '-listen',
                    '127.0.0.1',
                    '-xkb',
                    '-repeat',
                    '-quiet',
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            processes.append(vnc_process)
            time.sleep(0.5)
            if vnc_process.poll() is not None:
                _, stderr = vnc_process.communicate(timeout=1)
                raise RecordingStartError(f'x11vnc failed: {stderr.strip()}')
            vnc_ready, vnc_error = wait_for_tcp_port('127.0.0.1', vnc_port, timeout=get_recorder_desktop_ready_timeout())
            if not vnc_ready:
                raise RecordingStartError(f'x11vnc did not become ready on port {vnc_port}: {vnc_error}')

            novnc_process = subprocess.Popen(
                [
                    websockify,
                    '--web',
                    web_root,
                    f'0.0.0.0:{novnc_port}',
                    f'127.0.0.1:{vnc_port}',
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            processes.append(novnc_process)
            time.sleep(0.5)
            if novnc_process.poll() is not None:
                _, stderr = novnc_process.communicate(timeout=1)
                raise RecordingStartError(f'websockify failed: {stderr.strip()}')
            novnc_ready, novnc_error = validate_recorder_websocket_endpoint(
                '127.0.0.1',
                novnc_port,
                path=get_recorder_novnc_websocket_path(),
                timeout=get_recorder_desktop_ready_timeout(),
            )
            if not novnc_ready:
                raise RecordingStartError(f'noVNC websocket did not become ready on port {novnc_port}: {novnc_error}')

            return processes, build_recorder_novnc_url(self.runtime_config), '; '.join(desktop_warnings)
        except Exception as exc:
            self._stop_processes(processes)
            return [], '', f'noVNC desktop access failed: {exc}'

    def _ensure_fcitx5_profile(self, env):
        home = env.get('HOME') or os.path.expanduser('~') or '/root'
        config_dir = os.path.join(home, '.config', 'fcitx5')
        os.makedirs(config_dir, exist_ok=True)
        profile_path = os.path.join(config_dir, 'profile')
        if not os.path.exists(profile_path):
            with open(profile_path, 'w', encoding='utf-8') as profile_file:
                profile_file.write(
                    '[Groups/0]\n'
                    'Name=Default\n'
                    'Default Layout=us\n'
                    'DefaultIM=pinyin\n'
                    '\n'
                    '[Groups/0/Items/0]\n'
                    'Name=keyboard-us\n'
                    'Layout=\n'
                    '\n'
                    '[Groups/0/Items/1]\n'
                    'Name=pinyin\n'
                    'Layout=\n'
                    '\n'
                    '[GroupOrder]\n'
                    '0=Default\n'
                )

    def _start_input_method(self, env, processes):
        enabled = parse_recorder_bool(os.environ.get('PLAYWRIGHT_RECORDER_FCITX_ENABLED'), default=True)
        if not enabled:
            return ''

        fcitx = shutil.which('fcitx5')
        if not fcitx:
            return 'Chinese input method unavailable: fcitx5 is not installed'

        try:
            self._ensure_fcitx5_profile(env)
        except Exception as exc:
            return f'Chinese input method profile could not be prepared: {exc}'

        dbus = shutil.which('dbus-daemon')
        if dbus and not env.get('DBUS_SESSION_BUS_ADDRESS'):
            dbus_process = subprocess.Popen(
                [dbus, '--session', '--nofork', '--print-address'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                address = dbus_process.stdout.readline().strip()
            except Exception:
                address = ''
            if dbus_process.poll() is not None:
                _, stderr = dbus_process.communicate(timeout=1)
                return f'Chinese input method dbus failed: {stderr.strip()}'
            if address:
                env['DBUS_SESSION_BUS_ADDRESS'] = address
                processes.append(dbus_process)
            else:
                self._stop_processes([dbus_process])

        fcitx_process = subprocess.Popen(
            [fcitx, '-r'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        processes.append(fcitx_process)
        time.sleep(0.8)
        if fcitx_process.poll() is not None and fcitx_process.returncode not in (0, None):
            processes.pop()
            _, stderr = fcitx_process.communicate(timeout=1)
            return f'Chinese input method failed: {stderr.strip()}'

        fcitx_remote = shutil.which('fcitx5-remote')
        if fcitx_remote:
            try:
                subprocess.run(
                    [fcitx_remote, '-s', 'pinyin'],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=2,
                    check=False,
                )
            except Exception:
                pass
        return ''

    def _start_localhost_target_proxy(self):
        rewrite_host = get_recorder_localhost_rewrite_host()
        if not rewrite_host or not is_localhost_url(self.original_target_url):
            return None

        parsed = urlparse(self.original_target_url)
        target_port = get_url_port(parsed)
        preferred_port = target_port
        proxy = TcpPortForwarder(
            '127.0.0.1',
            preferred_port,
            rewrite_host,
            target_port,
        )
        try:
            proxy.start()
        except RecordingStartError:
            proxy = TcpPortForwarder(
                '127.0.0.1',
                0,
                rewrite_host,
                target_port,
            )
            proxy.start()

        self.browser_target_url = build_url_with_host_port(
            self.original_target_url,
            '127.0.0.1',
            proxy.listen_port,
        )
        return proxy

    def _stop_processes(self, processes):
        for process in reversed(processes or []):
            if process is None:
                continue
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    def _stop_virtual_display(self, process):
        if process is None:
            return
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    def _resolve_browser_url(self, browser_type):
        if browser_type != 'chromium':
            return ''

        port = self.runtime_config.cdp_internal_port
        endpoint = f'http://127.0.0.1:{port}/json'
        for _ in range(20):
            try:
                with urlopen(endpoint, timeout=0.5) as response:
                    targets = json.loads(response.read().decode('utf-8'))
                if isinstance(targets, list):
                    page_target = next(
                        (
                            item for item in targets
                            if isinstance(item, dict)
                            and item.get('type') == 'page'
                            and item.get('devtoolsFrontendUrl')
                        ),
                        None,
                    )
                    if page_target:
                        return self._externalize_devtools_url(page_target.get('devtoolsFrontendUrl') or '')
            except Exception:
                time.sleep(0.2)
        return ''

    def _externalize_devtools_url(self, devtools_url):
        if not devtools_url:
            return ''

        origin = get_recorder_devtools_external_origin(host_port=self.runtime_config.cdp_host_port)
        parsed_origin = urlparse(origin)
        ws_host = parsed_origin.netloc
        public_port = self.runtime_config.cdp_public_port
        internal_port = self.runtime_config.cdp_internal_port
        parsed_devtools_url = urlparse(devtools_url)
        if parsed_devtools_url.path.endswith('/inspector.html') and parsed_devtools_url.query:
            external_url = f'{origin}/devtools/inspector.html?{parsed_devtools_url.query}'
            if parsed_devtools_url.fragment:
                external_url = f'{external_url}#{parsed_devtools_url.fragment}'
        elif devtools_url.startswith('http://') or devtools_url.startswith('https://'):
            external_url = devtools_url
        else:
            external_url = f'{origin}/{devtools_url.lstrip("/")}'

        replacements = [
            f'ws=127.0.0.1:{internal_port}',
            f'ws=localhost:{internal_port}',
            f'ws=0.0.0.0:{internal_port}',
            f'ws=%5B::1%5D:{internal_port}',
            f'ws=127.0.0.1:{public_port}',
            f'ws=localhost:{public_port}',
            f'ws=0.0.0.0:{public_port}',
            f'ws=%5B::1%5D:{public_port}',
        ]
        for old in replacements:
            external_url = external_url.replace(old, f'ws={ws_host}')
        return external_url

    def _drain_page_events(self, page, flush_pending=False):
        if page.is_closed():
            return

        for frame in list(page.frames):
            if page.is_closed():
                return
            try:
                is_detached = getattr(frame, 'is_detached', None)
                if callable(is_detached) and is_detached():
                    continue
                events = frame.evaluate(
                    """flushPending => window.__testhub_recording_drainEvents
                        ? window.__testhub_recording_drainEvents(Boolean(flushPending))
                        : []""",
                    flush_pending,
                )
            except Exception:
                continue

            if not isinstance(events, list):
                continue

            for event in events:
                if not isinstance(event, dict):
                    continue
                self._persist_event(page, event, frame=frame)

    def _attach_frame_runtime_data(self, page, frame, event):
        if frame is None:
            return event

        try:
            main_frame = page.main_frame
            is_main = frame == main_frame
        except Exception:
            is_main = False

        frame_payload = event.get('frame') if isinstance(event.get('frame'), dict) else {}
        try:
            frame_url = frame.url or frame_payload.get('url') or event.get('url') or ''
        except Exception:
            frame_url = frame_payload.get('url') or event.get('url') or ''
        try:
            frame_name = frame.name or frame_payload.get('name') or ''
        except Exception:
            frame_name = frame_payload.get('name') or ''
        try:
            parent_frame = frame.parent_frame
            parent_url = parent_frame.url if parent_frame else ''
        except Exception:
            parent_url = ''

        frame_payload.update({
            'url': frame_url,
            'name': frame_name,
            'isMain': is_main,
            'parentUrl': parent_url,
        })
        event['frame'] = frame_payload
        event['frame_url'] = frame_url
        event['frame_name'] = frame_name
        event['is_iframe_event'] = not is_main
        return event

    def _persist_event(self, page, event, frame=None):
        try:
            if self.stop_requested.is_set():
                return
            event = sanitize_recording_payload(event if isinstance(event, dict) else {})
            event = self._attach_frame_runtime_data(page, frame, event)
            self.step_number += 1
            step_number = self.step_number
            page_title = self._safe_page_title(page, event)
            page_url = self._safe_page_url(page, event)
            action_type = str(event.get('action_type') or 'action').strip()[:40] or 'action'
            action_value = self._extract_action_value(event)
            snapshot_filename = f'recording-{self.session_id}-step-{step_number:04d}.yml'
            snapshot_content = self._capture_snapshot(page, frame=frame)

            try:
                from .views import write_snapshot_file

                session_module = {}
                try:
                    session = PlaywrightRecordingSession.objects.filter(session_id=self.session_id).only('metadata').first()
                    metadata = session.metadata if session and isinstance(session.metadata, dict) else {}
                    session_module = metadata.get('module') if isinstance(metadata.get('module'), dict) else {}
                except Exception:
                    session_module = {}

                step_label = f'{page_title or page_url or self.session_id} step {step_number}'
                write_snapshot_file(
                    snapshot_filename,
                    snapshot_content,
                    overwrite=True,
                    page_name=step_label,
                    alias=step_label,
                    module=session_module if session_module else None,
                    creation_method='server_playwright_cli',
                )
            except Exception:
                snapshot_filename = ''

            screenshot_path = self._capture_screenshot(page, step_number)
            element = self._json_safe(event.get('element') or {})
            selectors = self._json_safe(event.get('selectors') or [])
            raw_event = self._json_safe(event)

            def operation():
                with transaction.atomic():
                    session = PlaywrightRecordingSession.objects.select_for_update().get(session_id=self.session_id)
                    if session.status in TERMINAL_RECORDING_STATUSES or session.status == PlaywrightRecordingSession.STATUS_STOPPING:
                        return
                    PlaywrightRecordingStep.objects.create(
                        session=session,
                        step_number=step_number,
                        action_type=action_type,
                        action_value=action_value,
                        page_url=page_url,
                        page_title=page_title,
                        element=element if isinstance(element, dict) else {},
                        selectors=selectors if isinstance(selectors, list) else [],
                        snapshot_filename=snapshot_filename,
                        screenshot_path=screenshot_path,
                        raw_event=raw_event if isinstance(raw_event, dict) else {},
                    )
                    metadata = dict(session.metadata or {})
                    metadata['last_step_number'] = step_number
                    metadata['last_event_at'] = timezone.now().isoformat()
                    session.metadata = metadata
                    session.status = PlaywrightRecordingSession.STATUS_RECORDING
                    session.save(update_fields=['metadata', 'status', 'updated_at'])

            self._run_db_operation(operation)
        except Exception as exc:
            self._append_session_warning(f'Failed to persist step: {exc}')

    def _capture_snapshot(self, page, frame=None):
        snapshot_target = frame or page
        try:
            locator = snapshot_target.locator('body')
            aria_snapshot = getattr(locator, 'aria_snapshot', None)
            if callable(aria_snapshot):
                content = aria_snapshot(timeout=2500)
                if isinstance(content, str) and content.strip():
                    return sanitize_snapshot_content(content)
        except Exception:
            pass

        try:
            elements = snapshot_target.evaluate(DOM_SNAPSHOT_SCRIPT)
            return sanitize_snapshot_content(self._format_dom_snapshot(elements if isinstance(elements, list) else []))
        except Exception as exc:
            return sanitize_snapshot_content(self._format_dom_snapshot([], error=str(exc)))

    def _capture_screenshot(self, page, step_number):
        try:
            date_path = datetime.now().strftime('%Y/%m')
            relative_dir = os.path.join('playwright_recordings', date_path)
            screenshot_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
            os.makedirs(screenshot_dir, exist_ok=True)
            filename = f'{self.session_id}-step-{step_number:04d}.png'
            absolute_path = os.path.join(screenshot_dir, filename)
            page.screenshot(path=absolute_path, full_page=True, timeout=4000)
            return os.path.join(relative_dir, filename).replace('\\', '/')
        except Exception:
            return ''

    def _format_dom_snapshot(self, elements, error=''):
        lines = ['- document:']
        if error:
            lines.append(f'  - generic "{self._quote_yaml_text(error)}"')

        if not elements:
            lines.append('  - generic "No interactive elements captured"')
            return '\n'.join(lines) + '\n'

        for index, element in enumerate(elements, start=1):
            role = str(element.get('role') or element.get('tag') or 'generic').strip() or 'generic'
            role = re.sub(r'[^A-Za-z0-9_-]', '', role) or 'generic'
            text = self._quote_yaml_text(element.get('text') or element.get('placeholder') or element.get('name') or '')
            attrs = [f'[ref={element.get("ref") or f"recorded-{index}"}]']
            if element.get('id'):
                attrs.append(f'[id={self._quote_attr(element.get("id"))}]')
            if element.get('name'):
                attrs.append(f'[name={self._quote_attr(element.get("name"))}]')
            if element.get('checked'):
                attrs.append('[checked]')
            if element.get('disabled'):
                attrs.append('[disabled]')
            lines.append(f'  - {role} "{text}" {" ".join(attrs)}')

        return '\n'.join(lines) + '\n'

    def _extract_action_value(self, event):
        if 'value' in event:
            value = event.get('value')
        elif 'checked' in event:
            value = event.get('checked')
        elif 'key' in event:
            value = event.get('key')
        else:
            value = ''

        if isinstance(value, bool):
            return 'true' if value else 'false'
        if isinstance(value, (list, dict)):
            return json.dumps(sanitize_recording_payload(value), ensure_ascii=False)
        if value is None:
            return ''
        return remove_private_use_characters(value)

    def _safe_page_title(self, page, event):
        event_title = event.get('title') or ''
        if event_title:
            return normalize_snapshot_inline_text(event_title)[:500]
        try:
            return normalize_snapshot_inline_text(page.title() or '')[:500]
        except Exception:
            return ''

    def _safe_page_url(self, page, event):
        page_url = str(event.get('url') or '')
        if not page_url:
            try:
                page_url = str(page.url or '')
            except Exception:
                page_url = ''
        page_url = restore_recorded_localhost_url(
            page_url,
            self.original_target_url,
            self.browser_target_url,
        )
        return page_url[:4000]

    def _json_safe(self, value):
        try:
            json.dumps(value, ensure_ascii=False)
            return value
        except TypeError:
            return json.loads(json.dumps(value, default=str, ensure_ascii=False))

    def _quote_yaml_text(self, value):
        return normalize_snapshot_inline_text(value).replace('\\', '\\\\').replace('"', '\\"')

    def _quote_attr(self, value):
        return normalize_snapshot_inline_text(value).replace(']', '')

    def _set_session_status(self, status_value, *, error_message=None, metadata=None):
        def operation():
            session = PlaywrightRecordingSession.objects.filter(session_id=self.session_id).only('status', 'metadata').first()
            if not session:
                return
            if (
                session.status in TERMINAL_RECORDING_STATUSES
                and status_value not in TERMINAL_RECORDING_STATUSES
            ):
                return
            if (
                session.status == PlaywrightRecordingSession.STATUS_STOPPING
                and status_value == PlaywrightRecordingSession.STATUS_RECORDING
            ):
                return
            update_fields = ['status', 'updated_at']
            values = {'status': status_value, 'updated_at': timezone.now()}
            if error_message is not None:
                values['error_message'] = error_message
                update_fields.append('error_message')
            if metadata is not None:
                current_metadata = dict(session.metadata or {}) if session else {}
                current_metadata.update(metadata)
                values['metadata'] = current_metadata
                update_fields.append('metadata')
            PlaywrightRecordingSession.objects.filter(session_id=self.session_id).update(**values)

        self._run_db_operation(operation)

    def _complete_session(self):
        def operation():
            PlaywrightRecordingSession.objects.filter(
                session_id=self.session_id,
                status__in=ACTIVE_RECORDING_STATUSES,
            ).update(
                status=PlaywrightRecordingSession.STATUS_COMPLETED,
                stopped_at=timezone.now(),
                updated_at=timezone.now(),
                metadata=self._metadata_with(active_recorder=False),
            )

        self._run_db_operation(operation)

    def _fail_session(self, error_message):
        def operation():
            session = PlaywrightRecordingSession.objects.filter(session_id=self.session_id).only('status').first()
            if session and session.status == PlaywrightRecordingSession.STATUS_COMPLETED:
                return
            PlaywrightRecordingSession.objects.filter(session_id=self.session_id).update(
                status=PlaywrightRecordingSession.STATUS_FAILED,
                stopped_at=timezone.now(),
                error_message=str(error_message or 'Recording failed')[:4000],
                updated_at=timezone.now(),
                metadata=self._metadata_with(active_recorder=False),
            )

        self._run_db_operation(operation)

    def _append_session_warning(self, warning):
        def operation():
            session = PlaywrightRecordingSession.objects.filter(session_id=self.session_id).first()
            if not session:
                return
            metadata = dict(session.metadata or {})
            warnings = metadata.get('warnings') if isinstance(metadata.get('warnings'), list) else []
            warnings.append(str(warning)[:1000])
            metadata['warnings'] = warnings[-20:]
            session.metadata = metadata
            session.save(update_fields=['metadata', 'updated_at'])

        self._run_db_operation(operation)

    def _metadata_with(self, **updates):
        session = PlaywrightRecordingSession.objects.filter(session_id=self.session_id).first()
        metadata = dict(session.metadata or {}) if session else {}
        metadata.update(updates)
        return metadata
