"""Constrained MVP generator: the "offline records tool" product class.

The language model never writes executable code here. It supplies a validated ProductSpec
(entity, fields, statuses, features) and copy; this module renders fixed, reviewed templates:

  index.html, styles.css, app.js (UI), app-core.js (pure logic), config.json,
  tests/core.test.js (generated from the spec), README.md (user docs), SPEC.md, package.json

The generated tests run with Node's built-in test runner using a fixed argv, a timeout, a minimal
environment and a temporary working directory — no model-generated shell commands are executed.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas.agent_io import MvpCopy, ProductSpec

SUPPORTED_CAPABILITIES = {
    "create_records", "edit_records", "delete_records", "search", "filter_by_status", "status_workflow",
    "due_dates", "summary_stats", "csv_export", "json_export", "local_persistence",
}

APP_CORE_JS = r"""/* app-core.js — pure logic for the generated records tool (no DOM). Works in browsers and Node. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) { module.exports = factory(); }
  else { root.MateCore = factory(); }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function memoryStorage() {
    var data = {};
    return {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null; },
      setItem: function (k, v) { data[k] = String(v); },
      removeItem: function (k) { delete data[k]; }
    };
  }

  function usableStorage(preferred) {
    try {
      if (preferred) {
        preferred.setItem('__probe__', '1');
        preferred.removeItem('__probe__');
        return preferred;
      }
    } catch (e) { /* storage blocked (private mode or sandboxed preview): fall back to memory */ }
    return memoryStorage();
  }

  function isEmpty(v) { return v === undefined || v === null || String(v).trim() === ''; }

  function createStore(config, storage) {
    var store = usableStorage(storage);
    var key = 'mvp:' + config.storageKey;
    var records = load();

    function load() {
      try {
        var parsed = JSON.parse(store.getItem(key) || '[]');
        return Array.isArray(parsed) ? parsed : [];
      } catch (e) { return []; }
    }
    function save() { store.setItem(key, JSON.stringify(records)); }
    function newId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }

    function validate(input, partial) {
      var errors = {};
      config.fields.forEach(function (f) {
        if (partial && !(f.key in input)) return;
        var v = input[f.key];
        if (isEmpty(v)) { if (f.required) errors[f.key] = f.label + ' is required.'; return; }
        if (f.type === 'number' && !isFinite(Number(v))) errors[f.key] = f.label + ' must be a number.';
        if (f.type === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(String(v))) errors[f.key] = f.label + ' must be a date (YYYY-MM-DD).';
        if (f.type === 'select' && f.options.indexOf(String(v)) === -1) errors[f.key] = f.label + ' must be one of: ' + f.options.join(', ') + '.';
      });
      if (input.status !== undefined && config.statusOptions.indexOf(input.status) === -1) errors.status = 'Unknown status.';
      return errors;
    }

    function clean(input) {
      var out = {};
      config.fields.forEach(function (f) {
        if (!(f.key in input)) return;
        var v = input[f.key];
        out[f.key] = isEmpty(v) ? '' : (f.type === 'number' ? Number(v) : String(v).trim());
      });
      return out;
    }

    function textOf(record) {
      return config.fields.map(function (f) { return record[f.key] === undefined ? '' : String(record[f.key]); }).join(' ').toLowerCase();
    }

    function csvCell(value) {
      var s = value === undefined || value === null ? '' : String(value);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }

    return {
      list: function () { return records.slice(); },
      get: function (id) { return records.filter(function (r) { return r.id === id; })[0] || null; },
      add: function (input) {
        var errors = validate(input, false);
        if (Object.keys(errors).length) return { ok: false, errors: errors };
        var record = Object.assign({ id: newId(), status: input.status || config.statusOptions[0], createdAt: new Date().toISOString() }, clean(input));
        records.push(record); save();
        return { ok: true, record: record };
      },
      update: function (id, changes) {
        var record = this.get(id);
        if (!record) return { ok: false, errors: { id: 'Not found.' } };
        var errors = validate(changes, true);
        if (Object.keys(errors).length) return { ok: false, errors: errors };
        Object.assign(record, clean(changes));
        if (changes.status) record.status = changes.status;
        record.updatedAt = new Date().toISOString(); save();
        return { ok: true, record: record };
      },
      remove: function (id) {
        var before = records.length;
        records = records.filter(function (r) { return r.id !== id; });
        save();
        return records.length < before;
      },
      search: function (query) {
        var q = String(query || '').trim().toLowerCase();
        if (!q) return records.slice();
        return records.filter(function (r) { return textOf(r).indexOf(q) !== -1; });
      },
      filterByStatus: function (status) {
        if (!status) return records.slice();
        return records.filter(function (r) { return r.status === status; });
      },
      advanceStatus: function (id) {
        var record = this.get(id);
        if (!record) return null;
        var i = config.statusOptions.indexOf(record.status);
        record.status = config.statusOptions[Math.min(i + 1, config.statusOptions.length - 1)];
        save();
        return record.status;
      },
      stats: function (today) {
        var byStatus = {};
        config.statusOptions.forEach(function (s) { byStatus[s] = 0; });
        records.forEach(function (r) { byStatus[r.status] = (byStatus[r.status] || 0) + 1; });
        var dateField = config.fields.filter(function (f) { return f.type === 'date'; })[0];
        var dueSoon = 0;
        if (dateField) {
          var start = today ? new Date(today) : new Date();
          var limit = new Date(start.getTime() + 7 * 86400000);
          records.forEach(function (r) {
            if (!r[dateField.key]) return;
            var d = new Date(r[dateField.key]);
            if (d >= start && d <= limit) dueSoon += 1;
          });
        }
        return { total: records.length, byStatus: byStatus, dueSoon: dueSoon };
      },
      toCSV: function () {
        var header = config.fields.map(function (f) { return csvCell(f.label); }).concat(['Status']).join(',');
        var rows = records.map(function (r) {
          return config.fields.map(function (f) { return csvCell(r[f.key]); }).concat([csvCell(r.status)]).join(',');
        });
        return [header].concat(rows).join('\n');
      },
      toJSON: function () { return JSON.stringify(records, null, 2); }
    };
  }

  return { createStore: createStore, memoryStorage: memoryStorage };
});
"""

APP_JS = r"""/* app.js — browser UI for the generated records tool. */
(function () {
  'use strict';
  var config = window.MATE_CONFIG;
  var storage = null;
  try { storage = window.localStorage; } catch (e) { storage = null; }
  var store = window.MateCore.createStore(config, storage);
  var caps = config.capabilities;
  var state = { query: '', status: '', editing: null };

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') node.textContent = attrs[k];
      else if (k.slice(0, 2) === 'on') node.addEventListener(k.slice(2), attrs[k]);
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) node.appendChild(c); });
    return node;
  }

  function download(name, text, type) {
    var blob = new Blob([text], { type: type });
    var a = el('a', { href: URL.createObjectURL(blob), download: name });
    document.body.appendChild(a); a.click(); a.remove();
  }

  function fieldInput(f, value) {
    var id = 'f-' + f.key;
    var input;
    if (f.type === 'longtext') input = el('textarea', { id: id, name: f.key, rows: '3' });
    else if (f.type === 'select') {
      input = el('select', { id: id, name: f.key }, [el('option', { value: '', text: 'Choose…' })].concat(
        f.options.map(function (o) { return el('option', { value: o, text: o }); })));
    } else input = el('input', { id: id, name: f.key, type: f.type === 'number' ? 'number' : (f.type === 'date' ? 'date' : 'text') });
    if (value !== undefined && value !== null) input.value = value;
    if (f.required) input.setAttribute('required', '');
    return el('label', { for: id, class: 'field' }, [el('span', { text: f.label + (f.required ? ' *' : '') }), input,
      el('small', { class: 'error', id: 'err-' + f.key, 'aria-live': 'polite' })]);
  }

  function renderForm() {
    var holder = document.getElementById('form');
    holder.innerHTML = '';
    var editing = state.editing ? store.get(state.editing) : null;
    var form = el('form', { novalidate: '' });
    config.fields.forEach(function (f) { form.appendChild(fieldInput(f, editing ? editing[f.key] : '')); });
    var statusSelect = el('select', { id: 'f-status', name: 'status' }, config.statusOptions.map(function (s) { return el('option', { value: s, text: s }); }));
    statusSelect.value = editing ? editing.status : config.statusOptions[0];
    form.appendChild(el('label', { for: 'f-status', class: 'field' }, [el('span', { text: 'Status' }), statusSelect]));
    form.appendChild(el('div', { class: 'actions' }, [
      el('button', { type: 'submit', class: 'primary', text: editing ? 'Save changes' : 'Add ' + config.entitySingular.toLowerCase() }),
      editing ? el('button', { type: 'button', text: 'Cancel', onclick: function () { state.editing = null; render(); } }) : null
    ]));
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = {};
      new FormData(form).forEach(function (v, k) { data[k] = v; });
      var result = editing ? store.update(editing.id, data) : store.add(data);
      config.fields.forEach(function (f) { document.getElementById('err-' + f.key).textContent = ''; });
      if (!result.ok) {
        Object.keys(result.errors).forEach(function (k) { var e = document.getElementById('err-' + k); if (e) e.textContent = result.errors[k]; });
        return;
      }
      state.editing = null; render();
    });
    holder.appendChild(form);
  }

  function renderStats() {
    var holder = document.getElementById('stats');
    holder.innerHTML = '';
    if (caps.indexOf('summary_stats') === -1) return;
    var s = store.stats();
    var parts = [el('span', { text: s.total + ' ' + config.entityPlural.toLowerCase() })];
    config.statusOptions.forEach(function (st) { parts.push(el('span', { text: st + ': ' + s.byStatus[st] })); });
    if (caps.indexOf('due_dates') !== -1) parts.push(el('span', { text: 'Due in 7 days: ' + s.dueSoon }));
    parts.forEach(function (p) { holder.appendChild(p); });
  }

  function renderList() {
    var holder = document.getElementById('list');
    holder.innerHTML = '';
    var rows = store.search(state.query).filter(function (r) { return !state.status || r.status === state.status; });
    if (!rows.length) { holder.appendChild(el('p', { class: 'empty', text: store.list().length ? 'Nothing matches this search.' : config.emptyState })); return; }
    var table = el('table', {}, [el('thead', {}, [el('tr', {}, config.fields.map(function (f) { return el('th', { scope: 'col', text: f.label }); })
      .concat([el('th', { scope: 'col', text: 'Status' }), el('th', { scope: 'col', text: 'Actions' })]))])]);
    var body = el('tbody');
    rows.forEach(function (r) {
      var actions = [el('button', { type: 'button', text: 'Edit', onclick: function () { state.editing = r.id; render(); } })];
      if (caps.indexOf('status_workflow') !== -1) actions.push(el('button', { type: 'button', text: 'Next status', onclick: function () { store.advanceStatus(r.id); render(); } }));
      actions.push(el('button', { type: 'button', class: 'danger', text: 'Delete', onclick: function () { store.remove(r.id); render(); } }));
      body.appendChild(el('tr', {}, config.fields.map(function (f) { return el('td', { text: r[f.key] === undefined ? '' : String(r[f.key]) }); })
        .concat([el('td', { text: r.status }), el('td', { class: 'row-actions' }, actions)])));
    });
    table.appendChild(body);
    holder.appendChild(table);
  }

  function renderToolbar() {
    var bar = document.getElementById('toolbar');
    bar.innerHTML = '';
    if (caps.indexOf('search') !== -1) {
      var search = el('input', { type: 'search', placeholder: 'Search ' + config.entityPlural.toLowerCase(), 'aria-label': 'Search' });
      search.value = state.query;
      search.addEventListener('input', function () { state.query = search.value; renderList(); });
      bar.appendChild(search);
    }
    if (caps.indexOf('filter_by_status') !== -1) {
      var filter = el('select', { 'aria-label': 'Filter by status' }, [el('option', { value: '', text: 'All statuses' })]
        .concat(config.statusOptions.map(function (s) { return el('option', { value: s, text: s }); })));
      filter.value = state.status;
      filter.addEventListener('change', function () { state.status = filter.value; renderList(); });
      bar.appendChild(filter);
    }
    if (caps.indexOf('csv_export') !== -1) bar.appendChild(el('button', { type: 'button', text: 'Export CSV', onclick: function () { download(config.storageKey + '.csv', store.toCSV(), 'text/csv'); } }));
    if (caps.indexOf('json_export') !== -1) bar.appendChild(el('button', { type: 'button', text: 'Export JSON', onclick: function () { download(config.storageKey + '.json', store.toJSON(), 'application/json'); } }));
  }

  function render() { renderToolbar(); renderStats(); renderForm(); renderList(); }
  document.addEventListener('DOMContentLoaded', render);
})();
"""

STYLES_CSS = """:root { --bg: #f7f8f6; --surface: #ffffff; --text: #1f2a2a; --muted: #5b6766; --line: #d9dfdd; --accent: __ACCENT__; }
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }
header, main { max-width: 1040px; margin: 0 auto; padding: 24px; }
header h1 { margin: 0 0 4px; font-size: 24px; }
header p { margin: 0; color: var(--muted); }
.layout { display: grid; grid-template-columns: 300px 1fr; gap: 24px; align-items: start; }
@media (max-width: 760px) { .layout { grid-template-columns: 1fr; } }
#form, #list { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
.field { display: grid; gap: 4px; margin-bottom: 12px; font-size: 14px; }
input, select, textarea { font: inherit; padding: 8px 10px; border: 1px solid #8c9896; border-radius: 6px; background: #fff; }
button { font: inherit; padding: 7px 12px; border-radius: 6px; border: 1px solid #8c9896; background: #fff; cursor: pointer; }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
button.danger { color: #a3261a; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
#toolbar, #stats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
#stats span { font-size: 13px; color: var(--muted); }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
.row-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.error { color: #a3261a; min-height: 1em; }
.empty { color: var(--muted); }
footer { max-width: 1040px; margin: 0 auto; padding: 0 24px 32px; color: var(--muted); font-size: 13px; }
"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header><h1>__TITLE__</h1><p>__TAGLINE__</p></header>
<main>
  <div id="toolbar"></div>
  <div id="stats" aria-live="polite"></div>
  <div class="layout"><section id="form" aria-label="Add or edit"></section><section id="list" aria-label="Records"></section></div>
</main>
<footer>__PRIVACY__</footer>
<script>window.MATE_CONFIG = __CONFIG__;</script>
<script src="app-core.js"></script>
<script src="app.js"></script>
</body>
</html>
"""


@dataclass
class BuildResult:
    files: dict[str, str]
    test_executed: bool
    tests_passed: int
    tests_failed: int
    exit_code: int | None
    output_tail: str
    unsupported_capabilities: list[str]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "mvp"


def build_config(spec: ProductSpec, copy: MvpCopy) -> dict[str, Any]:
    caps = sorted({f.capability for f in spec.must_have_features} | {"create_records", "edit_records", "delete_records", "local_persistence"})
    return {
        "productName": copy.app_title,
        "tagline": copy.tagline,
        "emptyState": copy.empty_state,
        "privacyNote": copy.privacy_note,
        "entitySingular": spec.entity.name_singular,
        "entityPlural": spec.entity.name_plural,
        "fields": [f.model_dump() for f in spec.entity.fields],
        "statusOptions": spec.entity.status_options,
        "storageKey": _slug(copy.app_title),
        "capabilities": caps,
    }


def _sample_value(field: dict[str, Any], variant: int = 0) -> Any:
    kind = field["type"]
    if kind == "number":
        return 3 + variant
    if kind == "date":
        return f"2030-01-{10 + variant:02d}"
    if kind == "select":
        return field["options"][min(variant, len(field["options"]) - 1)]
    return f"Test {field['label']} {variant + 1}"


def build_tests(config: dict[str, Any]) -> str:
    fields = config["fields"]
    sample_a = {f["key"]: _sample_value(f, 0) for f in fields}
    sample_b = {f["key"]: _sample_value(f, 1) for f in fields}
    required = [f for f in fields if f["required"]]
    text_field = next((f for f in fields if f["type"] in ("text", "longtext")), None)
    select_field = next((f for f in fields if f["type"] == "select"), None)
    number_field = next((f for f in fields if f["type"] == "number"), None)
    caps = set(config["capabilities"])
    lines = [
        "// Generated from the product spec. Run with: node --test tests/core.test.js",
        "const test = require('node:test');",
        "const assert = require('node:assert/strict');",
        "const config = require('../config.json');",
        "const { createStore, memoryStorage } = require('../app-core.js');",
        f"const A = {json.dumps(sample_a)};",
        f"const B = {json.dumps(sample_b)};",
        "",
        "test('config is well formed', () => {",
        "  const keys = config.fields.map(f => f.key);",
        "  assert.equal(new Set(keys).size, keys.length, 'field keys are unique');",
        "  assert.ok(config.statusOptions.length >= 2);",
        "});",
        "",
        "test('adds, lists and persists records', () => {",
        "  const storage = memoryStorage();",
        "  const store = createStore(config, storage);",
        "  const result = store.add(A);",
        "  assert.equal(result.ok, true, JSON.stringify(result.errors));",
        "  assert.equal(store.list().length, 1);",
        "  assert.equal(result.record.status, config.statusOptions[0]);",
        "  const reopened = createStore(config, storage);",
        "  assert.equal(reopened.list().length, 1, 'records survive a reload');",
        "});",
        "",
        "test('edits and deletes records', () => {",
        "  const store = createStore(config, memoryStorage());",
        "  const { record } = store.add(A);",
        "  const updated = store.update(record.id, B);",
        "  assert.equal(updated.ok, true);",
        f"  assert.equal(store.get(record.id)[{json.dumps(fields[0]['key'])}], B[{json.dumps(fields[0]['key'])}]);",
        "  assert.equal(store.remove(record.id), true);",
        "  assert.equal(store.list().length, 0);",
        "});",
    ]
    if required:
        key = required[0]["key"]
        lines += [
            "",
            "test('rejects a record missing a required field', () => {",
            "  const store = createStore(config, memoryStorage());",
            f"  const input = Object.assign({{}}, A, {{ {json.dumps(key)}: '' }});",
            "  const result = store.add(input);",
            "  assert.equal(result.ok, false);",
            f"  assert.ok(result.errors[{json.dumps(key)}]);",
            "});",
        ]
    if select_field:
        lines += [
            "",
            "test('rejects an unknown option', () => {",
            "  const store = createStore(config, memoryStorage());",
            f"  const result = store.add(Object.assign({{}}, A, {{ {json.dumps(select_field['key'])}: 'not-an-option' }}));",
            "  assert.equal(result.ok, false);",
            "});",
        ]
    if number_field:
        lines += [
            "",
            "test('rejects a non-numeric number field', () => {",
            "  const store = createStore(config, memoryStorage());",
            f"  const result = store.add(Object.assign({{}}, A, {{ {json.dumps(number_field['key'])}: 'abc' }}));",
            "  assert.equal(result.ok, false);",
            "});",
        ]
    if "search" in caps and text_field:
        lines += [
            "",
            "test('search finds records by text', () => {",
            "  const store = createStore(config, memoryStorage());",
            "  store.add(A); store.add(B);",
            f"  assert.equal(store.search(B[{json.dumps(text_field['key'])}]).length, 1);",
            "  assert.equal(store.search('').length, 2);",
            "});",
        ]
    if "filter_by_status" in caps or "status_workflow" in caps:
        lines += [
            "",
            "test('status workflow and filtering', () => {",
            "  const store = createStore(config, memoryStorage());",
            "  const { record } = store.add(A); store.add(B);",
            "  assert.equal(store.advanceStatus(record.id), config.statusOptions[1]);",
            "  assert.equal(store.filterByStatus(config.statusOptions[1]).length, 1);",
            "  assert.equal(store.filterByStatus(config.statusOptions[0]).length, 1);",
            "});",
        ]
    if "csv_export" in caps:
        lines += [
            "",
            "test('CSV export has a header and escapes values', () => {",
            "  const store = createStore(config, memoryStorage());",
            f"  store.add(Object.assign({{}}, A{', { ' + json.dumps(text_field['key']) + ': ' + json.dumps('Comma, and \"quote\"') + ' }' if text_field else ''}));",
            "  const csv = store.toCSV().split('\\n');",
            "  assert.ok(csv[0].includes(config.fields[0].label));",
            "  assert.equal(csv.length, 2);",
            *(["  assert.ok(csv[1].includes('\"Comma, and \"\"quote\"\"\"'));"] if text_field else []),
            "});",
        ]
    if "json_export" in caps:
        lines += [
            "",
            "test('JSON export round-trips', () => {",
            "  const store = createStore(config, memoryStorage());",
            "  store.add(A);",
            "  assert.equal(JSON.parse(store.toJSON()).length, 1);",
            "});",
        ]
    if "summary_stats" in caps:
        lines += [
            "",
            "test('summary stats count by status', () => {",
            "  const store = createStore(config, memoryStorage());",
            "  store.add(A); store.add(B);",
            "  const stats = store.stats('2030-01-08');",
            "  assert.equal(stats.total, 2);",
            "  assert.equal(stats.byStatus[config.statusOptions[0]], 2);",
            "});",
        ]
    lines += [
        "",
        "test('falls back to memory when storage is blocked', () => {",
        "  const blocked = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() {} };",
        "  const store = createStore(config, blocked);",
        "  assert.equal(store.add(A).ok, true);",
        "});",
        "",
    ]
    return "\n".join(lines)


def build_readme(spec: ProductSpec, copy: MvpCopy, config: dict[str, Any], unsupported: list[str]) -> str:
    fields = "\n".join(f"| {f['label']} | {f['type']} | {'yes' if f['required'] else 'no'} |" for f in config["fields"])
    features = "\n".join(f"- **{f.name}** — {f.user_value}" for f in spec.must_have_features)
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(copy.getting_started, start=1))
    out_of_scope = "\n".join(f"- {item} — STUBBED (not part of this MVP)" for item in spec.out_of_scope) or "- None listed."
    unsupported_text = (
        "\n\nRequested capabilities the template does not support (STUBBED): " + ", ".join(unsupported) if unsupported else ""
    )
    return f"""# {copy.app_title}

{copy.tagline}

Generated by Mate's MVP Builder from a reviewed template (product class: offline records tool).
It is a working starter for testing the product idea with real users, not a finished product.

## Open it

Double-click `index.html`, or serve the folder with any static file server. No install, no account,
no network access. Data stays in this browser (localStorage).

## Getting started

{steps}

## What it does

{features}

### {spec.entity.name_singular} fields

| Field | Type | Required |
|---|---|---|
{fields}

Statuses: {", ".join(spec.entity.status_options)}

## Not included

{out_of_scope}{unsupported_text}

## Privacy

{copy.privacy_note}

## Tests

Requires Node.js 18+: `node --test tests/core.test.js`
"""


def build_spec_doc(spec: ProductSpec) -> str:
    journeys = "\n".join(f"### {j.name}\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(j.steps, 1)) for j in spec.user_journeys)
    features = "\n".join(f"| {f.name} | `{f.capability}` | {f.user_value} |" for f in spec.must_have_features)
    criteria = "\n".join(f"- [ ] {c}" for c in spec.acceptance_criteria)
    return f"""# Product specification — {spec.product_name}

**Problem:** {spec.problem_statement}

**Primary user:** {spec.primary_user}

## Functional requirements

| Feature | Capability | User value |
|---|---|---|
{features}

## User journeys

{journeys}

## Acceptance criteria

{criteria}

## Technology

{chr(10).join('- ' + t for t in spec.tech_choices) or '- Static HTML, CSS and JavaScript; no backend.'}
"""


def render_files(spec: ProductSpec, copy: MvpCopy, accent: str = "#2f6f68") -> tuple[dict[str, str], list[str]]:
    unsupported = sorted({f.capability for f in spec.must_have_features} - SUPPORTED_CAPABILITIES)
    config = build_config(spec, copy)
    config_json = json.dumps(config, indent=2)
    index = (
        INDEX_HTML.replace("__TITLE__", html.escape(copy.app_title))
        .replace("__TAGLINE__", html.escape(copy.tagline))
        .replace("__PRIVACY__", html.escape(copy.privacy_note))
        .replace("__CONFIG__", json.dumps(config).replace("</", "<\\/"))
    )
    files = {
        "index.html": index,
        "styles.css": STYLES_CSS.replace("__ACCENT__", accent if re.fullmatch(r"#[0-9a-fA-F]{6}", accent) else "#2f6f68"),
        "app-core.js": APP_CORE_JS,
        "app.js": APP_JS,
        "config.json": config_json + "\n",
        "tests/core.test.js": build_tests(config),
        "README.md": build_readme(spec, copy, config, unsupported),
        "SPEC.md": build_spec_doc(spec),
        "package.json": json.dumps(
            {"name": config["storageKey"], "version": "0.1.0", "private": True, "license": "MIT", "scripts": {"test": "node --test tests/core.test.js"}},
            indent=2,
        )
        + "\n",
    }
    return files, unsupported


def run_generated_tests(files: dict[str, str], node_binary: str, timeout: float) -> tuple[bool, int, int, int | None, str]:
    """Run the generated tests in a throwaway directory with a fixed command and minimal env."""
    node = shutil.which(node_binary)
    if node is None:
        return False, 0, 0, None, f"Test runner unavailable: '{node_binary}' was not found on PATH."
    with tempfile.TemporaryDirectory(prefix="mate-mvp-") as tmp:
        root = Path(tmp)
        for name, content in files.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        env = {"PATH": os.environ.get("PATH", ""), "HOME": tmp, "NODE_OPTIONS": ""}
        try:
            proc = subprocess.run(  # noqa: S603 — fixed argv, no shell, no model-generated input
                [node, "--test", "--test-reporter=tap", "tests/core.test.js"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return True, 0, 0, None, f"Tests timed out after {timeout:.0f}s."
    output = proc.stdout + proc.stderr
    passed = int(m.group(1)) if (m := re.search(r"^# pass (\d+)", output, re.M)) else 0
    failed = int(m.group(1)) if (m := re.search(r"^# fail (\d+)", output, re.M)) else 0
    return True, passed, failed, proc.returncode, output[-3000:]


def build_mvp(spec: ProductSpec, copy: MvpCopy, *, node_binary: str, timeout: float, accent: str = "#2f6f68") -> BuildResult:
    files, unsupported = render_files(spec, copy, accent)
    executed, passed, failed, exit_code, tail = run_generated_tests(files, node_binary, timeout)
    return BuildResult(files, executed, passed, failed, exit_code, tail, unsupported)


def bundle_preview(files: dict[str, str]) -> str:
    """Inline CSS and JS into one HTML document for a sandboxed iframe preview."""
    page = files["index.html"]
    page = page.replace('<link rel="stylesheet" href="styles.css">', f"<style>{files['styles.css']}</style>")
    page = page.replace('<script src="app-core.js"></script>', f"<script>{files['app-core.js']}</script>")
    page = page.replace('<script src="app.js"></script>', f"<script>{files['app.js']}</script>")
    return page
