import json

import pytest

from llm_wiki.compile import parse_llm_response


def test_parse_valid_json():
    raw = '{"new_pages": [], "updated_pages": [], "index_patch": ""}'
    result = parse_llm_response(raw)
    assert result == {"new_pages": [], "updated_pages": [], "index_patch": ""}


def test_parse_json_in_code_fences():
    raw = '```json\n{"new_pages": [], "updated_pages": [], "index_patch": ""}\n```'
    result = parse_llm_response(raw)
    assert result == {"new_pages": [], "updated_pages": [], "index_patch": ""}


def test_parse_json_in_unlabeled_code_fences():
    raw = '```\n{"new_pages": [], "updated_pages": [], "index_patch": ""}\n```'
    result = parse_llm_response(raw)
    assert result == {"new_pages": [], "updated_pages": [], "index_patch": ""}


def test_parse_json_with_leading_trailing_whitespace():
    raw = '  \n  {"new_pages": [], "updated_pages": [], "index_patch": ""}  \n  '
    result = parse_llm_response(raw)
    assert result == {"new_pages": [], "updated_pages": [], "index_patch": ""}


def test_parse_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_llm_response("this is not json")


def test_parse_invalid_json_in_fences_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_llm_response("```json\nnot json\n```")
